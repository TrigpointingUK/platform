"""
Coordinate conversion API endpoint.

Provides accurate WGS84 <-> OSGB36 conversion using OSTN15/OSGM15 models.
See: docs/decisions/0001-ostn15-coordinate-conversion.md
"""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.api.lifecycle import openapi_lifecycle
from api.services.coordinate_service import (
    convert_osgb_to_wgs84,
    convert_wgs84_to_osgb,
    eastings_northings_to_gridref,
)

router = APIRouter()


class CoordinateInput(BaseModel):
    """Input coordinates (varies based on source CRS)."""

    lat: Optional[float] = Field(None, description="WGS84 latitude in decimal degrees")
    lon: Optional[float] = Field(None, description="WGS84 longitude in decimal degrees")
    e: Optional[int] = Field(None, description="OSGB36 eastings in metres")
    n: Optional[int] = Field(None, description="OSGB36 northings in metres")
    height: Optional[float] = Field(
        None,
        description="Height in metres (ellipsoidal for WGS84, orthometric for OSGB)",
    )
    gridref: Optional[str] = Field(
        None, description="OS National Grid reference (only for OSGB input)"
    )


class CoordinateOutput(BaseModel):
    """Output coordinates (varies based on target CRS)."""

    lat: Optional[float] = Field(None, description="WGS84 latitude in decimal degrees")
    lon: Optional[float] = Field(None, description="WGS84 longitude in decimal degrees")
    e: Optional[int] = Field(None, description="OSGB36 eastings in metres")
    n: Optional[int] = Field(None, description="OSGB36 northings in metres")
    height: Optional[float] = Field(
        None,
        description="Height in metres (ellipsoidal for WGS84, orthometric for OSGB)",
    )
    gridref: Optional[str] = Field(
        None, description="OS National Grid reference (only for OSGB output)"
    )


class CoordinateConversionResponse(BaseModel):
    """Response from coordinate conversion endpoint."""

    from_crs: str = Field(..., description="Source coordinate reference system")
    to_crs: str = Field(..., description="Target coordinate reference system")
    input: CoordinateInput = Field(..., description="Input coordinates")
    output: CoordinateOutput = Field(..., description="Converted coordinates")


@router.get(
    "/convert",
    response_model=CoordinateConversionResponse,
    openapi_extra=openapi_lifecycle(
        "ga",
        note="Convert coordinates between WGS84 and OSGB36 using OSTN15/OSGM15.",
    ),
)
def convert_coordinates(
    from_crs: Literal["wgs84", "osgb"] = Query(
        ..., alias="from", description="Source coordinate reference system"
    ),
    to_crs: Literal["wgs84", "osgb"] = Query(
        ..., alias="to", description="Target coordinate reference system"
    ),
    lat: Optional[float] = Query(
        None, ge=-90, le=90, description="WGS84 latitude (required if from=wgs84)"
    ),
    lon: Optional[float] = Query(
        None, ge=-180, le=180, description="WGS84 longitude (required if from=wgs84)"
    ),
    e: Optional[int] = Query(
        None, ge=0, le=700000, description="OSGB36 eastings (required if from=osgb)"
    ),
    n: Optional[int] = Query(
        None, ge=0, le=1300000, description="OSGB36 northings (required if from=osgb)"
    ),
    height: Optional[float] = Query(
        None,
        description="Height in metres. If from=wgs84, this is ellipsoidal height. "
        "If from=osgb, this is orthometric height (ODN). "
        "When provided, enables 3D transformation including height conversion.",
    ),
) -> CoordinateConversionResponse:
    """
    Convert coordinates between WGS84 and OSGB36.

    Uses the Ordnance Survey OSTN15 transformation for horizontal coordinates
    (sub-centimetre accuracy) and OSGM15 geoid model for height conversion
    when height is provided.

    ## Examples

    **WGS84 to OSGB36 (2D):**
    ```
    GET /v1/coordinates/convert?from=wgs84&to=osgb&lat=51.5074&lon=-0.1276
    ```

    **WGS84 to OSGB36 (3D with height):**
    ```
    GET /v1/coordinates/convert?from=wgs84&to=osgb&lat=51.5074&lon=-0.1276&height=50
    ```

    **OSGB36 to WGS84:**
    ```
    GET /v1/coordinates/convert?from=osgb&to=wgs84&e=530034&n=179382
    ```
    """
    # Validate same CRS conversion is not requested
    if from_crs == to_crs:
        raise HTTPException(
            status_code=400,
            detail="Source and target CRS must be different",
        )

    # Validate required parameters based on source CRS
    if from_crs == "wgs84":
        if lat is None or lon is None:
            raise HTTPException(
                status_code=400,
                detail="lat and lon are required when from=wgs84",
            )

        # Perform conversion
        try:
            out_e, out_n, out_h = convert_wgs84_to_osgb(lon, lat, height)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Conversion failed: {exc}",
            ) from exc

        # Generate grid reference
        try:
            gridref = eastings_northings_to_gridref(out_e, out_n)
        except ValueError:
            gridref = None  # Outside GB grid

        return CoordinateConversionResponse(
            from_crs="wgs84",
            to_crs="osgb",
            input=CoordinateInput(
                lat=lat, lon=lon, height=height, e=None, n=None, gridref=None
            ),
            output=CoordinateOutput(
                e=round(out_e),
                n=round(out_n),
                height=round(out_h, 1) if out_h is not None else None,
                gridref=gridref,
                lat=None,
                lon=None,
            ),
        )

    else:  # from_crs == "osgb"
        if e is None or n is None:
            raise HTTPException(
                status_code=400,
                detail="e and n are required when from=osgb",
            )

        # Perform conversion
        try:
            out_lon, out_lat, out_h = convert_osgb_to_wgs84(float(e), float(n), height)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Conversion failed: {exc}",
            ) from exc

        # Generate grid reference for input (convenience)
        try:
            gridref = eastings_northings_to_gridref(e, n)
        except ValueError:
            gridref = None

        return CoordinateConversionResponse(
            from_crs="osgb",
            to_crs="wgs84",
            input=CoordinateInput(
                e=e, n=n, height=height, gridref=gridref, lat=None, lon=None
            ),
            output=CoordinateOutput(
                lat=round(out_lat, 6),
                lon=round(out_lon, 6),
                height=round(out_h, 1) if out_h is not None else None,
                e=None,
                n=None,
                gridref=None,
            ),
        )
