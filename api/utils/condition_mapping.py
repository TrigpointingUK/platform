"""
Utility functions for mapping condition codes to human-readable descriptions.

Supports both database lookups and hardcoded fallback values.
"""

from typing import Dict, Optional

from sqlalchemy.orm import Session

# Hardcoded fallback mapping for when database is not available
FALLBACK_CONDITION_MAP = {
    "Z": "Not Logged",
    "N": "Couldn't find it",
    "G": "Good",
    "S": "Slightly damaged",
    "C": "Converted",
    "D": "Damaged",
    "R": "Remains",
    "T": "Toppled",
    "M": "Moved",
    "Q": "Possibly missing",
    "X": "Destroyed",
    "V": "Unreachable but visible",
    "P": "Inaccessible",
    "U": "Unknown",
}


def get_condition_description(condition_code: str, db: Optional[Session] = None) -> str:
    """
    Convert condition code to human-readable description.

    If a database session is provided, looks up the condition name from the
    condition table. Otherwise, uses a hardcoded fallback mapping.

    Args:
        condition_code: Single character condition code
        db: Optional database session for dynamic lookup

    Returns:
        Human-readable condition description
    """
    code = str(condition_code).upper()

    # Try database lookup if session provided
    if db is not None:
        from api.crud.condition import get_condition_name_by_code

        name = get_condition_name_by_code(db, code)
        if name:
            return name

    # Fall back to hardcoded mapping
    return FALLBACK_CONDITION_MAP.get(code, "Unknown")


def get_condition_counts_by_description(
    condition_counts: Dict[str, int], db: Optional[Session] = None
) -> Dict[str, int]:
    """
    Convert condition code counts to human-readable description counts.

    If a database session is provided, uses database lookups for condition names.
    Otherwise, uses hardcoded fallback values.

    Args:
        condition_counts: Dictionary mapping condition codes to counts
        db: Optional database session for dynamic lookup

    Returns:
        Dictionary mapping human-readable descriptions to counts
    """
    result: Dict[str, int] = {}
    for code, count in condition_counts.items():
        description = get_condition_description(code, db)
        if description in result:
            result[description] += count
        else:
            result[description] = count

    return result


def build_condition_map_from_db(db: Session) -> Dict[str, str]:
    """
    Build a condition code to name mapping from the database.

    Args:
        db: Database session

    Returns:
        Dictionary mapping condition codes to names
    """
    from api.crud.condition import get_all_conditions

    conditions = get_all_conditions(db)
    return {str(c.code): str(c.name) for c in conditions}
