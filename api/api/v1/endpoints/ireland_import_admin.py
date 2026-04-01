"""
Admin endpoints for Ireland trigpoint import comparison.

Provides functionality to compare Ireland25 CSV data with Irish trigpoints
in the database, apply CSV data to existing trigs, and create new trigs
from CSV rows.
"""

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.api.deps import get_db, require_admin
from api.api.lifecycle import openapi_lifecycle
from api.core.logging import get_logger
from api.crud import location as location_crud
from api.crud import trig as trig_crud
from api.models.user import User
from api.schemas.ireland_import import (
    ComparisonItem,
    CSVRowData,
    DBTrigData,
    FieldDifference,
    IrelandImportApplyRequest,
    IrelandImportBulkCreateRequest,
    IrelandImportBulkCreateResponse,
    IrelandImportComparisonResponse,
    IrelandImportCreateRequest,
)
from api.schemas.trig_admin import TrigAdminDetail
from api.services.cache_invalidator import invalidate_patterns, invalidate_trig_caches
from api.services.ireland_import_service import (
    AREA_NAMES,
    build_trig_data_from_csv,
    compare_ireland_csv_with_db,
    get_csv_row_by_index,
)

logger = get_logger(__name__)
router = APIRouter()
ADMIN_SCOPE_DEPENDENCY = require_admin()


def _csv_row_to_schema(row) -> CSVRowData:
    """Convert service CSVRow dataclass to Pydantic CSVRowData schema."""
    return CSVRowData(
        csv_row_index=row.row_index,
        station_name=row.station_name,
        osi_ni_no=row.osi_ni_no,
        eastings=row.eastings,
        northings=row.northings,
        height=row.height,
        fb_sort=row.fb_sort,
        fb_number=row.fb_number,
        date_built=row.date_built,
        order=row.order,
        dr=row.dr,
        grid_ref=row.grid_ref,
        notes=row.notes,
    )


def _db_trig_to_schema(trig) -> DBTrigData:
    """Convert service DBIrishTrig dataclass to Pydantic DBTrigData schema."""
    return DBTrigData(
        trig_id=trig.trig_id,
        waypoint=trig.waypoint,
        name=trig.name,
        fb_number=trig.fb_number,
        stn_number=trig.stn_number,
        osgb_eastings=trig.osgb_eastings,
        osgb_northings=trig.osgb_northings,
        osgb_gridref=trig.osgb_gridref,
        osgb_height=trig.osgb_height,
        condition=trig.condition,
        historic_use=trig.historic_use,
        current_use=trig.current_use,
        status_id=trig.status_id,
        type_id=trig.type_id,
        has_non_irish_gridref=trig.has_non_irish_gridref,
        area_name=AREA_NAMES.get(trig.area_id, ""),
    )


