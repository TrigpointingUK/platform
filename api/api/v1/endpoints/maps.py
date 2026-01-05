"""
Map-related endpoints.

Currently includes a placeholder thumbnail endpoint for KMZ exports.
"""

import io

from fastapi import APIRouter
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont

router = APIRouter()


@router.get("/thumb/{trig_id}")
def get_map_thumbnail(trig_id: int):
    """
    Return a placeholder map thumbnail image for a trigpoint.

    This is intentionally a simple server-generated PNG (no OS imagery embedded).
    """
    # Small, deterministic placeholder image
    width, height = 320, 240
    img = Image.new("RGB", (width, height), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # Render centred text
    title = "OS map thumbnail"
    subtitle = "TBC"
    meta = f"Trig {trig_id}"

    def _centre_text(y: int, text: str) -> int:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) // 2
        draw.text((x, y), text, fill=(30, 30, 30), font=font)
        # Pillow stubs type these values loosely; normalise to int for mypy.
        return int(y + (bbox[3] - bbox[1]) + 8)

    y = 30
    y = _centre_text(y, title)
    y = _centre_text(y, subtitle)
    _centre_text(y + 10, meta)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    png_bytes = out.getvalue()

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            # Safe caching for placeholders; can increase later when made real
            "Cache-Control": "public, max-age=3600",
            "X-Placeholder": "TBC",
        },
    )
