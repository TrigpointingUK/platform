"""
Open Graph image generation and S3 caching service.

Generates 1200x630 social media preview images for trigs and logs,
caches them in S3, and serves OG HTML for social media crawlers.
"""

import io
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Union

import boto3
import numpy as np
from botocore.exceptions import ClientError
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models import TLog, TPhoto, Trig
from api.models.condition import Condition
from api.models.server import Server
from api.models.user import User
from api.utils.condition_mapping import get_condition_description
from api.utils.url import join_url

logger = logging.getLogger(__name__)

WIDTH = 1200
HEIGHT = 630
PADDING = 40
PHOTO_TYPES_PRIORITY = ["T", "F", "L", "O", "P"]

RES_DIR_CANDIDATES = [
    Path("/app/res"),
    Path(__file__).parent.parent.parent / "res",
]


def _find_res_dir() -> Path:
    for p in RES_DIR_CANDIDATES:
        if p.exists():
            return p
    return RES_DIR_CANDIDATES[-1]


def _load_font(size: int, bold: bool = False) -> Union[ImageFont.FreeTypeFont, Any]:
    """Load Inter variable font at the given size. Falls back to system fonts."""
    res = _find_res_dir()
    font_path = res / "fonts" / "InterVariable.ttf"
    if font_path.exists():
        try:
            font = ImageFont.truetype(str(font_path), size)
            if bold:
                font.set_variation_by_axes([700])
            return font
        except Exception:  # nosec B110 - intentional fallback to next font
            pass

    for fallback in [
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        (
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ),
    ]:
        if Path(fallback).exists():
            try:
                return ImageFont.truetype(fallback, size)
            except Exception:  # nosec B110 - intentional fallback to default font
                pass

    return ImageFont.load_default()


def _draw_gradient(img: Image.Image) -> None:
    """Draw a dark gradient background onto img."""
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(15 + 10 * ratio)
        g = int(25 + 15 * ratio)
        b = int(45 + 20 * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))


def _round_corners(img: Image.Image, radius: int) -> Image.Image:
    """Apply rounded corners to an RGBA image."""
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, img.size[0], img.size[1]], radius=radius, fill=255)
    result = img.copy()
    result.putalpha(mask)
    return result


