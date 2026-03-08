"""
Pydantic schemas for Ireland trigpoint import comparison API.
"""

from typing import Optional

from pydantic import BaseModel, Field


class CSVRowData(BaseModel):
    """Data from one row of the Ireland25 CSV file."""

    csv_row_index: int = Field(..., description="0-based index of the row in the CSV")
    station_name: str = Field(..., description="Station Name (column A)")
    osi_ni_no: str = Field("", description="OSI/NI No (column B)")
    eastings: float = Field(..., description="Irish Grid eastings in metres (column C)")
    northings: float = Field(
        ..., description="Irish Grid northings in metres (column D)"
    )
    height: Optional[float] = Field(
        None, description="Height in metres, null if unknown (column E)"
    )
    fb_sort: str = Field("", description="FB Sort value (column F)")
    fb_number: str = Field("", description="Flush bracket number (column G)")
    date_built: str = Field("", description="Date built (column H)")
    order: str = Field("", description="Ord - triangulation order (column I)")
    dr: str = Field("", description="DR value (column J)")
    grid_ref: str = Field("", description="Irish Grid reference (column K)")
    notes: str = Field("", description="Notes including condition codes (column L)")


class DBTrigData(BaseModel):
    """Data from a matched database trig record."""

    trig_id: int = Field(..., description="Trigpoint database ID")
    waypoint: str = Field(..., description="Waypoint code (e.g. TP1234)")
    name: str = Field(..., description="Trigpoint name")
    fb_number: str = Field("", description="Flush bracket number")
    stn_number: str = Field("", description="Station number")
    osgb_eastings: float = Field(..., description="Stored eastings")
    osgb_northings: float = Field(..., description="Stored northings")
    osgb_gridref: str = Field("", description="Stored grid reference")
    osgb_height: Optional[float] = Field(None, description="Stored height")
    condition: str = Field("", description="Condition code")
    historic_use: str = Field("", description="Historic use")
    current_use: str = Field("", description="Current use")
    status_id: int = Field(..., description="Status ID")
    type_id: Optional[int] = Field(None, description="Type ID")
    has_non_irish_gridref: bool = Field(
        False,
        description="True if osgb_gridref is not in Irish Grid format (data quality warning)",
    )
    area_name: str = Field(
        "",
        description="Area name: 'Republic of Ireland' or 'Northern Ireland'",
    )


class FieldDifference(BaseModel):
    """A single field-level difference between CSV and DB."""

    field_name: str = Field(..., description="Name of the differing field")
    csv_value: Optional[str] = Field(None, description="Value from CSV")
    db_value: Optional[str] = Field(None, description="Value from database")


class ComparisonItem(BaseModel):
    """A single comparison result between a CSV row and zero or more DB records."""

    category: str = Field(
        ...,
        description=(
            "Category: matched_identical, matched_different, ambiguous, "
            "new_in_csv, orphan_in_db"
        ),
    )
    csv_data: Optional[CSVRowData] = Field(
        None, description="CSV row data (absent for orphan_in_db)"
    )
    db_data: Optional[DBTrigData] = Field(
        None,
        description="Primary matched DB record (absent for new_in_csv)",
    )
    additional_db_matches: list[DBTrigData] = Field(
        default_factory=list,
        description="Extra DB records within 500m (for ambiguous matches)",
    )
    differences: list[FieldDifference] = Field(
        default_factory=list,
        description="Field-level differences (for matched_different and ambiguous)",
    )
    distance_metres: Optional[float] = Field(
        None, description="Distance between CSV and primary DB match in metres"
    )
    description: str = Field("", description="Human-readable summary of this item")


class IrelandImportComparisonResponse(BaseModel):
    """Response from the Ireland import comparison endpoint."""

    csv_count: int = Field(..., description="Total rows in CSV file")
    db_irish_count: int = Field(..., description="Total Irish trigs in database")
    matched_identical_count: int = Field(
        ..., description="CSV rows matched with no differences"
    )
    matched_different_count: int = Field(
        ..., description="CSV rows matched with field differences"
    )
    ambiguous_count: int = Field(
        ..., description="CSV rows with multiple DB matches within 500m"
    )
    new_in_csv_count: int = Field(..., description="CSV rows with no DB match")
    orphan_in_db_count: int = Field(..., description="DB trigs with no CSV match")
    non_irish_gridref_count: int = Field(
        ...,
        description="DB Irish trigs whose osgb_gridref is not in Irish Grid format",
    )
    items: list[ComparisonItem] = Field(..., description="All comparison items")


class IrelandImportApplyRequest(BaseModel):
    """Request to apply CSV data to an existing DB trig."""

    csv_row_index: int = Field(
        ..., description="0-based CSV row index identifying the source row"
    )
    admin_comment: str = Field(
        default="Ireland25 import: applied CSV data",
        min_length=1,
        description="Admin comment for the audit trail",
    )


class IrelandImportCreateRequest(BaseModel):
    """Request to create a new trig from a CSV row."""

    csv_row_index: int = Field(
        ..., description="0-based CSV row index identifying the source row"
    )
    admin_comment: str = Field(
        default="Ireland25 import: created from CSV",
        min_length=1,
        description="Admin comment for the audit trail",
    )


class IrelandImportBulkCreateRequest(BaseModel):
    """Request to bulk-create all unmatched CSV rows as new trigs."""

    admin_comment: str = Field(
        default="Ireland25 import: bulk created from CSV",
        min_length=1,
        description="Admin comment for the audit trail",
    )


class BulkCreateResultItem(BaseModel):
    """Result of creating (or failing to create) a single trig."""

    csv_row_index: int
    station_name: str
    trig_id: int | None = None
    waypoint: str | None = None
    error: str | None = None


class IrelandImportBulkCreateResponse(BaseModel):
    """Response from the bulk-create endpoint."""

    created_count: int = Field(..., description="Number of trigs successfully created")
    failed_count: int = Field(..., description="Number of rows that failed")
    total_new_in_csv: int = Field(
        ..., description="Total new_in_csv rows identified by comparison"
    )
    created: list[dict] = Field(
        default_factory=list, description="Details of created trigs"
    )
    failed: list[dict] = Field(
        default_factory=list, description="Details of failed rows"
    )
