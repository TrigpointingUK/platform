"""
Open Graph endpoints for social media preview HTML and images.

Provides OG meta tag HTML pages for social media crawlers and
on-demand image generation for preview cards. Also serves
content-rich SEO HTML for search engine crawlers (Googlebot, bingbot).
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from api.crud.area import get_county_name_for_trig
from api.db.database import get_db
from api.models import TLog, Trig
from api.models.user import User
from api.services.opengraph_service import OpenGraphService
from api.utils.condition_mapping import get_condition_description

logger = logging.getLogger(__name__)

trigs_router = APIRouter()
logs_router = APIRouter()


def _canonical_base() -> str:
    """Return the canonical base URL for the site (not the API)."""
    from api.core.config import settings

    if settings.ENVIRONMENT == "staging":
        return "https://trigpointing.me"
    return "https://trigpointing.uk"


@trigs_router.get(
    "/{trig_id}/opengraph",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def get_trig_opengraph_html(
    trig_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Return an HTML page with OG meta tags and structured data for a trig.

    Consumed by social media crawlers and search engine bots (Googlebot, bingbot).
    Includes JSON-LD Place/GeoCoordinates, semantic HTML content, and breadcrumbs.
    """
    trig = db.query(Trig).filter(Trig.id == trig_id).first()
    if not trig:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    svc = OpenGraphService()
    try:
        image_url = svc.get_or_create_trig_image(trig_id, db)
    except Exception as e:
        logger.error("Failed to generate OG image for trig %d: %s", trig_id, e)
        image_url = ""

    parts: list[str] = [str(trig.osgb_gridref)]
    if trig.osgb_height:
        parts.append(f"{float(trig.osgb_height):.0f}m")
    if trig.type_name:
        parts.append(str(trig.type_name))
    description = f"Trigpoint at {', '.join(parts)}"

    site_base = _canonical_base()
    canonical_url = f"{site_base}/trigs/{trig_id}"
    title = f"{trig.waypoint} \u2013 {trig.name}"

    county = get_county_name_for_trig(db, trig_id) or ""
    condition_label = (
        get_condition_description(str(trig.condition)) if trig.condition else ""
    )

    html = svc.generate_trig_seo_html(
        trig=trig,
        title=title,
        description=description,
        image_url=image_url,
        canonical_url=canonical_url,
        site_base=site_base,
        county=county,
        condition_label=condition_label,
    )
    return HTMLResponse(content=html, headers={"Cache-Control": "public, max-age=3600"})


@trigs_router.get(
    "/{trig_id}/opengraph-image",
    include_in_schema=False,
)
def get_trig_opengraph_image(
    trig_id: int,
    refresh: bool = False,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Generate the OG image if needed and redirect to the S3 URL."""
    trig = db.query(Trig).filter(Trig.id == trig_id).first()
    if not trig:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    svc = OpenGraphService()
    try:
        if refresh:
            svc.delete_image("trigs", trig_id)
        image_url = svc.get_or_create_trig_image(trig_id, db)
    except Exception as e:
        logger.error("Failed to generate OG image for trig %d: %s", trig_id, e)
        raise HTTPException(status_code=500, detail="Image generation failed")

    if refresh:
        image_url += f"?t={int(time.time())}"
    return RedirectResponse(url=image_url, status_code=302)


@logs_router.get(
    "/{log_id}/opengraph",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def get_log_opengraph_html(
    log_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Return an HTML page with OG meta tags for a log (consumed by social media crawlers)."""
    log = db.query(TLog).filter(TLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    trig = db.query(Trig).filter(Trig.id == log.trig_id).first()
    user = db.query(User).filter(User.id == log.user_id).first()

    svc = OpenGraphService()
    try:
        image_url = svc.get_or_create_log_image(log_id, db)
    except Exception as e:
        logger.error("Failed to generate OG image for log %d: %s", log_id, e)
        image_url = ""

    trig_name = str(trig.name) if trig else "Unknown Trig"
    user_name = str(user.name) if user else "Unknown User"

    desc_parts = [f"Visit by {user_name}"]
    if log.date:
        desc_parts.append(f"on {log.date.strftime('%-d %B %Y')}")
    if log.condition:
        desc_parts.append(f"\u2013 {get_condition_description(str(log.condition))}")
    description = " ".join(desc_parts)

    canonical_url = f"{_canonical_base()}/logs/{log_id}"
    title = f"Log #{log_id} \u2013 {trig_name}"

    html = svc.generate_og_html(
        title=title,
        description=description,
        image_url=image_url,
        canonical_url=canonical_url,
    )
    return HTMLResponse(content=html, headers={"Cache-Control": "public, max-age=3600"})


@logs_router.get(
    "/{log_id}/opengraph-image",
    include_in_schema=False,
)
def get_log_opengraph_image(
    log_id: int,
    refresh: bool = False,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Generate the OG image if needed and redirect to the S3 URL."""
    log = db.query(TLog).filter(TLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    svc = OpenGraphService()
    try:
        if refresh:
            svc.delete_image("logs", log_id)
        image_url = svc.get_or_create_log_image(log_id, db)
    except Exception as e:
        logger.error("Failed to generate OG image for log %d: %s", log_id, e)
        raise HTTPException(status_code=500, detail="Image generation failed")

    if refresh:
        image_url += f"?t={int(time.time())}"
    return RedirectResponse(url=image_url, status_code=302)
