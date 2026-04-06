#!/usr/bin/env python3
"""Sync medal awards from analytics to operational tables.

Compares analytics.mart_user_medals with public.medal_award, inserts new
awards and creates notification records for newly earned tiers.

Usage:
    python sync_medals.py [staging|production]

Credentials are fetched from AWS Secrets Manager using the fastapi-*
secret (needs write access to public schema).
"""

import json
import logging
import os
import subprocess
import sys

import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


def get_credentials(target: str) -> dict:
    """Fetch database credentials from Secrets Manager."""
    secret_id = f"fastapi-{target}-postgres-credentials"
    region = os.environ.get("AWS_REGION", "eu-west-1")

    result = subprocess.run(
        [
            "aws", "--region", region,
            "secretsmanager", "get-secret-value",
            "--secret-id", secret_id,
            "--query", "SecretString",
            "--output", "text",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout.strip())


def build_notification(row: dict) -> tuple:
    """Build notification title/body/metadata for a medal award."""
    tier_text = row["highest_tier_name"]
    medal_name = row["name"]

    if row["medal_type"] == "counted":
        title = f"{medal_name}!"
        body = f"{row['description']} (count: {row['current_value']})"
    elif row["medal_type"] == "collection":
        title = f"{tier_text} {medal_name}!"
        body = f"{row['description']} \u2014 {tier_text} tier earned"
    else:
        title = f"{tier_text} {medal_name}!"
        body = f"{row['description']} \u2014 tier {tier_text} earned ({row['current_value']:,})"

    metadata = json.dumps({
        "medal_code": row["code"],
        "tier_level": row["highest_tier_level"],
        "tier_name": row["highest_tier_name"],
        "category": row["category"],
        "icon": row["icon"],
    })

    return title, body, metadata


def sync_medals(conn) -> None:
    """Detect new medal awards and insert award + notification records."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT user_id, code, name, description, category, medal_type,
                   icon, current_value, highest_tier_level, highest_tier_name
            FROM analytics.mart_user_medals
            WHERE highest_tier_level IS NOT NULL
        """)
        qualified = cur.fetchall()
        logger.info("Found %d qualified (user, medal, tier) rows in analytics", len(qualified))

        cur.execute("SELECT user_id, medal_code, tier_level FROM public.medal_award")
        existing = {(r["user_id"], r["medal_code"], r["tier_level"]) for r in cur.fetchall()}
        logger.info("Found %d existing awards in public.medal_award", len(existing))

        new_awards = [
            row for row in qualified
            if (row["user_id"], row["code"], row["highest_tier_level"]) not in existing
        ]

        if not new_awards:
            logger.info("No new awards to sync")
            return

        logger.info("Inserting %d new awards in batches of %d", len(new_awards), BATCH_SIZE)

        award_rows = []
        notif_rows = []
        user_ids = set()

        for row in new_awards:
            award_rows.append((
                row["user_id"],
                row["code"],
                row["highest_tier_level"],
                row["highest_tier_name"],
                row["current_value"],
            ))
            user_ids.add(row["user_id"])

            title, body, metadata = build_notification(row)
            notif_rows.append((
                row["user_id"],
                "medal_awarded",
                title,
                body,
                "/medals",
                metadata,
            ))

    with conn.cursor() as cur:
        for i in range(0, len(award_rows), BATCH_SIZE):
            batch = award_rows[i:i + BATCH_SIZE]
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO public.medal_award
                    (user_id, medal_code, tier_level, tier_name, metric_value_at_award)
                VALUES %s
                ON CONFLICT ON CONSTRAINT uq_medal_award_user_medal_tier DO NOTHING
                """,
                batch,
                page_size=BATCH_SIZE,
            )
            logger.info("  awards batch %d-%d inserted", i + 1, min(i + BATCH_SIZE, len(award_rows)))

        for i in range(0, len(notif_rows), BATCH_SIZE):
            batch = notif_rows[i:i + BATCH_SIZE]
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO public.notification
                    (user_id, notification_type, title, body, link, metadata)
                VALUES %s
                """,
                batch,
                page_size=BATCH_SIZE,
            )
            logger.info("  notifications batch %d-%d inserted", i + 1, min(i + BATCH_SIZE, len(notif_rows)))

    conn.commit()
    logger.info(
        "Awarded %d new medals to %d users, created %d notifications",
        len(award_rows),
        len(user_ids),
        len(notif_rows),
    )


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "staging"
    logger.info("=== Medal sync (target: %s) ===", target)

    creds = get_credentials(target)

    host = os.environ.get("DBT_HOST", "localhost")
    port = os.environ.get("DBT_PORT", "5433")

    conn = psycopg2.connect(
        host=host,
        port=int(port),
        user=creds["username"],
        password=creds["password"],
        dbname=creds["dbname"],
    )
    conn.autocommit = False

    try:
        sync_medals(conn)
    except Exception:
        conn.rollback()
        logger.exception("Medal sync failed, rolled back")
        raise
    finally:
        conn.close()

    logger.info("=== Medal sync complete ===")


if __name__ == "__main__":
    main()
