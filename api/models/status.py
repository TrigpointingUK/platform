"""
SQLAlchemy model for the status lookup table.
"""

from sqlalchemy import CHAR, Column, Integer, String

from api.db.database import Base


class Status(Base):
    """Lookup of status id to human-readable name and descriptions."""

    __tablename__ = "status"

    id = Column(Integer, primary_key=True)
    name = Column(CHAR(20), nullable=False)
    descr = Column(String(50), nullable=False)
    limit_descr = Column(String(255), nullable=False)

    def __repr__(self):
        return f"<Status(id={self.id}, name='{self.name}')>"
