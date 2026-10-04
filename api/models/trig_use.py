"""
SQLAlchemy models for the historic use and recent (current) use lookups.

trig.historic_use and trig.current_use hold the value's name as a string (a
legacy of the MySQL schema), so these tables are the list of allowed values
rather than a foreign key target. The API keeps the two in step: renaming a
value updates the trigs using it, and a value in use can't be deleted.
"""

from sqlalchemy import Column, Integer, SmallInteger, String

from api.db.database import Base


class HistoricUse(Base):
    """An allowed value for trig.historic_use, e.g. "Primary"."""

    __tablename__ = "trig_historic_use"

    id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    sort_order = Column(SmallInteger, nullable=False)

    def __repr__(self):
        return f"<HistoricUse(id={self.id}, name='{self.name}')>"


class CurrentUse(Base):
    """An allowed value for trig.current_use ("Recent use"), e.g. "Passive station"."""

    __tablename__ = "trig_current_use"

    id = Column(Integer, primary_key=True)
    name = Column(String(25), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    sort_order = Column(SmallInteger, nullable=False)

    def __repr__(self):
        return f"<CurrentUse(id={self.id}, name='{self.name}')>"