@router.get(
    "/comparison",
    response_model=IrelandImportComparisonResponse,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Compare Ireland25 CSV with Irish trigpoints in the database.",
    ),
)
def get_ireland_import_comparison(
    admin_user: User = Depends(ADMIN_SCOPE_DEPENDENCY),
    db: Session = Depends(get_db),
) -> IrelandImportComparisonResponse:
    """
    Compare Ireland25 CSV data with Irish trigpoints in the database.

    Irish trigs are identified via the trig_area table where area_type_id=3
    and area_id IN (339, 342). Matching uses Euclidean distance on Irish Grid
    coordinates with a 500m threshold.

    Categories:
    - **matched_identical**: CSV and DB agree on all fields
    - **matched_different**: Matched by proximity but with field differences
    - **ambiguous**: Multiple DB records within 500m of a CSV row
    - **new_in_csv**: CSV row with no DB match
    - **orphan_in_db**: DB trig with no CSV match

    Requires `api:admin` scope.
    """
    logger.info(
        "Ireland import comparison requested",
        extra={"admin_user_id": int(admin_user.id)},
    )

    try:
        result = compare_ireland_csv_with_db(db)
    except Exception as e:
        logger.error("Ireland import comparison error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during comparison: {e}",
        ) from e

    # Convert dataclasses to response models
    items = []
    for item in result.items:
        csv_data = _csv_row_to_schema(item.csv_row) if item.csv_row else None
        db_data = _db_trig_to_schema(item.db_trig) if item.db_trig else None
        additional = [_db_trig_to_schema(m) for m in item.additional_db_matches]
        differences = [
            FieldDifference(
                field_name=d.field_name,
                csv_value=d.csv_value,
                db_value=d.db_value,
            )
            for d in item.differences
        ]

        items.append(
            ComparisonItem(
                category=item.category,
                csv_data=csv_data,
                db_data=db_data,
                additional_db_matches=additional,
                differences=differences,
                distance_metres=item.distance_metres,
                description=item.description,
            )
        )

    logger.info(
        "Ireland import comparison complete",
        extra={
            "csv_count": result.csv_count,
            "db_irish_count": result.db_irish_count,
            "matched_identical": result.matched_identical_count,
            "matched_different": result.matched_different_count,
            "ambiguous": result.ambiguous_count,
            "new_in_csv": result.new_in_csv_count,
            "orphan_in_db": result.orphan_in_db_count,
            "non_irish_gridref": result.non_irish_gridref_count,
        },
    )

    return IrelandImportComparisonResponse(
        csv_count=result.csv_count,
        db_irish_count=result.db_irish_count,
        matched_identical_count=result.matched_identical_count,
        matched_different_count=result.matched_different_count,
        ambiguous_count=result.ambiguous_count,
        new_in_csv_count=result.new_in_csv_count,
        orphan_in_db_count=result.orphan_in_db_count,
        non_irish_gridref_count=result.non_irish_gridref_count,
        items=items,
    )


@router.post(
    "/apply/{trig_id}",
    response_model=TrigAdminDetail,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Apply Ireland25 CSV data to an existing database trigpoint.",
    ),
)
def apply_csv_to_trig(
    trig_id: int,
    apply_request: IrelandImportApplyRequest,
    request: Request,
    admin_user: User = Depends(ADMIN_SCOPE_DEPENDENCY),
    db: Session = Depends(get_db),
) -> TrigAdminDetail:
    """
    Apply Ireland25 CSV data to an existing trigpoint.

    Updates the trig's fields from the CSV row, sets original_* provenance
    fields, recomputes WGS84 coordinates from Irish Grid, and updates the
    PostGIS location.

    Requires `api:admin` scope.
    """
    from api.utils.ip_address import get_client_ip_normalized

    # Validate trig exists
    trig = trig_crud.get_trig_by_id(db, trig_id)
    if not trig:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    # Get CSV row
    csv_row = get_csv_row_by_index(apply_request.csv_row_index)
    if not csv_row:
        raise HTTPException(
            status_code=404,
            detail=f"CSV row index {apply_request.csv_row_index} not found",
        )

    raw_ip = request.client.host if request.client else "unknown"
    client_ip = get_client_ip_normalized(raw_ip)

    # Build trig data from CSV
    trig_data = build_trig_data_from_csv(csv_row)

    # Auto-set postcode based on WGS coordinates
    postcode_result = location_crud.find_nearest_postcode(
        db,
        float(trig_data["wgs_lat"]),
        float(trig_data["wgs_long"]),
        max_distance_m=5000.0,
    )
    nearest_postcode = postcode_result[0] if postcode_result else None

    # Format timestamp for attention_comment
    timestamp_str = datetime.now(UTC).strftime("%d %b %Y %H:%M:%S")
    new_comment = (
        f"{timestamp_str} - {admin_user.name} - {admin_user.email} - "
        f"IRELAND25 APPLY: {apply_request.admin_comment}"
    )
    updated_attention_comment = (
        f"{new_comment}\n\n{trig.attention_comment}"
        if trig.attention_comment
        else new_comment
    )

    # Build update dict - metadata fields from CSV, but preserve existing
    # DB coordinates/gridref as they are generally more accurate than the
    # CSV values (many of which derive from 6-figure grid references).
    updates: dict = {
        "name": trig_data["name"],
        "fb_number": trig_data["fb_number"],
        "stn_number": trig_data["stn_number"],
        "historic_use": trig_data["historic_use"],
        "condition": trig_data["condition"],
        "postcode": nearest_postcode,
        "attention_comment": updated_attention_comment,
        # Original location provenance (records CSV source data without
        # overwriting the trig's current, more precise coordinates)
        "original_osgb_eastings": trig_data["original_osgb_eastings"],
        "original_osgb_northings": trig_data["original_osgb_northings"],
        "original_osgb_gridref": trig_data["original_osgb_gridref"],
        "original_osgb_height": trig_data["original_osgb_height"],
        "original_wgs_lat": trig_data["original_wgs_lat"],
        "original_wgs_long": trig_data["original_wgs_long"],
        "original_wgs_height": trig_data["original_wgs_height"],
        "original_grid_system": trig_data["original_grid_system"],
        "original_provenance": trig_data["original_provenance"],
    }

    # Apply update with admin tracking
    updated_trig = trig_crud.update_trig_admin(
        db, trig_id, int(admin_user.id), client_ip, updates
    )

    if not updated_trig:
        raise HTTPException(status_code=500, detail="Failed to update trigpoint")

    # Invalidate caches
    invalidate_trig_caches(trig_id)

    logger.info(
        json.dumps(
            {
                "event": "ireland_import_apply",
                "trig_id": trig_id,
                "csv_row_index": apply_request.csv_row_index,
                "admin_user_id": int(admin_user.id),
                "csv_station_name": csv_row.station_name,
            }
        )
    )

    return TrigAdminDetail.model_validate(updated_trig)


