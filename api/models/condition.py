"""
SQLAlchemy model for the condition lookup table.
"""

from sqlalchemy import CHAR, Column, SmallInteger, String

from api.db.database import Base


class Condition(Base):
    """Lookup of condition code to human-readable name and display properties."""

    __tablename__ = "condition"

    code = Column(CHAR(1), primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    icon_file = Column(String(100), nullable=True)
    trig_colour = Column(String(20), nullable=True)
    log_colour = Column(String(20), nullable=True)
    similar_codes = Column(String(10), nullable=True)
    wiki_url = Column(String(255), nullable=True)
    sort_order = Column(SmallInteger, nullable=False)

    def __repr__(self):
        return f"<Condition(code='{self.code}', name='{self.name}')>"
