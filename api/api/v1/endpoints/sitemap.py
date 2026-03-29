"""
Sitemap endpoint — generates a sitemap XML for search engine consumption.

Includes static pages and dynamic pages for all trigs (plus photo sub-pages
for trigs that have at least one photo).
"""

import logging
from datetime import date, datetime
from xml.sax.saxutils import (
    escape as escape_xml,  # nosec B406 - used for XML generation, not parsing untrusted input
)

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.core.config import settings
from api.utils.cache_decorator import cached

logger = logging.getLogger(__name__)

router = APIRouter()


def _site_base_url() -> str:
    if settings.ENVIRONMENT == "production":
        return "https://trigpointing.uk"
    return "https://trigpointing.me"


def _format_date(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return value.isoformat()


@router.get(
    "",
    response_class=Response,
    responses={200: {"content": {"application/xml": {}}}},
)
@cached(resource_type="sitemap", ttl=86400, subresource="xml")
def get_sitemap(db: Session = Depends(get_db)):
    """Generate a sitemap XML listing all public pages."""

    base = _site_base_url()

    # Static pages
    static_pages = [
        ("/", "daily", "1.0"),
        ("/trigs", "daily", "0.8"),
        ("/map", "weekly", "0.6"),
        ("/photos", "daily", "0.7"),
        ("/logs", "daily", "0.6"),
        ("/users", "weekly", "0.5"),
        ("/about", "monthly", "0.3"),
        ("/contact", "monthly", "0.3"),
        ("/attributions", "monthly", "0.2"),
        ("/experiment", "monthly", "0.3"),
        ("/experiment/survey-timeline", "monthly", "0.3"),
        ("/experiment/coordinates", "monthly", "0.2"),
        ("/experiment/trigs-v2", "monthly", "0.3"),
        ("/experiment/3d-model", "monthly", "0.2"),
    ]

    # Trig pages with optional photo flag
    # Single query: all trig IDs with their last-updated date and whether photos exist
    rows = db.execute(text("""
            SELECT
                t.id,
                COALESCE(t.upd_timestamp, t.crt_date) AS last_modified,
                EXISTS (
                    SELECT 1
                    FROM tlog tl
                    JOIN tphoto tp ON tp.tlog_id = tl.id
                    WHERE tl.trig_id = t.id
                      AND tp.deleted_ind = 'N'
                      AND tp.public_ind = 'Y'
                ) AS has_photos
            FROM trig t
            ORDER BY t.id
        """)).fetchall()

    # Build XML
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for path, changefreq, priority in static_pages:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape_xml(base + path)}</loc>")
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")

    for row in rows:
        trig_id = row[0]
        last_mod = _format_date(row[1])
        has_photos = row[2]

        lines.append("  <url>")
        lines.append(f"    <loc>{base}/trigs/{trig_id}</loc>")
        if last_mod:
            lines.append(f"    <lastmod>{last_mod}</lastmod>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append("    <priority>0.8</priority>")
        lines.append("  </url>")

        if has_photos:
            lines.append("  <url>")
            lines.append(f"    <loc>{base}/trigs/{trig_id}/photos</loc>")
            if last_mod:
                lines.append(f"    <lastmod>{last_mod}</lastmod>")
            lines.append("    <changefreq>monthly</changefreq>")
            lines.append("    <priority>0.5</priority>")
            lines.append("  </url>")

    lines.append("</urlset>")

    xml = "\n".join(lines)
    return Response(content=xml, media_type="application/xml")
