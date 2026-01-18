"""
Coordinate conversion API endpoint.

Provides accurate coordinate conversions:
- WGS84 <-> OSGB36 using OSTN15/OSGM15 models
- WGS84 <-> Irish Grid (TM65/EPSG:29903)
- Auto-detection of appropriate grid system based on country polygons

See: docs/decisions/0001-ostn15-coordinate-conversion.md
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import openapi_lifecycle
from api.services.coordinate_service import (
    convert_irish_to_wgs84,
    convert_osgb_to_wgs84,
    convert_wgs84_to_irish,
    convert_wgs84_to_osgb,
    eastings_northings_to_gridref,
    eastings_northings_to_irish_gridref,
)
from api.services.grid_system import get_country_info_for_point

router = APIRouter()


class CoordinateInput(BaseModel):
    """Input coordinates (varies based on source CRS)."""

    lat: Optional[float] = Field(None, description="WGS84 latitude in decimal degrees")
    lon: Optional[float] = Field(None, description="WGS84 longitude in decimal degrees")
    e: Optional[int] = Field(
        None, description="Eastings in metres (OSGB36 or Irish Grid)"
    )
    n: Optional[int] = Field(
        None, description="Northings in metres (OSGB36 or Irish Grid)"
    )
    height: Optional[float] = Field(
        None,
        description="Height in metres (ellipsoidal for WGS84, orthometric for OSGB)",
    )
    gridref: Optional[str] = Field(
        None, description="Grid reference (OSGB or Irish format)"
    )


class CoordinateOutput(BaseModel):
    """Output coordinates (varies based on target CRS)."""

    lat: Optional[float] = Field(None, description="WGS84 latitude in decimal degrees")
    lon: Optional[float] = Field(None, description="WGS84 longitude in decimal degrees")
    e: Optional[int] = Field(
        None, description="Eastings in metres (OSGB36 or Irish Grid)"
    )
    n: Optional[int] = Field(
        None, description="Northings in metres (OSGB36 or Irish Grid)"
    )
    height: Optional[float] = Field(
        None,
        description="Height in metres (ellipsoidal for WGS84, orthometric for OSGB)",
    )
    gridref: Optional[str] = Field(
        None, description="Grid reference (OSGB or Irish format)"
    )


class CoordinateConversionResponse(BaseModel):
    """Response from coordinate conversion endpoint."""

    from_crs: str = Field(..., description="Source coordinate reference system")
    to_crs: str = Field(..., description="Target coordinate reference system")
    input: CoordinateInput = Field(..., description="Input coordinates")
    output: CoordinateOutput = Field(..., description="Converted coordinates")
    grid_system: Optional[str] = Field(
        None, description="Grid system used: 'gb' (OSGB36) or 'ie' (Irish Grid)"
    )
    country_name: Optional[str] = Field(
        None, description="Country name if auto-detected (e.g., 'Ireland', 'England')"
    )


@router.get(
    "/convert",
    response_model=CoordinateConversionResponse,
    openapi_extra=openapi_lifecycle(
        "ga",
        note="Convert coordinates between WGS84 and OSGB36/Irish Grid.",
    ),
)
def convert_coordinates(
    from_crs: Literal["wgs84", "osgb", "irish"] = Query(
        ...,
        alias="from",
        description="Source CRS: wgs84, osgb (British National Grid), or irish (Irish Grid)",
    ),
    to_crs: Literal["wgs84", "osgb", "irish", "grid"] = Query(
        ...,
        alias="to",
        description="Target CRS: wgs84, osgb, irish, or grid (auto-detect based on location)",
    ),
    lat: Optional[float] = Query(
        None, ge=-90, le=90, description="WGS84 latitude (required if from=wgs84)"
    ),
    lon: Optional[float] = Query(
        None, ge=-180, le=180, description="WGS84 longitude (required if from=wgs84)"
    ),
    e: Optional[int] = Query(
        None,
        ge=0,
        le=700000,
        description="Eastings in metres (required if from=osgb or from=irish)",
    ),
    n: Optional[int] = Query(
        None,
        ge=0,
        le=1300000,
        description="Northings in metres (required if from=osgb or from=irish)",
    ),
    height: Optional[float] = Query(
        None,
        description="Height in metres. If from=wgs84, this is ellipsoidal height. "
        "If from=osgb, this is orthometric height (ODN). "
        "When provided with OSGB, enables 3D transformation including height conversion. "
        "Note: Irish Grid does not support height conversion.",
    ),
    db: Session = Depends(get_db),
) -> CoordinateConversionResponse:
    """
    Convert coordinates between WGS84, OSGB36, and Irish Grid.

    Supports:
    - **OSGB36** (British National Grid, EPSG:27700): Uses OSTN15/OSGM15 for high accuracy
    - **Irish Grid** (TM65, EPSG:29903): For the island of Ireland (ROI + Northern Ireland)
    - **Auto-detection** (`to=grid`): Automatically selects OSGB or Irish Grid based on country

    ## Examples

    **WGS84 to OSGB36:**
    ```
    GET /v1/coordinates/convert?from=wgs84&to=osgb&lat=51.5074&lon=-0.1276
    ```

    **WGS84 to Irish Grid:**
    ```
    GET /v1/coordinates/convert?from=wgs84&to=irish&lat=53.3498&lon=-6.2603
    ```

    **WGS84 to auto-detected grid:**
    ```
    GET /v1/coordinates/convert?from=wgs84&to=grid&lat=53.3498&lon=-6.2603
    ```

    **Irish Grid to WGS84:**
    ```
    GET /v1/coordinates/convert?from=irish&to=wgs84&e=315904&n=234671
    ```
    """
    # Validate same CRS conversion is not requested (except grid which is auto)
    if from_crs == to_crs:
        raise HTTPException(
            status_code=400,
            detail="Source and target CRS must be different",
        )

    # Handle auto-detection (to=grid) - only valid from wgs84
    if to_crs == "grid":
        if from_crs != "wgs84":
            raise HTTPException(
                status_code=400,
                detail="to=grid (auto-detect) is only valid when from=wgs84",
            )
        if lat is None or lon is None:
            raise HTTPException(
                status_code=400,
                detail="lat and lon are required when from=wgs84",
            )

        # Classify the point to determine grid system
        grid_system, country_code, country_name = get_country_info_for_point(
            db, lat, lon
        )

        if grid_system is None:
            raise HTTPException(
                status_code=400,
                detail="Location is not within a known country (GB or Ireland)",
            )

        # Route to appropriate grid system
        if grid_system == "gb":
            to_crs = "osgb"
        else:  # grid_system == "ie"
            to_crs = "irish"

        # Continue to conversion logic below with resolved to_crs
        # (grid_system and country_name will be included in response)
    else:
        grid_system = None
        country_name = None

    # -------------------------------------------------------------------------
    # WGS84 -> OSGB or Irish
    # -------------------------------------------------------------------------
    if from_crs == "wgs84":
        if lat is None or lon is None:
            raise HTTPException(
                status_code=400,
                detail="lat and lon are required when from=wgs84",
            )

        if to_crs == "osgb":
            # WGS84 -> OSGB36
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
                grid_system=grid_system or "gb",
                country_name=country_name,
            )

        elif to_crs == "irish":
            # WGS84 -> Irish Grid (no height conversion)
            try:
                out_e, out_n = convert_wgs84_to_irish(lon, lat)
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Conversion failed: {exc}",
                ) from exc

            # Generate Irish grid reference
            try:
                gridref = eastings_northings_to_irish_gridref(out_e, out_n)
            except ValueError:
                gridref = None  # Outside Irish grid

            return CoordinateConversionResponse(
                from_crs="wgs84",
                to_crs="irish",
                input=CoordinateInput(
                    lat=lat, lon=lon, height=height, e=None, n=None, gridref=None
                ),
                output=CoordinateOutput(
                    e=round(out_e),
                    n=round(out_n),
                    height=None,  # Irish Grid doesn't do height conversion
                    gridref=gridref,
                    lat=None,
                    lon=None,
                ),
                grid_system=grid_system or "ie",
                country_name=country_name,
            )

    # -------------------------------------------------------------------------
    # OSGB -> WGS84
    # -------------------------------------------------------------------------
    elif from_crs == "osgb":
        if e is None or n is None:
            raise HTTPException(
                status_code=400,
                detail="e and n are required when from=osgb",
            )

        if to_crs != "wgs84":
            raise HTTPException(
                status_code=400,
                detail="from=osgb can only convert to=wgs84",
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
            grid_system="gb",
            country_name=None,
        )

    # -------------------------------------------------------------------------
    # Irish -> WGS84
    # -------------------------------------------------------------------------
    elif from_crs == "irish":
        if e is None or n is None:
            raise HTTPException(
                status_code=400,
                detail="e and n are required when from=irish",
            )

        if to_crs != "wgs84":
            raise HTTPException(
                status_code=400,
                detail="from=irish can only convert to=wgs84",
            )

        # Perform conversion
        try:
            out_lon, out_lat = convert_irish_to_wgs84(float(e), float(n))
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Conversion failed: {exc}",
            ) from exc

        # Generate Irish grid reference for input (convenience)
        try:
            gridref = eastings_northings_to_irish_gridref(e, n)
        except ValueError:
            gridref = None

        return CoordinateConversionResponse(
            from_crs="irish",
            to_crs="wgs84",
            input=CoordinateInput(
                e=e, n=n, height=height, gridref=gridref, lat=None, lon=None
            ),
            output=CoordinateOutput(
                lat=round(out_lat, 6),
                lon=round(out_lon, 6),
                height=None,  # Irish Grid doesn't do height conversion
                e=None,
                n=None,
                gridref=None,
            ),
            grid_system="ie",
            country_name=None,
        )

    # Should never reach here
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported conversion: from={from_crs} to={to_crs}",
    )
