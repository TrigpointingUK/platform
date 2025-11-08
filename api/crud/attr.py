"""
CRUD operations for attribute tables.
"""

from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from api.models.attr import Attr, AttrSet, AttrSetAttrVal, AttrSource, AttrVal


def get_attrs_for_trig(db: Session, trig_id: int) -> Optional[list[dict]]:
    """
    Get all attribute data for a trigpoint, grouped by source.

    Args:
        db: Database session
        trig_id: Trigpoint ID

    Returns:
        List of dicts with structure:
        [{
            "source": {"id": int, "name": str, "url": str},
            "attr_names": {attr_id: attr_name, ...},
            "attribute_sets": [{"values": {attr_id: value_string, ...}}, ...]
        }]
        or None if no attributes found
    """
    # Query to get all attrvals for this trig
    # Join: attrset -> attrset_attrval -> attrval -> attr
    # Also get attrsource info
    query = (
        db.query(
            AttrSet.id.label("attrset_id"),
            AttrSet.sort_order.label("attrset_sort_order"),
            AttrSource.id.label("attrsource_id"),
            AttrSource.name.label("attrsource_name"),
            AttrSource.url.label("attrsource_url"),
            AttrSource.sort_order.label("attrsource_sort_order"),
            Attr.id.label("attr_id"),
            Attr.name.label("attr_name"),
            Attr.sort_order.label("attr_sort_order"),
            AttrVal.value_string,
        )
        .join(AttrSource, AttrSet.attrsource_id == AttrSource.id)
        .join(AttrSetAttrVal, AttrSet.id == AttrSetAttrVal.attrset_id)
        .join(AttrVal, AttrSetAttrVal.attrval_id == AttrVal.id)
        .join(Attr, AttrVal.attr_id == Attr.id)
        .filter(AttrSet.trig_id == trig_id)
        .order_by(
            AttrSource.sort_order,
            AttrSet.sort_order,
            AttrSet.id,
            Attr.sort_order,
        )
    )

    results = query.all()

    if not results:
        return None

    # Group data by attrsource_id
    sources_dict = {}
    sources_order = []

    for row in results:
        source_id = row.attrsource_id

        # Create source entry if it doesn't exist
        if source_id not in sources_dict:
            sources_dict[source_id] = {
                "source": {
                    "id": source_id,
                    "name": row.attrsource_name,
                    "url": row.attrsource_url,
                },
                "attr_names": {},
                "attribute_sets_dict": defaultdict(
                    dict
                ),  # attrset_id -> {attr_id: value}
            }
            sources_order.append(source_id)

        source_data = sources_dict[source_id]

        # Add attr_name to attr_names dict
        if row.attr_id not in source_data["attr_names"]:
            source_data["attr_names"][row.attr_id] = row.attr_name

        # Add value to the appropriate attribute set
        source_data["attribute_sets_dict"][row.attrset_id][row.attr_id] = (
            row.value_string or ""
        )

    # Convert to final structure
    result = []
    for source_id in sources_order:
        source_data = sources_dict[source_id]
        attribute_sets = [
            {"values": values} for values in source_data["attribute_sets_dict"].values()
        ]

        result.append(
            {
                "source": source_data["source"],
                "attr_names": source_data["attr_names"],
                "attribute_sets": attribute_sets,
            }
        )

    return result