@router.post(
    "/create",
    response_model=TrigAdminDetail,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Create a new trigpoint from Ireland25 CSV data.",
    ),
)
def create_trig_from_csv(
    create_request: IrelandImportCreateRequest,
    request: Request,
    admin_user: User = Depends(ADMIN_SCOPE_DEPENDENCY),
    db: Session = Depends(get_db),
) -> TrigAdminDetail:
    """
    Create a new trigpoint from an Ireland25 CSV row.

    Auto-generates waypoint, computes WGS84 from Irish Grid coordinates,
    and sets original_* provenance fields.

    Requires `api:admin` scope.
    """
    from api.utils.ip_address import get_client_ip_normalized

    # Get CSV row
    csv_row = get_csv_row_by_index(create_request.csv_row_index)
    if not csv_row:
        raise HTTPException(
            status_code=404,
            detail=f"CSV row index {create_request.csv_row_index} not found",
        )

    raw_ip = request.client.host if request.client else "unknown"
    client_ip = get_client_ip_normalized(raw_ip)

    # Build trig data from CSV
    trig_data = build_trig_data_from_csv(csv_row)

    # Auto-generate waypoint
    waypoint = trig_crud.get_next_waypoint(db)

    # Auto-set postcode based on WGS coordinates
    postcode_result = location_crud.find_nearest_postcode(
        db,
        float(trig_data["wgs_lat"]),
        float(trig_data["wgs_long"]),
        max_distance_m=5000.0,
    )
    trig_data["postcode"] = postcode_result[0] if postcode_result else None

    # Format attention_comment
    timestamp_str = datetime.now(UTC).strftime("%d %b %Y %H:%M:%S")
    trig_data["attention_comment"] = (
        f"{timestamp_str} - {admin_user.name} - {admin_user.email} - "
        f"IRELAND25 CREATE: {create_request.admin_comment}"
    )

    # Set PostGIS location from WGS84 coordinates (PostgreSQL only)
    if db.bind and db.bind.dialect.name != "sqlite":  # type: ignore[union-attr]
        from geoalchemy2.functions import ST_MakePoint, ST_SetSRID

        trig_data["location"] = ST_SetSRID(
            ST_MakePoint(float(trig_data["wgs_long"]), float(trig_data["wgs_lat"])),
            4326,
        )

    # Create the trigpoint
    new_trig = trig_crud.create_trig_admin(
        db, waypoint, int(admin_user.id), client_ip, trig_data
    )

    # Invalidate export caches
    invalidate_patterns(["trigs:*:export*"])

    logger.info(
        json.dumps(
            {
                "event": "ireland_import_create",
                "trig_id": int(new_trig.id),
                "waypoint": waypoint,
                "csv_row_index": create_request.csv_row_index,
                "admin_user_id": int(admin_user.id),
                "csv_station_name": csv_row.station_name,
            }
        )
    )

    return TrigAdminDetail.model_validate(new_trig)


