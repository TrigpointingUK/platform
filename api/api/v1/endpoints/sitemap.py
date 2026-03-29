"""
Sitemap endpoint — generates a sitemap index + paginated sub-sitemaps.

The sitemap protocol limits each file to 50,000 URLs, so we split into:
  - /v1/sitemap        → sitemap index listing all sub-sitemaps
  - /v1/sitemap/static → static pages (home, about, experiments, etc.)
  - /v1/sitemap/trigs?page=N → trig detail pages, paginated
  - /v1/sitemap/photos → trig photo pages (only trigs with photos)
"""

import logging
from datetime import date, datetime
from xml.sax.saxutils import (
    escape as escape_xml,  # nosec B406 - used for XML generation, not parsing untrusted input
)

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.core.config import settings
from api.utils.cache_decorator import cached

logger = logging.getLogger(__name__)

router = APIRouter()

URLS_PER_PAGE = 50000


def _site_base_url() -> str:
    if settings.ENVIRONMENT == "production":
        return "https://trigpointing.uk"
    return "https://trigpointing.me"


def _api_base_url() -> str:
    if settings.ENVIRONMENT == "production":
        return "https://api.trigpointing.uk"
    return "https://api.trigpointing.me"


def _format_date(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return value.isoformat()


def _xml_response(xml: str) -> Response:
    return Response(content=xml, media_type="application/xml")


# ── Sitemap index ────────────────────────────────────────────────────────────


@router.get(
    "",
    response_class=Response,
    responses={200: {"content": {"application/xml": {}}}},
)
@cached(resource_type="sitemap", ttl=86400, subresource="index")
def get_sitemap_index(db: Session = Depends(get_db)):
    """Sitemap index listing all sub-sitemaps."""

    api = _api_base_url()

    trig_count = db.execute(text("SELECT COUNT(*) FROM trig")).scalar() or 0
    trig_pages = max(1, (trig_count + URLS_PER_PAGE - 1) // URLS_PER_PAGE)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "  <sitemap>",
        f"    <loc>{api}/v1/sitemap/static</loc>",
        "  </sitemap>",
    ]

    for page in range(1, trig_pages + 1):
        lines.append("  <sitemap>")
        lines.append(f"    <loc>{api}/v1/sitemap/trigs?page={page}</loc>")
        lines.append("  </sitemap>")

    lines.append("  <sitemap>")
    lines.append(f"    <loc>{api}/v1/sitemap/photos</loc>")
    lines.append("  </sitemap>")

    lines.append("</sitemapindex>")
    return _xml_response("\n".join(lines))


# ── Static pages ─────────────────────────────────────────────────────────────


@router.get(
    "/static",
    response_class=Response,
    responses={200: {"content": {"application/xml": {}}}},
)
@cached(resource_type="sitemap", ttl=86400, subresource="static")
def get_sitemap_static():
    """Sitemap for static (non-database-driven) pages."""

    base = _site_base_url()

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

    lines.append("</urlset>")
    return _xml_response("\n".join(lines))


# ── Trig detail pages (paginated) ───────────────────────────────────────────


@router.get(
    "/trigs",
    response_class=Response,
    responses={200: {"content": {"application/xml": {}}}},
)
@cached(resource_type="sitemap", ttl=86400, subresource="trigs-{page}")
def get_sitemap_trigs(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
):
    """Sitemap for trig detail pages, paginated at 50,000 per page."""

    base = _site_base_url()
    offset = (page - 1) * URLS_PER_PAGE

    rows = db.execute(
        text("""
            SELECT id, COALESCE(upd_timestamp, crt_date) AS last_modified
            FROM trig
            ORDER BY id
            LIMIT :limit OFFSET :offset
        """),
        {"limit": URLS_PER_PAGE, "offset": offset},
    ).fetchall()

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for trig_id, last_modified in rows:
        last_mod = _format_date(last_modified)
        lines.append("  <url>")
        lines.append(f"    <loc>{base}/trigs/{trig_id}</loc>")
        if last_mod:
            lines.append(f"    <lastmod>{last_mod}</lastmod>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append("    <priority>0.8</priority>")
        lines.append("  </url>")

    lines.append("</urlset>")
    return _xml_response("\n".join(lines))


# ── Trig photo pages ────────────────────────────────────────────────────────


@router.get(
    "/photos",
    response_class=Response,
    responses={200: {"content": {"application/xml": {}}}},
)
@cached(resource_type="sitemap", ttl=86400, subresource="photos")
def get_sitemap_photos(db: Session = Depends(get_db)):
    """Sitemap for trig photo pages (only trigs that have public photos)."""

    base = _site_base_url()

    rows = db.execute(text("""
        SELECT DISTINCT t.id, COALESCE(t.upd_timestamp, t.crt_date) AS last_modified
        FROM trig t
        JOIN tlog tl ON tl.trig_id = t.id
        JOIN tphoto tp ON tp.tlog_id = tl.id
        WHERE tp.deleted_ind = 'N'
          AND tp.public_ind = 'Y'
        ORDER BY t.id
    """)).fetchall()

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for trig_id, last_modified in rows:
        last_mod = _format_date(last_modified)
        lines.append("  <url>")
        lines.append(f"    <loc>{base}/trigs/{trig_id}/photos</loc>")
        if last_mod:
            lines.append(f"    <lastmod>{last_mod}</lastmod>")
        lines.append("    <changefreq>monthly</changefreq>")
        lines.append("    <priority>0.5</priority>")
        lines.append("  </url>")

    lines.append("</urlset>")
    return _xml_response("\n".join(lines))
