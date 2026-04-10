"""
SQLAlchemy model for the trigstats table.
"""

from typing import Any

from sqlalchemy import DATE, DECIMAL, INTEGER, TIMESTAMP, Column, ForeignKey

from api.db.database import Base


class TrigStats(Base):
    """Statistics for a trigpoint, keyed by trig.id."""

    __tablename__ = "trigstats"

    # Primary key and FK to trig.id (not declared as FK due to legacy DB constraints)
    id = Column(INTEGER, ForeignKey("trig.id", ondelete="CASCADE"), primary_key=True)

    # Log related stats
    logged_first = Column(DATE, nullable=True)  # NULL if never logged
    logged_last = Column(DATE, nullable=True)  # NULL if never logged
    logged_count = Column(INTEGER, nullable=False)

    # Found related stats
    found_last = Column(DATE, nullable=True)  # NULL if never found
    found_count = Column(INTEGER, nullable=False)

    # Photos
    photo_count = Column(INTEGER, nullable=False)

    # Scores
    score_mean: Any = Column(DECIMAL(5, 2), nullable=False)
    score_baysian: Any = Column(DECIMAL(5, 2), nullable=False)

    # Coordinate discrepancy monitoring (nullable - populated incrementally)
    # Distance in metres between WGS84->OSTN15 and stored OSGB coords
    dist_wgs_osgb: Any = Column(DECIMAL(10, 4), nullable=True)
    # Distance in metres between trig.osgb* and attrval OSGB coords (attr_id 4,5)
    dist_osgb_osgb: Any = Column(DECIMAL(10, 4), nullable=True)

    # Audit
    upd_timestamp = Column(TIMESTAMP, nullable=True)

    def __repr__(self):
        return f"<TrigStats(id={self.id}, logged_count={self.logged_count}, photo_count={self.photo_count})>"