@router.post(
    "/bulk-create",
    response_model=IrelandImportBulkCreateResponse,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Bulk-create new trigpoints from all unmatched Ireland25 CSV rows.",
    ),
)
def bulk_create_trigs_from_csv(
    bulk_request: IrelandImportBulkCreateRequest,
    request: Request,
    admin_user: User = Depends(ADMIN_SCOPE_DEPENDENCY),
    db: Session = Depends(get_db),
) -> IrelandImportBulkCreateResponse:
    """
    Bulk-create new trigpoints from unmatched Ireland25 CSV rows.

    Runs the comparison, identifies all 'new_in_csv' items, and creates
    a trig for each one. Returns a summary of created and failed rows.

    Requires `api:admin` scope.
    """
    from api.utils.ip_address import get_client_ip_normalized

    raw_ip = request.client.host if request.client else "unknown"
    client_ip = get_client_ip_normalized(raw_ip)

    result = compare_ireland_csv_with_db(db)
    new_items = [i for i in result.items if i.category == "new_in_csv" and i.csv_row]

    created: list[dict] = []
    failed: list[dict] = []

    for item in new_items:
        csv_row = item.csv_row
        assert csv_row is not None

        try:
            trig_data = build_trig_data_from_csv(csv_row)
            waypoint = trig_crud.get_next_waypoint(db)

            postcode_result = location_crud.find_nearest_postcode(
                db,
                float(trig_data["wgs_lat"]),
                float(trig_data["wgs_long"]),
                max_distance_m=5000.0,
            )
            trig_data["postcode"] = postcode_result[0] if postcode_result else None

            timestamp_str = datetime.now(UTC).strftime("%d %b %Y %H:%M:%S")
            trig_data["attention_comment"] = (
                f"{timestamp_str} - {admin_user.name} - {admin_user.email} - "
                f"IRELAND25 BULK CREATE: {bulk_request.admin_comment}"
            )

            if db.bind and db.bind.dialect.name != "sqlite":  # type: ignore[union-attr]
                from geoalchemy2.functions import ST_MakePoint, ST_SetSRID

                trig_data["location"] = ST_SetSRID(
                    ST_MakePoint(
                        float(trig_data["wgs_long"]), float(trig_data["wgs_lat"])
                    ),
                    4326,
                )

            new_trig = trig_crud.create_trig_admin(
                db, waypoint, int(admin_user.id), client_ip, trig_data
            )

            created.append(
                {
                    "csv_row_index": csv_row.row_index,
                    "station_name": csv_row.station_name,
                    "trig_id": int(new_trig.id),
                    "waypoint": new_trig.waypoint,
                }
            )
        except Exception as e:
            logger.error(
                "Bulk create failed for CSV row %d (%s): %s",
                csv_row.row_index,
                csv_row.station_name,
                str(e),
                exc_info=True,
            )
            db.rollback()
            failed.append(
                {
                    "csv_row_index": csv_row.row_index,
                    "station_name": csv_row.station_name,
                    "error": str(e),
                }
            )

    if created:
        invalidate_patterns(["trigs:*:export*"])

    logger.info(
        json.dumps(
            {
                "event": "ireland_import_bulk_create",
                "admin_user_id": int(admin_user.id),
                "created_count": len(created),
                "failed_count": len(failed),
            }
        )
    )

    return IrelandImportBulkCreateResponse(
        created_count=len(created),
        failed_count=len(failed),
        total_new_in_csv=len(new_items),
        created=created,
        failed=failed,
    )