def _add_drop_shadow(
    img: Image.Image, offset: int = 4, blur_radius: int = 8
) -> Image.Image:
    """Create a shadow behind an RGBA image, returning a larger canvas."""
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow_layer = Image.new("RGBA", img.size, (0, 0, 0, 80))
    shadow.paste(shadow_layer, mask=img.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    canvas_w = img.size[0] + offset + blur_radius * 2
    canvas_h = img.size[1] + offset + blur_radius * 2
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    canvas.paste(shadow, (blur_radius + offset, blur_radius + offset))
    canvas.paste(img, (blur_radius, blur_radius), mask=img)
    return canvas


def _crop_center_square(img: Image.Image) -> Image.Image:
    """Crop the centre square from an image."""
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def _make_circular(img: Image.Image) -> Image.Image:
    """Crop image into a circle with alpha channel."""
    img = _crop_center_square(img).convert("RGBA")
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([0, 0, img.size[0], img.size[1]], fill=255)
    img.putalpha(mask)
    return img


def _load_condition_icon(
    condition_code: str, db: Session, size: int = 20
) -> Optional[Image.Image]:
    """Load a condition icon PNG from the path stored in the database."""
    code = str(condition_code).upper()
    condition = db.query(Condition).filter(Condition.code == code).first()
    if not condition or not condition.icon_file:
        return None
    filename = str(condition.icon_file)
    res = _find_res_dir()
    icon_path = res / "icons" / "conditions" / filename
    if not icon_path.exists():
        return None
    try:
        icon = Image.open(icon_path).convert("RGBA")
        return icon.resize((size, size), Image.Resampling.LANCZOS)
    except Exception:
        return None


def _get_station_number(trig: Trig) -> str:
    """Return the best available station number from the trig's variants."""
    for attr in ("stn_number_active", "stn_number_passive", "stn_number_osgb36"):
        val = getattr(trig, attr, None)
        if val and str(val).strip():
            return str(val).strip()
    if trig.stn_number and str(trig.stn_number).strip():
        return str(trig.stn_number).strip()
    return ""


def _draw_uk_map(trig: Trig) -> Image.Image:
    """Draw a small UK map with a dot at the trig location."""
    res = _find_res_dir()
    map_path = res / "stretched53_default.png"
    calib_path = res / "stretched53_default.json"

    if not map_path.exists() or not calib_path.exists():
        placeholder = Image.new("RGBA", (200, 200), (30, 50, 80, 255))
        return placeholder

    base = Image.open(map_path).convert("RGBA")
    with open(calib_path, "r") as f:
        d = json.load(f)
    affine = np.array(d["affine"], dtype=float)

    lon, lat = float(trig.wgs_long), float(trig.wgs_lat)
    x = affine[0][0] * lon + affine[0][1] * lat + affine[0][2]
    y = affine[1][0] * lon + affine[1][1] * lat + affine[1][2]

    target_size = 200
    scale = target_size / max(base.size)
    base = base.resize(
        (int(base.size[0] * scale), int(base.size[1] * scale)),
        Image.Resampling.LANCZOS,
    )
    x, y = x * scale, y * scale

    tint = Image.new("RGBA", base.size, (240, 240, 220, 70))
    tint.putalpha(base.split()[3])
    base = Image.alpha_composite(base, tint)

    draw = ImageDraw.Draw(base)
    r = 8
    draw.ellipse([x - r, y - r, x + r, y + r], fill=(234, 40, 40, 255))

    return base


def _select_photos_for_trig(db: Session, trig_id: int, limit: int = 4) -> list[TPhoto]:
    """Select a diverse set of photos for a trig, preferring variety of types."""
    photos = (
        db.query(TPhoto)
        .join(TLog, TPhoto.tlog_id == TLog.id)
        .filter(TLog.trig_id == trig_id)
        .filter(TPhoto.deleted_ind != "Y")
        .order_by(TPhoto.crt_timestamp.desc())
        .limit(200)
        .all()
    )

    selected: list[TPhoto] = []
    used_types: set[str] = set()

    for ptype in PHOTO_TYPES_PRIORITY:
        if len(selected) >= limit:
            break
        for p in photos:
            if p.type == ptype and p.id not in {s.id for s in selected}:
                selected.append(p)
                used_types.add(ptype)
                break

    # Fill remaining slots, preferring types not yet represented
    remaining = [p for p in photos if p.id not in {s.id for s in selected}]
    for p in remaining:
        if len(selected) >= limit:
            break
        if p.type not in used_types:
            selected.append(p)
            used_types.add(str(p.type))

    # Last resort: allow duplicate types if we still need more
    for p in remaining:
        if len(selected) >= limit:
            break
        if p.id not in {s.id for s in selected}:
            selected.append(p)

    return selected[:limit]


def _select_photos_for_log(
    db: Session, log: TLog, trig_id: int, limit: int = 4
) -> list[TPhoto]:
    """Select photos for a log, prioritising the log's own photos then same user."""
    log_photos = (
        db.query(TPhoto)
        .filter(TPhoto.tlog_id == log.id)
        .filter(TPhoto.deleted_ind != "Y")
        .order_by(TPhoto.crt_timestamp.desc())
        .all()
    )

    selected = list(log_photos[:limit])
    if len(selected) >= limit:
        return selected

    used_ids = {p.id for p in selected}
    used_types = {str(p.type) for p in selected}

    # Prefer other photos by the same user on this trig
    if log.user_id:
        user_photos = (
            db.query(TPhoto)
            .join(TLog, TPhoto.tlog_id == TLog.id)
            .filter(TLog.trig_id == trig_id)
            .filter(TLog.user_id == log.user_id)
            .filter(TPhoto.id.notin_(used_ids))
            .filter(TPhoto.deleted_ind != "Y")
            .order_by(TPhoto.crt_timestamp.desc())
            .limit(50)
            .all()
        )
        for p in user_photos:
            if len(selected) >= limit:
                break
            if str(p.type) not in used_types:
                selected.append(p)
                used_ids.add(p.id)
                used_types.add(str(p.type))
        for p in user_photos:
            if len(selected) >= limit:
                break
            if p.id not in used_ids:
                selected.append(p)
                used_ids.add(p.id)

    if len(selected) >= limit:
        return selected[:limit]

    remaining = limit - len(selected)
    supplement = _select_photos_for_trig(db, trig_id, limit=remaining + 10)
    for p in supplement:
        if len(selected) >= limit:
            break
        if p.id not in used_ids:
            selected.append(p)

    return selected[:limit]


def _download_photo(db: Session, photo: TPhoto) -> Optional[Image.Image]:
    """Download a photo from S3 or via its server URL."""
    try:
        s3 = boto3.client("s3")
        key = str(photo.filename)
        bucket = settings.PHOTOS_S3_BUCKET
        resp = s3.get_object(Bucket=bucket, Key=key)
        data = resp["Body"].read()
        return Image.open(io.BytesIO(data))
    except Exception:
        try:
            server = db.query(Server).filter(Server.id == photo.server_id).first()
            if server:
                import urllib.request

                url = join_url(str(server.url), str(photo.filename))
                with urllib.request.urlopen(
                    url, timeout=10
                ) as resp:  # nosec B310 - URL is constructed from trusted DB data
                    return Image.open(io.BytesIO(resp.read()))
        except Exception as e:
            logger.warning("Failed to download photo %d: %s", photo.id, e)
    return None


def _download_avatar(user: User) -> Optional[Image.Image]:
    """Download a user's avatar from S3."""
    try:
        s3 = boto3.client("s3")
        key = f"{user.id}.jpg"
        resp = s3.get_object(Bucket=settings.AVATARS_S3_BUCKET, Key=key)
        data = resp["Body"].read()
        return Image.open(io.BytesIO(data))
    except Exception:
        return None


_BNG_ORIGIN = (-238375.0, 1376256.0)
_BNG_RESOLUTIONS = [
    896,
    448,
    224,
    112,
    56,
    28,
    14,
    7,
    3.5,
    1.75,
    0.875,
    0.4375,
    0.21875,
    0.109375,
]


def _fetch_os_map_tile(lat: float, lon: float, zoom: int = 8) -> Optional[Image.Image]:
    """Fetch a 2x2 grid of OS Paper (Leisure_27700) tiles centred on lat/lon."""
    if not settings.OS_API_KEY:
        return None

    from api.services.coordinate_service import convert_wgs84_to_osgb

    easting, northing, _ = convert_wgs84_to_osgb(lon, lat)

    tile_cache_dir = Path(settings.TILE_CACHE_DIR) if settings.TILE_CACHE_DIR else None
    layer = "Leisure_27700"
    zoom = min(zoom, len(_BNG_RESOLUTIONS) - 1)
    res = _BNG_RESOLUTIONS[zoom]
    tile_span = res * 256

    center_x = (easting - _BNG_ORIGIN[0]) / tile_span
    center_y = (_BNG_ORIGIN[1] - northing) / tile_span

    base_tx = int(center_x)
    base_ty = int(center_y)
    frac_x = center_x - base_tx
    frac_y = center_y - base_ty
    tx_start = base_tx - 1 if frac_x < 0.5 else base_tx
    ty_start = base_ty - 1 if frac_y < 0.5 else base_ty

    tiles: list[Image.Image] = []
    for dy in range(2):
        for dx in range(2):
            tx, ty = tx_start + dx, ty_start + dy
            tile_img = _fetch_single_tile(layer, zoom, tx, ty, tile_cache_dir)
            if tile_img is None:
                return None
            tiles.append(tile_img)

    composite = Image.new("RGB", (512, 512))
    composite.paste(tiles[0], (0, 0))
    composite.paste(tiles[1], (256, 0))
    composite.paste(tiles[2], (0, 256))
    composite.paste(tiles[3], (256, 256))

    px_x = int((center_x - tx_start) * 256)
    px_y = int((center_y - ty_start) * 256)
    half = 200
    left = max(0, min(px_x - half, 512 - 2 * half))
    top = max(0, min(px_y - half, 512 - 2 * half))

    return composite.crop((left, top, left + 2 * half, top + 2 * half))


def _fetch_single_tile(
    layer: str, z: int, x: int, y: int, cache_dir: Optional[Path]
) -> Optional[Image.Image]:
    """Fetch a single OS tile, using EFS cache if available."""
    if cache_dir:
        cached = cache_dir / layer / str(z) / str(x) / f"{y}.png"
        if cached.exists():
            try:
                return Image.open(cached).convert("RGB")
            except Exception:  # nosec B110 - fallback to API fetch
                pass

    import urllib.request

    url = (
        f"https://api.os.uk/maps/raster/v1/zxy/{layer}/{z}/{x}/{y}.png"
        f"?key={settings.OS_API_KEY}"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:  # nosec B310
            data = resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        if cache_dir:
            try:
                tile_path = cache_dir / layer / str(z) / str(x) / f"{y}.png"
                tile_path.parent.mkdir(parents=True, exist_ok=True)
                with open(tile_path, "wb") as f:
                    f.write(data)
            except Exception:  # nosec B110 - caching is best-effort
                pass
        return img
    except Exception as e:
        logger.warning("Failed to fetch OS tile z=%d x=%d y=%d: %s", z, x, y, e)
        return None


def _compose_photo_strip(
    canvas: Image.Image, photos: list[Image.Image], y_offset: int
) -> None:
    """Arrange photos in a horizontal strip on the canvas."""
    if not photos:
        return

    available_w = WIDTH - 2 * PADDING
    photo_h = 260
    gap = 16
    count = len(photos)
    photo_w = (available_w - gap * (count - 1)) // count

    x = PADDING
    for img in photos:
        thumb = _crop_center_square(img).resize(
            (photo_w, photo_h), Image.Resampling.LANCZOS
        )
        thumb = thumb.convert("RGBA")
        thumb = _round_corners(thumb, 12)
        with_shadow = _add_drop_shadow(thumb, offset=3, blur_radius=6)
        canvas.paste(with_shadow, (x - 6, y_offset - 6), mask=with_shadow)
        x += photo_w + gap


class OpenGraphService:
    """Generates and caches Open Graph preview images in S3."""

    def __init__(self) -> None:
        try:
            self.s3_client = boto3.client("s3")
            self.bucket = settings.OPENGRAPH_S3_BUCKET
        except Exception as e:
            logger.error("Failed to initialise S3 client for OG images: %s", e)
            self.s3_client = None

    def _s3_key(self, entity_type: str, entity_id: int) -> str:
        return f"{entity_type}/{entity_id}.png"

    def get_image_url(self, entity_type: str, entity_id: int) -> str:
        key = self._s3_key(entity_type, entity_id)
        return f"https://{self.bucket}.s3.eu-west-1.amazonaws.com/{key}"

    def check_image_fresh(self, entity_type: str, entity_id: int) -> bool:
        """Return True if the cached image exists and is within TTL."""
        if not self.s3_client:
            return False
        key = self._s3_key(entity_type, entity_id)
        try:
            resp = self.s3_client.head_object(Bucket=self.bucket, Key=key)
            last_modified = resp["LastModified"]
            ttl = timedelta(days=settings.OPENGRAPH_IMAGE_TTL_DAYS)
            return datetime.now(timezone.utc) - last_modified < ttl
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.warning("S3 HEAD failed for %s: %s", key, e)
            return False

    def upload_image(self, entity_type: str, entity_id: int, img_bytes: bytes) -> str:
        """Upload generated image to S3, returning the public URL."""
        key = self._s3_key(entity_type, entity_id)
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=img_bytes,
            ContentType="image/png",
            CacheControl="public, max-age=604800",
            ACL="public-read",
        )
        logger.info("Uploaded OG image: %s", key)
        return self.get_image_url(entity_type, entity_id)

    def delete_image(self, entity_type: str, entity_id: int) -> None:
        """Delete a cached OG image from S3."""
        if not self.s3_client:
            return
        key = self._s3_key(entity_type, entity_id)
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
            logger.info("Deleted OG image: %s", key)
        except ClientError as e:
            logger.warning("S3 DELETE failed for %s: %s", key, e)

    def get_or_create_trig_image(self, trig_id: int, db: Session) -> str:
        """Return the S3 URL for the trig's OG image, generating if needed."""
        if self.check_image_fresh("trigs", trig_id):
            return self.get_image_url("trigs", trig_id)

        trig = db.query(Trig).filter(Trig.id == trig_id).first()
        if not trig:
            raise ValueError(f"Trig {trig_id} not found")

        img_bytes = self._generate_trig_image(trig, db)
        return self.upload_image("trigs", trig_id, img_bytes)

    def get_or_create_log_image(self, log_id: int, db: Session) -> str:
        """Return the S3 URL for the log's OG image, generating if needed."""
        if self.check_image_fresh("logs", log_id):
            return self.get_image_url("logs", log_id)

        log = db.query(TLog).filter(TLog.id == log_id).first()
        if not log:
            raise ValueError(f"Log {log_id} not found")

        trig = db.query(Trig).filter(Trig.id == log.trig_id).first()
        user = db.query(User).filter(User.id == log.user_id).first()

        img_bytes = self._generate_log_image(log, trig, user, db)
        return self.upload_image("logs", log_id, img_bytes)

    def _generate_trig_image(self, trig: Trig, db: Session) -> bytes:
        """Compose a 1200x630 OG image for a trig."""
        canvas = Image.new("RGBA", (WIDTH, HEIGHT))
        _draw_gradient(canvas)

        font_title = _load_font(56, bold=True)
        font_subtitle = _load_font(32)
        font_meta = _load_font(26)
        font_detail = _load_font(24)
        font_brand = _load_font(32)

        draw = ImageDraw.Draw(canvas)

        # UK map with location dot (top-left)
        uk_map = _draw_uk_map(trig)
        map_x, map_y = PADDING, PADDING
        canvas.paste(uk_map, (map_x, map_y), mask=uk_map)

        # T:UK logo (top-right)
        self._draw_logo(canvas)

        # Title: waypoint - name
        text_x = map_x + uk_map.size[0] + 30
        text_y = PADDING + 15
        title = f"{trig.waypoint} \u2013 {trig.name}"
        draw.text((text_x, text_y), str(title), font=font_title, fill=(255, 255, 255))

        # Subtitle: gridref . height (3dp)
        text_y += 74
        parts: list[str] = [str(trig.osgb_gridref)]
        if trig.osgb_height:
            parts.append(f"{float(trig.osgb_height):.3f}m")
        subtitle = "  \u00b7  ".join(parts)
        draw.text((text_x, text_y), subtitle, font=font_subtitle, fill=(220, 235, 245))

        # Meta line: type, "Condition:" icon + text
        text_y += 50
        meta_x = text_x
        if trig.type_name:
            type_text = str(trig.type_name)
            draw.text((meta_x, text_y), type_text, font=font_meta, fill=(190, 210, 225))
            bbox = draw.textbbox((meta_x, text_y), type_text, font=font_meta)
            meta_x = int(bbox[2]) + 20

        if trig.condition:
            cond_label = "Condition: "
            draw.text(
                (meta_x, text_y), cond_label, font=font_meta, fill=(190, 210, 225)
            )
            bbox = draw.textbbox((meta_x, text_y), cond_label, font=font_meta)
            meta_x = int(bbox[2]) + 2
            cond_icon = _load_condition_icon(str(trig.condition), db, size=26)
            if cond_icon:
                canvas.paste(cond_icon, (meta_x, text_y + 1), mask=cond_icon)
                meta_x += 30
            cond_desc = get_condition_description(str(trig.condition))
            draw.text((meta_x, text_y), cond_desc, font=font_meta, fill=(190, 210, 225))

        # Detail line: WGS84 coords, flush bracket, station number
        text_y += 44
        detail_parts: list[str] = []
        detail_parts.append(
            f"WGS84: {float(trig.wgs_lat):.7f}, {float(trig.wgs_long):.7f}"
        )
        fb = str(trig.fb_number).strip() if trig.fb_number else ""
        if fb:
            detail_parts.append(f"Flush Bracket: {fb}")
        stn = _get_station_number(trig)
        if stn:
            detail_parts.append(f"Station: {stn}")
        draw.text(
            (text_x, text_y),
            "  \u00b7  ".join(detail_parts),
            font=font_detail,
            fill=(170, 190, 210),
        )

        # Photo strip: 3 photos + OS map tile on the right
        photos_db = _select_photos_for_trig(db, int(trig.id), limit=3)
        photo_images = []
        for p in photos_db:
            img = _download_photo(db, p)
            if img:
                photo_images.append(img)

        os_tile = _fetch_os_map_tile(float(trig.wgs_lat), float(trig.wgs_long))
        if os_tile:
            photo_images.append(os_tile)

        photo_y = PADDING + uk_map.size[1] + 40
        if photo_images:
            _compose_photo_strip(canvas, photo_images, photo_y)
        else:
            draw.text(
                (PADDING, photo_y + 80),
                "No photos yet \u2014 be the first to add one!",
                font=font_meta,
                fill=(150, 170, 190),
            )

        # Branding footer
        footer_url = f"https://trigpointing.uk/trigs/{int(trig.id)}"
        footer_bbox = draw.textbbox((0, 0), footer_url, font=font_brand)
        footer_w = footer_bbox[2] - footer_bbox[0]
        draw.text(
            (WIDTH - PADDING - footer_w, HEIGHT - 50),
            footer_url,
            font=font_brand,
            fill=(255, 255, 255),
        )

        flat = Image.new("RGB", (WIDTH, HEIGHT), (20, 30, 50))
        flat.paste(canvas, mask=canvas)

        buf = io.BytesIO()
        flat.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    def _generate_log_image(
        self,
        log: TLog,
        trig: Optional[Trig],
        user: Optional[User],
        db: Session,
    ) -> bytes:
        """Compose a 1200x630 OG image for a log visit."""
        canvas = Image.new("RGBA", (WIDTH, HEIGHT))
        _draw_gradient(canvas)

        font_trig_name = _load_font(38, bold=True)
        font_subtitle = _load_font(28)
        font_meta = _load_font(28)
        font_detail = _load_font(22)
        font_user = _load_font(44, bold=True)
        font_user_label = _load_font(38)
        font_brand = _load_font(32)

        draw = ImageDraw.Draw(canvas)

        # UK map (top-left)
        if trig:
            uk_map = _draw_uk_map(trig)
        else:
            uk_map = Image.new("RGBA", (200, 200), (30, 50, 80, 255))
        map_x, map_y = PADDING, PADDING
        canvas.paste(uk_map, (map_x, map_y), mask=uk_map)

        # Logo (top-right)
        self._draw_logo(canvas)

        text_x = map_x + uk_map.size[0] + 30
        text_y = PADDING

        # User avatar + "Logged by:" name (top line)
        avatar_size = 48
        avatar_drawn = False
        if user:
            avatar_img = _download_avatar(user)
            if avatar_img:
                avatar_img = _make_circular(
                    avatar_img.resize(
                        (avatar_size, avatar_size), Image.Resampling.LANCZOS
                    )
                )
                canvas.paste(avatar_img, (text_x, text_y + 4), mask=avatar_img)
                avatar_drawn = True

        name_x = text_x + (avatar_size + 12 if avatar_drawn else 0)
        if user:
            label = "Logged by: "
            label_y = text_y + 5
            draw.text(
                (name_x, label_y),
                label,
                font=font_user_label,
                fill=(200, 215, 228),
            )
            label_bbox = draw.textbbox((name_x, label_y), label, font=font_user_label)
            draw.text(
                (int(label_bbox[2]) + 2, text_y),
                str(user.name),
                font=font_user,
                fill=(74, 222, 128),
            )

        # Date and "Condition:" icon + text
        info_y = text_y + 60
        info_x = name_x
        if log.date:
            date_text = log.date.strftime("%-d %B %Y")
            draw.text((info_x, info_y), date_text, font=font_meta, fill=(190, 210, 225))
            bbox = draw.textbbox((info_x, info_y), date_text, font=font_meta)
            info_x = int(bbox[2]) + 20

        if log.condition:
            cond_label = "Condition: "
            draw.text(
                (info_x, info_y), cond_label, font=font_meta, fill=(190, 210, 225)
            )
            bbox = draw.textbbox((info_x, info_y), cond_label, font=font_meta)
            info_x = int(bbox[2]) + 2
            cond_icon = _load_condition_icon(str(log.condition), db, size=26)
            if cond_icon:
                canvas.paste(cond_icon, (info_x, info_y + 1), mask=cond_icon)
                info_x += 30
            cond_desc = get_condition_description(str(log.condition))
            draw.text((info_x, info_y), cond_desc, font=font_meta, fill=(190, 210, 225))

        # Trig name with waypoint
        text_y = info_y + 44
        if trig:
            trig_title = f"{trig.waypoint} \u2013 {trig.name}"
        else:
            trig_title = "Unknown Trig"
        draw.text(
            (text_x, text_y),
            str(trig_title),
            font=font_trig_name,
            fill=(230, 240, 248),
        )

        # Gridref . height (3dp)
        text_y += 48
        if trig:
            parts: list[str] = [str(trig.osgb_gridref)]
            if trig.osgb_height:
                parts.append(f"{float(trig.osgb_height):.3f}m")
            subtitle = "  \u00b7  ".join(parts)
            draw.text(
                (text_x, text_y), subtitle, font=font_subtitle, fill=(210, 225, 238)
            )

        # Detail line: WGS84, flush bracket, station number
        text_y += 38
        if trig:
            detail_parts: list[str] = [
                f"WGS84: {float(trig.wgs_lat):.7f}, {float(trig.wgs_long):.7f}"
            ]
            fb = str(trig.fb_number).strip() if trig.fb_number else ""
            if fb:
                detail_parts.append(f"Flush Bracket: {fb}")
            stn = _get_station_number(trig)
            if stn:
                detail_parts.append(f"Station: {stn}")
            draw.text(
                (text_x, text_y),
                "  \u00b7  ".join(detail_parts),
                font=font_detail,
                fill=(170, 190, 210),
            )

        # Photo strip: 3 photos + OS map tile on the right
        trig_id = int(trig.id) if trig else int(log.trig_id or 0)
        photos_db = _select_photos_for_log(db, log, trig_id, limit=3)
        photo_images = []
        for p in photos_db:
            img = _download_photo(db, p)
            if img:
                photo_images.append(img)

        if trig:
            os_tile = _fetch_os_map_tile(float(trig.wgs_lat), float(trig.wgs_long))
            if os_tile:
                photo_images.append(os_tile)

        photo_y = PADDING + uk_map.size[1] + 70
        if photo_images:
            _compose_photo_strip(canvas, photo_images, photo_y)

        # Branding
        footer_url = f"https://trigpointing.uk/logs/{int(log.id)}"
        footer_bbox = draw.textbbox((0, 0), footer_url, font=font_brand)
        footer_w = footer_bbox[2] - footer_bbox[0]
        draw.text(
            (WIDTH - PADDING - footer_w, HEIGHT - 50),
            footer_url,
            font=font_brand,
            fill=(255, 255, 255),
        )

        flat = Image.new("RGB", (WIDTH, HEIGHT), (20, 30, 50))
        flat.paste(canvas, mask=canvas)

        buf = io.BytesIO()
        flat.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    def _draw_logo(self, canvas: Image.Image) -> None:
        """Draw the T:UK logo with 'TrigpointingUK' text below it."""
        res = _find_res_dir()
        logo_path = res / "tuk_logo.png"
        if not logo_path.exists():
            return
        try:
            logo = Image.open(logo_path).convert("RGBA")
            max_h = 130
            ratio = max_h / logo.height
            logo = logo.resize(
                (int(logo.width * ratio), max_h), Image.Resampling.LANCZOS
            )
            logo_x = WIDTH - PADDING - logo.width
            logo_y = PADDING
            canvas.paste(logo, (logo_x, logo_y), mask=logo)

            brand_text = "TrigpointingUK"
            logo_w = logo.width
            font_size = 36
            font = _load_font(font_size, bold=True)
            draw = ImageDraw.Draw(canvas)
            bbox = draw.textbbox((0, 0), brand_text, font=font)
            text_w = bbox[2] - bbox[0]
            while text_w > logo_w and font_size > 8:
                font_size -= 1
                font = _load_font(font_size, bold=True)
                bbox = draw.textbbox((0, 0), brand_text, font=font)
                text_w = bbox[2] - bbox[0]
            text_x = logo_x + (logo_w - text_w) // 2
            text_y = logo_y + max_h + 4
            draw.text((text_x, text_y), brand_text, font=font, fill=(230, 240, 248))
        except Exception as e:
            logger.warning("Could not draw logo: %s", e)

    def generate_og_html(
        self,
        *,
        title: str,
        description: str,
        image_url: str,
        canonical_url: str,
    ) -> str:
        """Generate a minimal HTML page with OG meta tags and a redirect for humans."""
        from html import escape

        t = escape(title)
        d = escape(description)
        i = escape(image_url)
        u = escape(canonical_url)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{t}</title>
<meta property="og:title" content="{t}"/>
<meta property="og:description" content="{d}"/>
<meta property="og:image" content="{i}"/>
<meta property="og:image:width" content="1200"/>
<meta property="og:image:height" content="630"/>
<meta property="og:url" content="{u}"/>
<meta property="og:type" content="website"/>
<meta property="og:site_name" content="TrigpointingUK"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{t}"/>
<meta name="twitter:description" content="{d}"/>
<meta name="twitter:image" content="{i}"/>
<meta http-equiv="refresh" content="0;url={u}"/>
</head>
<body>
<p>Redirecting to <a href="{u}">{t}</a>&hellip;</p>
<script>window.location.replace("{u}");</script>
</body>
</html>"""
