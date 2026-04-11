"""add has_avatar column to user

Add a boolean has_avatar column to the user table, then bulk-populate it
by listing the S3 avatars bucket.  This lets the frontend skip 404/403
round-trips for users who never uploaded an avatar.

Revision ID: b2f3a4c5d6e7
Revises: afac436783c8
Create Date: 2026-04-11

"""

import logging
import os
import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2f3a4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "afac436783c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

AVATAR_KEY_PATTERN = re.compile(r"^U(\d+)\.jpg$")


def _list_avatar_user_ids() -> set[int]:
    """List the avatars S3 bucket and return the set of user IDs that have objects."""
    try:
        import boto3
    except ImportError:
        logger.warning("boto3 not available — skipping S3 backfill")
        return set()

    bucket = os.getenv("AVATARS_S3_BUCKET", "trigpointinguk-avatars")
    s3 = boto3.client("s3")
    user_ids: set[int] = set()
    continuation_token = None

    while True:
        kwargs: dict = {"Bucket": bucket, "MaxKeys": 1000}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        try:
            resp = s3.list_objects_v2(**kwargs)
        except Exception as exc:
            logger.warning("Failed to list S3 bucket %s: %s", bucket, exc)
            return set()

        for obj in resp.get("Contents", []):
            m = AVATAR_KEY_PATTERN.match(obj["Key"])
            if m:
                user_ids.add(int(m.group(1)))

        if not resp.get("IsTruncated"):
            break
        continuation_token = resp.get("NextContinuationToken")

    logger.info("Found %d avatar objects in S3 bucket %s", len(user_ids), bucket)
    return user_ids


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "has_avatar",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Bulk-populate from S3
    user_ids = _list_avatar_user_ids()
    if user_ids:
        conn = op.get_bind()
        batch_size = 500
        id_list = sorted(user_ids)
        total_updated = 0
        for i in range(0, len(id_list), batch_size):
            batch = id_list[i : i + batch_size]
            placeholders = ", ".join(str(uid) for uid in batch)
            result = conn.execute(
                sa.text(
                    f'UPDATE "user" SET has_avatar = true WHERE id IN ({placeholders})'
                )
            )
            total_updated += result.rowcount
        logger.info("Set has_avatar=true for %d users", total_updated)
    else:
        logger.info("No avatar objects found — all users default to has_avatar=false")


def downgrade() -> None:
    op.drop_column("user", "has_avatar")
