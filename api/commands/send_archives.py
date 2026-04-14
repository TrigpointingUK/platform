"""
Scheduled task: scan users due an archive email, generate and send them.

Run as: python -m api.commands.send_archives

Designed to be invoked by an ECS Scheduled Task (EventBridge -> Fargate RunTask)
or locally via `make send-archives`.
"""

import logging
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.core.config import settings
from api.core.metrics import get_metrics_collector
from api.db.database import get_session_local
from api.models.user import TLog, User, UserArchive
from api.services.archive_service import generate_archive_zip
from api.services.email_service import email_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

FREQUENCY_INTERVALS = {
    "W": timedelta(weeks=1),
    "M": timedelta(days=30),
    "Y": timedelta(days=365),
}

FALLBACK_INTERVALS = {
    "W": timedelta(days=30),
    "M": timedelta(days=365),
}

ACTIVE_WINDOWS = {
    "W": timedelta(weeks=1),
    "M": timedelta(days=30),
}


def _last_successful_archive(db: Session, user_id: int) -> datetime | None:
    """Return the created_at of the most recent successful archive, or None."""
    row = (
        db.query(UserArchive.created_at)
        .filter(UserArchive.user_id == user_id, UserArchive.status == "S")
        .order_by(UserArchive.created_at.desc())
        .first()
    )
    return row[0] if row else None


def _last_activity(db: Session, user_id: int) -> datetime | None:
    """Return the most recent upd_timestamp across user's published logs."""
    row = (
        db.query(func.max(TLog.upd_timestamp))
        .filter(TLog.user_id == user_id, TLog.status == "P")
        .first()
    )
    return row[0] if row and row[0] else None


def _is_user_due(db: Session, user: User, now: datetime) -> tuple[bool, str]:
    """
    Determine whether a user is due an archive email.

    Returns (is_due, reason).
    For W: send weekly if active in last week, else monthly.
    For M: send monthly if active in last month, else yearly.
    For Y: send yearly always.
    """
    freq = str(user.archive_frequency or "N")
    if freq == "N":
        return False, "frequency=N"

    user_id = int(user.id)
    last_sent = _last_successful_archive(db, user_id)

    if freq == "Y":
        if last_sent and (now - last_sent) < FREQUENCY_INTERVALS["Y"]:
            return False, "yearly: not yet due"
        return True, "yearly: due"

    active_window = ACTIVE_WINDOWS.get(freq)
    last_act = _last_activity(db, user_id)
    is_active = (
        last_act is not None
        and active_window is not None
        and (now - last_act.replace(tzinfo=timezone.utc) < active_window)
    )

    if is_active:
        interval = FREQUENCY_INTERVALS[freq]
        label = "weekly" if freq == "W" else "monthly"
    else:
        interval = FALLBACK_INTERVALS[freq]
        label = "monthly-fallback" if freq == "W" else "yearly-fallback"

    if last_sent and (now - last_sent) < interval:
        return False, f"{label}: not yet due"

    # Check if there is any new activity since last send
    if last_sent and last_act:
        last_act_aware = last_act.replace(tzinfo=timezone.utc)
        if last_act_aware <= last_sent:
            return False, f"{label}: no new activity since last archive"

    return True, f"{label}: due"


def process_user(db: Session, user: User, now: datetime) -> None:
    """Generate and send archive for a single user, recording the result."""
    user_id = int(user.id)
    username = str(user.name or f"user_{user_id}")
    archive_format = str(user.archive_format or "R")
    freq = str(user.archive_frequency or "N")
    mc = get_metrics_collector()

    try:
        zip_bytes = generate_archive_zip(db, user, archive_format)
    except Exception as e:
        logger.error(f"Archive generation failed for user {user_id}: {e}")
        record = UserArchive(
            user_id=user_id,
            status="F",
            frequency_at_send=freq,
            format_at_send=archive_format,
            error_message=str(e)[:500],
        )
        db.add(record)
        db.commit()
        if mc:
            mc.record_archive_failed("generate")
        return

    log_count = (
        db.query(TLog).filter(TLog.user_id == user_id, TLog.status == "P").count()
    )
    export_ts = now.strftime("%Y%m%d_%H%M%S")
    filename = f"trigpointinguk_{username}_{export_ts}.zip"

    dry_run = getattr(settings, "DRY_RUN_ARCHIVES", False)
    if dry_run:
        import pathlib
        import tempfile

        out_path = pathlib.Path(tempfile.gettempdir()) / filename
        out_path.write_bytes(zip_bytes)
        logger.info(f"DRY RUN: wrote {out_path} ({len(zip_bytes)} bytes)")
        email_sent = True
    else:
        email_sent = email_service.send_archive_email(
            to_email=str(user.email),
            username=username,
            zip_bytes=zip_bytes,
            filename=filename,
            log_count=log_count,
            user_id=user_id,
            firstname=str(user.firstname or ""),
            surname=str(user.surname or ""),
        )

    record = UserArchive(
        user_id=user_id,
        status="S" if email_sent else "F",
        frequency_at_send=freq,
        format_at_send=archive_format,
        log_count=log_count,
        file_size_bytes=len(zip_bytes),
        error_message=None if email_sent else "SES send failed",
    )
    db.add(record)
    db.commit()

    if email_sent:
        logger.info(
            f"Archive sent to {username} (user_id={user_id}, "
            f"logs={log_count}, size={len(zip_bytes)})"
        )
        if mc:
            mc.record_archive_sent(archive_format, len(zip_bytes))
    else:
        logger.error(f"Archive email failed for {username} (user_id={user_id})")
        if mc:
            mc.record_archive_failed("send")


def run() -> None:
    """Main entry point for the scheduled archive task."""
    now = datetime.now(timezone.utc)
    logger.info(f"Starting archive email run at {now.isoformat()}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    db: Session = get_session_local()()
    try:
        candidates = (
            db.query(User)
            .filter(
                User.archive_frequency != "N",
                User.email_valid == "Y",
                User.email.isnot(None),
                User.email != "",
            )
            .all()
        )

        logger.info(f"Found {len(candidates)} user(s) with archive enabled")

        sent = 0
        skipped = 0
        failed = 0
        mc = get_metrics_collector()

        for user in candidates:
            is_due, reason = _is_user_due(db, user, now)
            if not is_due:
                logger.info(f"Skipping user {user.id} ({user.name}): {reason}")
                skipped += 1
                if mc:
                    mc.record_archive_skipped()
                continue

            logger.info(f"Processing user {user.id} ({user.name}): {reason}")
            try:
                process_user(db, user, now)
                sent += 1
            except Exception as e:
                logger.error(
                    f"Unexpected error processing user {user.id}: {e}",
                    exc_info=True,
                )
                failed += 1
                if mc:
                    mc.record_archive_failed("generate")

        logger.info(
            f"Archive run complete: sent={sent}, skipped={skipped}, failed={failed}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
    sys.exit(0)
