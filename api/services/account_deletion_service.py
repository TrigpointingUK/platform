"""
Orchestration for account deletion and anonymisation (user or admin initiated).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.core.logging import get_logger
from api.models.tphoto import TPhoto
from api.models.user import TLog, TPhotoVote, User, UserArchive
from api.schemas.account_deletion import (
    AccountDeletionExecuteResponse,
    AccountDeletionMode,
    AccountDeletionSummaryResponse,
)
from api.services.auth0_service import auth0_service
from api.services.avatar_service import AvatarService
from api.services.cache_invalidator import invalidate_user_caches
from api.services.email_service import email_service
from api.services.s3_service import S3Service

logger = get_logger(__name__)

DELETION_BACKUP_FORMAT_FLAG = "D"


def get_account_deletion_summary(
    db: Session, user: User
) -> AccountDeletionSummaryResponse:
    """Build overview counts for the deletion confirmation UI."""
    user_id = int(user.id)
    log_count = (
        db.query(func.count(TLog.id)).filter(TLog.user_id == user_id).scalar() or 0
    )
    photo_count = (
        db.query(func.count(TPhoto.id))
        .join(TLog, TPhoto.tlog_id == TLog.id)
        .filter(TLog.user_id == user_id, TPhoto.deleted_ind != "Y")
        .scalar()
        or 0
    )
    fn = str(user.firstname or "").strip()
    sn = str(user.surname or "").strip()
    full_name = " ".join(p for p in (fn, sn) if p)
    return AccountDeletionSummaryResponse(
        user_id=user_id,
        username=str(user.name or ""),
        full_name=full_name,
        email=str(user.email or ""),
        log_count=int(log_count),
        photo_count=int(photo_count),
    )


def _pick_deleted_username(db: Session) -> str:
    """Return a unique username ``Deleted-XXXXXX`` (six digits)."""
    for _ in range(100):
        suffix = f"{secrets.randbelow(1_000_000):06d}"
        candidate = f"Deleted-{suffix}"
        exists = db.query(User.id).filter(User.name == candidate).first()
        if not exists:
            return candidate
    raise RuntimeError("Could not allocate a unique anonymised username")


def _collect_active_photo_ids_for_user(db: Session, user_id: int) -> list[int]:
    rows = (
        db.query(TPhoto.id)
        .join(TLog, TPhoto.tlog_id == TLog.id)
        .filter(TLog.user_id == user_id, TPhoto.deleted_ind != "Y")
        .order_by(TPhoto.id)
        .all()
    )
    return [int(r[0]) for r in rows]


def _collect_log_ids_for_user(db: Session, user_id: int) -> list[int]:
    rows = db.query(TLog.id).filter(TLog.user_id == user_id).order_by(TLog.id).all()
    return [int(r[0]) for r in rows]


def _hard_delete_photos_by_ids(
    db: Session, s3: S3Service, photo_ids: list[int]
) -> Tuple[int, int]:
    """
    Hard-delete photos: S3 first, then DB via existing CRUD.

    Returns (deleted_count, s3_failure_count).
    """
    from api.crud import tphoto as tphoto_crud

    deleted = 0
    s3_failures = 0
    for pid in photo_ids:
        if not s3.delete_photo_and_thumbnail(pid):
            s3_failures += 1
        if tphoto_crud.delete_photo(db, photo_id=pid, soft=False):
            deleted += 1
    return deleted, s3_failures


def _purge_user_logs_and_photos(
    db: Session, s3: S3Service, user_id: int
) -> Tuple[int, int, int]:
    """
    Delete all photos (S3 + DB) and hard-delete all logs for the user.

    Returns (logs_deleted, photos_deleted, s3_failures).
    """
    from api.crud import tlog as tlog_crud

    log_ids = _collect_log_ids_for_user(db, user_id)
    photos_deleted = 0
    s3_failures = 0
    for log_id in log_ids:
        photo_ids = (
            db.query(TPhoto.id)
            .filter(TPhoto.tlog_id == log_id, TPhoto.deleted_ind != "Y")
            .order_by(TPhoto.id)
            .all()
        )
        pids = [int(r[0]) for r in photo_ids]
        pd, sf = _hard_delete_photos_by_ids(db, s3, pids)
        photos_deleted += pd
        s3_failures += sf
        tlog_crud.delete_log_hard(db, log_id=log_id)
    return len(log_ids), photos_deleted, s3_failures


def _send_ops_email(
    *,
    target_user_id: int,
    previous_username: str,
    previous_email: str,
    mode: AccountDeletionMode,
    feedback: Optional[str],
    actor_label: str,
    details_lines: list[str],
) -> None:
    body_lines = [
        "Account deletion report",
        "",
        f"Target user id: {target_user_id}",
        f"Previous username: {previous_username}",
        f"Previous email (if any): {previous_email}",
        f"Mode: {mode.value}",
        f"Actor: {actor_label}",
        f"Time (UTC): {datetime.now(UTC).isoformat()}",
        "",
        "Details:",
        *details_lines,
        "",
    ]
    if feedback and feedback.strip():
        body_lines.extend(["Feedback from user:", feedback.strip(), ""])

    message = "\n".join(body_lines)
    reply_to = (
        previous_email.strip() if previous_email.strip() else "contact@trigpointing.uk"
    )
    ok = email_service.send_contact_email(
        to_email="trigpointing@teasel.org",
        reply_to=reply_to,
        subject=f"Account deletion: {previous_username} (user {target_user_id})",
        message=message,
        name="TrigpointingUK account system",
        user_id=target_user_id,
        username=previous_username,
    )
    if not ok:
        logger.error(
            "Failed to send account deletion ops email",
            extra={"target_user_id": target_user_id},
        )


def execute_account_deletion(
    db: Session,
    *,
    target_user: User,
    mode: AccountDeletionMode,
    feedback: Optional[str],
    actor_user: User,
    is_admin_action: bool,
) -> AccountDeletionExecuteResponse:
    """
    Apply the chosen deletion policy.

    Auth0 is removed before anonymising local rows (when keeping a placeholder user).
    For full purge, the database user is removed first, then Auth0.
    """
    s3 = S3Service()
    avatar = AvatarService()

    user_id = int(target_user.id)
    previous_username = str(target_user.name or "")
    previous_email = str(target_user.email or "")
    auth0_id = (
        str(target_user.auth0_user_id).strip() if target_user.auth0_user_id else None
    )

    actor_label = (
        f"admin user_id={int(actor_user.id)}"
        if is_admin_action
        else f"self user_id={int(actor_user.id)}"
    )

    if mode == AccountDeletionMode.purge_all:
        logs_deleted, photos_deleted, s3_failures = _purge_user_logs_and_photos(
            db, s3, user_id
        )
        db.query(TPhotoVote).filter(TPhotoVote.user_id == user_id).delete(
            synchronize_session=False
        )
        db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        db.commit()

        if auth0_id and not auth0_service.delete_user(auth0_id):
            logger.warning(
                "Auth0 delete failed after user purge (database user already removed)",
                extra={"auth0_user_id": auth0_id, "user_id": user_id},
            )

        invalidate_user_caches(user_id=user_id)
        invalidate_user_caches()

        details = [
            "User row deleted: yes",
            f"Logs deleted: {logs_deleted}",
            f"Photos deleted: {photos_deleted}",
            f"S3 photo delete failures: {s3_failures}",
        ]
        _send_ops_email(
            target_user_id=user_id,
            previous_username=previous_username,
            previous_email=previous_email,
            mode=mode,
            feedback=feedback,
            actor_label=actor_label,
            details_lines=details,
        )

        return AccountDeletionExecuteResponse(
            mode=mode,
            user_id=user_id,
            previous_username=previous_username,
            new_username=None,
            logs_anonymised=0,
            photos_deleted=photos_deleted,
            logs_deleted=logs_deleted,
            s3_photo_delete_failures=s3_failures,
            user_row_deleted=True,
        )

    # Anonymise paths: remove Auth0 first so we do not commit DB changes if IdP removal fails.
    if auth0_id and not auth0_service.delete_user(auth0_id):
        logger.error(
            "Auth0 user delete failed; aborting account anonymisation",
            extra={"auth0_user_id": auth0_id, "user_id": user_id},
        )
        raise RuntimeError(
            "Could not remove the login profile from Auth0. No changes were made."
        )

    photos_deleted = 0
    s3_failures = 0

    if mode == AccountDeletionMode.anonymise_delete_photos:
        photo_ids = _collect_active_photo_ids_for_user(db, user_id)
        photos_deleted, s3_failures = _hard_delete_photos_by_ids(db, s3, photo_ids)

    new_name_final = ""
    for attempt in range(100):
        candidate = _pick_deleted_username(db)
        try:
            u = db.query(User).filter(User.id == user_id).with_for_update().one()
            u.name = candidate  # type: ignore[assignment]
            u.firstname = ""  # type: ignore[assignment]
            u.surname = ""  # type: ignore[assignment]
            u.email = ""  # type: ignore[assignment]
            u.homepage = ""  # type: ignore[assignment]
            u.about = ""  # type: ignore[assignment]
            u.cryptpw = ""  # type: ignore[assignment]
            u.auth0_user_id = None  # type: ignore[assignment]
            u.email_valid = "N"  # type: ignore[assignment]
            u.email_ind = "N"  # type: ignore[assignment]
            u.has_avatar = False  # type: ignore[assignment]
            u.ui_prefs = {}  # type: ignore[assignment]
            u.archive_frequency = "N"  # type: ignore[assignment]
            db.query(TLog).filter(TLog.user_id == user_id).update(
                {TLog.ip_addr: None}, synchronize_session=False
            )
            db.commit()
            new_name_final = candidate
            break
        except IntegrityError:
            db.rollback()
            logger.warning(
                "Anonymised username collision; retrying",
                extra={"attempt": attempt, "candidate": candidate, "user_id": user_id},
            )
    else:
        raise RuntimeError(
            "Failed to anonymise user after repeated username collisions"
        )

    try:
        avatar.delete(user_id)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "Avatar delete failed during anonymisation", extra={"error": str(exc)}
        )

    logs_anonymised = (
        db.query(func.count(TLog.id)).filter(TLog.user_id == user_id).scalar() or 0
    )

    invalidate_user_caches(user_id=user_id)
    invalidate_user_caches()

    details = [
        "User row deleted: no",
        f"New username: {new_name_final}",
        f"Logs retained with ip_addr cleared: {int(logs_anonymised)}",
        f"Photos deleted: {photos_deleted}",
        f"S3 photo delete failures: {s3_failures}",
    ]
    _send_ops_email(
        target_user_id=user_id,
        previous_username=previous_username,
        previous_email=previous_email,
        mode=mode,
        feedback=feedback,
        actor_label=actor_label,
        details_lines=details,
    )

    return AccountDeletionExecuteResponse(
        mode=mode,
        user_id=user_id,
        previous_username=previous_username,
        new_username=new_name_final,
        logs_anonymised=int(logs_anonymised),
        photos_deleted=photos_deleted,
        logs_deleted=0,
        s3_photo_delete_failures=s3_failures,
        user_row_deleted=False,
    )


def deletion_backup_is_allowed(db: Session, user_id: int, *, is_admin: bool) -> bool:
    """Return False when a non-admin user has already received a deletion backup in 24 hours."""
    if is_admin:
        return True
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    recent = (
        db.query(UserArchive.id)
        .filter(
            UserArchive.user_id == user_id,
            UserArchive.status == "S",
            UserArchive.format_at_send == DELETION_BACKUP_FORMAT_FLAG,
            UserArchive.created_at >= cutoff,
        )
        .first()
    )
    return recent is None


def send_account_deletion_log_backup_email(db: Session, user: User) -> bool:
    """
    Build a published-log zip for ``user`` and email it; record ``user_archive`` for auditing.

    Returns True if the email was accepted by SES. Caller should enforce rate limits.
    """
    from api.services.archive_service import generate_archive_zip

    user_id = int(user.id)
    email_addr = str(user.email or "").strip()
    if not email_addr:
        return False

    archive_format = str(user.archive_format or "R")
    try:
        zip_bytes = generate_archive_zip(db, user, archive_format)
    except Exception as exc:
        logger.error(
            "Deletion backup zip generation failed",
            extra={"user_id": user_id, "error": str(exc)},
        )
        db.add(
            UserArchive(
                user_id=user_id,
                status="F",
                frequency_at_send="N",
                format_at_send=DELETION_BACKUP_FORMAT_FLAG,
                error_message=str(exc)[:2000],
            )
        )
        db.commit()
        return False

    log_count = (
        db.query(func.count(TLog.id))
        .filter(TLog.user_id == user_id, TLog.status == "P")
        .scalar()
        or 0
    )
    username = str(user.name or f"user_{user_id}")
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"trigpointinguk_{username}_{ts}_pre_deletion.zip"

    fn = (str(user.firstname).strip() if user.firstname else None) or None  # type: ignore[arg-type]
    sn = (str(user.surname).strip() if user.surname else None) or None  # type: ignore[arg-type]

    ok = email_service.send_deletion_backup_email(
        to_email=email_addr,
        username=username,
        zip_bytes=zip_bytes,
        filename=filename,
        log_count=int(log_count),
        user_id=user_id,
        firstname=fn,
        surname=sn,
    )
    db.add(
        UserArchive(
            user_id=user_id,
            status="S" if ok else "F",
            frequency_at_send="N",
            format_at_send=DELETION_BACKUP_FORMAT_FLAG,
            log_count=int(log_count),
            file_size_bytes=len(zip_bytes) if ok else None,
            error_message=None if ok else "Email send failed",
        )
    )
    db.commit()
    return ok
