"""point photo server urls at the CDN

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-08-11 15:41:02.118374

Photos were served from direct S3 URLs, so every image view by every browser and
bot was a billable S3 GetObject plus egress. They are now fronted by
CloudFlare -> CloudFront -> S3 (see docs/infrastructure/PHOTOS_BEHIND_CLOUDFLARE.md).

The API builds photo_url from server.url via api/utils/url.py:join_url, so this
row is the switch that actually moves traffic onto the CDN. Terraform alone does
nothing until this runs.

Only the hostname is rewritten, via replace(), rather than assigning a whole new
URL. That matters for two reasons:

  * join_url tolerates a base with or without a trailing slash, so the stored
    value could be either form. Swapping the hostname preserves whatever is
    there rather than guessing, which makes the downgrade byte-for-byte exact.
  * Matching on the bucket hostname rather than on server.id means the same
    migration is correct in both databases. tuk_production and tuk_staging share
    an RDS instance and both may carry rows for either bucket; each row follows
    its own bucket to that bucket's CDN hostname.

Both statements are no-ops if the URLs are already switched, so re-running is
safe. A row count of 0 is not an error, but it is logged so it is visible in the
`make migrate-*` audit trail.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

# (bucket hostname served directly from S3, hostname of the CDN in front of it)
HOSTNAME_MAP: tuple[tuple[str, str], ...] = (
    ("trigpointinguk-photos.s3.amazonaws.com", "photos.trigpointing.uk"),
    ("trigpointinguk-test.s3.amazonaws.com", "photos.trigpointing.me"),
)

_SWAP_HOSTNAME = sa.text("""
    UPDATE server
    SET url = replace(url, :from_host, :to_host)
    WHERE url LIKE '%' || :from_host || '%'
    """)


def _log_server_urls(conn: sa.engine.Connection, when: str) -> None:
    """Dump the server table so the migration output is a usable audit trail."""
    rows = conn.execute(
        sa.text("SELECT id, name, url FROM server ORDER BY id")
    ).fetchall()
    logger.info("server table %s migration (%d rows):", when, len(rows))
    for row in rows:
        logger.info("  id=%s name=%s url=%s", row.id, row.name, row.url)


def _swap(conn: sa.engine.Connection, from_host: str, to_host: str) -> None:
    result = conn.execute(_SWAP_HOSTNAME, {"from_host": from_host, "to_host": to_host})
    logger.info(
        "Rewrote %s -> %s in server.url: %d row(s) updated",
        from_host,
        to_host,
        result.rowcount,
    )


def upgrade() -> None:
    """Point photo server URLs at the CDN hostnames."""
    conn = op.get_bind()
    _log_server_urls(conn, "before")

    for from_host, to_host in HOSTNAME_MAP:
        _swap(conn, from_host, to_host)

    _log_server_urls(conn, "after")


def downgrade() -> None:
    """Point photo server URLs back at the direct S3 bucket hostnames.

    The S3 buckets remain publicly readable and were never locked down to the
    CDN, so rolling back restores fully working URLs with no other change needed.
    """
    conn = op.get_bind()
    _log_server_urls(conn, "before")

    for from_host, to_host in HOSTNAME_MAP:
        _swap(conn, to_host, from_host)

    _log_server_urls(conn, "after")
