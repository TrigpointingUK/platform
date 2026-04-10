"""
SQLAlchemy model for the server table which stores photo base URLs.
"""

from sqlalchemy import Column, Integer, String

from api.db.database import Base


class Server(Base):
    __tablename__ = "server"

    id = Column(Integer, primary_key=True)
    url = Column(String(255), nullable=False)
    path = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
