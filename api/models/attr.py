"""
SQLAlchemy models for the attr tables - attribute data from various sources.
"""

from sqlalchemy import TIMESTAMP, Column, Integer, String, Text

from api.db.database import Base

# Note: TINYINT is MySQL-specific, using Integer for compatibility


class AttrSource(Base):
    """AttrSource model - data sources for attribute information."""

    __tablename__ = "attrsource"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    descr = Column(Text, nullable=True)
    url = Column(String(255), nullable=True)
    sort_order = Column(Integer, nullable=False)
    crt_timestamp = Column(TIMESTAMP, nullable=True)

    def __repr__(self):
        return f"<AttrSource(id={self.id}, name='{self.name}')>"


class Attr(Base):
    """Attr model - attribute definitions (column headers)."""

    __tablename__ = "attr"

    id = Column(Integer, primary_key=True, index=True)
    attrsource_id = Column(Integer, nullable=False)
    name = Column(String(45), nullable=False)
    description = Column(String(255), nullable=False)
    mandatory = Column(Integer, nullable=False)
    multivalued = Column(Integer, nullable=False)
    grouped = Column(Integer, nullable=False)
    sort_order = Column(Integer, nullable=False)
    style = Column(String(45), nullable=True)
    url_javaclass = Column(String(45), nullable=True)
    type = Column(String(45), nullable=True)
    upd_timestamp = Column(TIMESTAMP, nullable=True)

    def __repr__(self):
        return f"<Attr(id={self.id}, name='{self.name}')>"


class AttrSet(Base):
    """AttrSet model - groups of attributes for a trig."""

    __tablename__ = "attrset"

    id = Column(Integer, primary_key=True, index=True)
    trig_id = Column(Integer, nullable=False, index=True)
    attrsource_id = Column(Integer, nullable=False)
    sort_order = Column(Integer, nullable=False)
    upd_timestamp = Column(TIMESTAMP, nullable=True)

    def __repr__(self):
        return f"<AttrSet(id={self.id}, trig_id={self.trig_id})>"


class AttrVal(Base):
    """AttrVal model - individual attribute values."""

    __tablename__ = "attrval"

    id = Column(Integer, primary_key=True, index=True)
    attr_id = Column(Integer, nullable=False)
    value_string = Column(String(255), nullable=True)
    value_double = Column(String(255), nullable=True)  # Using String for compatibility
    value_bool = Column(Integer, nullable=True)
    value_point = Column(Text, nullable=True)
    group_name = Column(String(255), nullable=True)
    upd_timestamp = Column(TIMESTAMP, nullable=True)

    def __repr__(self):
        return f"<AttrVal(id={self.id}, attr_id={self.attr_id})>"


class AttrSetAttrVal(Base):
    """AttrSetAttrVal model - junction table linking attrsets to attrvals."""

    __tablename__ = "attrset_attrval"

    attrset_id = Column(Integer, primary_key=True)
    attrval_id = Column(Integer, primary_key=True)
    upd_timestamp = Column(TIMESTAMP, nullable=True)

    def __repr__(self):
        return f"<AttrSetAttrVal(attrset_id={self.attrset_id}, attrval_id={self.attrval_id})>"
