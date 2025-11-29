"""
Database models for the existing legacy database schema.
"""

from datetime import date, datetime, time

from sqlalchemy import Column, Date, DateTime, Integer, SmallInteger, String, Text, Time
from sqlalchemy.types import CHAR

from api.db.database import Base


class User(Base):
    """User model matching the existing legacy database schema."""

    __tablename__ = "user"

    # Primary identifier
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Core identity fields
    name = Column(String(30), nullable=False, index=True, unique=True)  # Username
    firstname = Column(
        String(30), nullable=True, default=""
    )  # Nullable for PostgreSQL compatibility
    surname = Column(
        String(30), nullable=True, default=""
    )  # Nullable for PostgreSQL compatibility
    email = Column(
        String(255), nullable=True, default="", index=True
    )  # Nullable for PostgreSQL compatibility
    email_valid = Column(
        CHAR(1), nullable=True, default="N"
    )  # Nullable for PostgreSQL compatibility
    email_ind = Column(
        CHAR(1), nullable=True, default="N"
    )  # Nullable for PostgreSQL compatibility
    homepage = Column(
        String(255), nullable=True, default=""
    )  # Nullable for PostgreSQL compatibility
    distance_ind = Column(
        CHAR(1), nullable=True, default="K"
    )  # Nullable for PostgreSQL compatibility
    about = Column(
        Text, nullable=True, default=""
    )  # Nullable for PostgreSQL compatibility
    status_max = Column(
        Integer, nullable=True, default=0
    )  # Nullable for PostgreSQL compatibility

    # License preferences
    public_ind = Column(
        CHAR(1), nullable=True, default="N"
    )  # Nullable for PostgreSQL compatibility

    # Legacy authentication - increased size for modern password hashes
    cryptpw = Column(
        String(100), nullable=True, default=""
    )  # Nullable for PostgreSQL compatibility

    # Auth0 integration
    auth0_user_id = Column(String(50), nullable=True, index=True)

    # Timestamps
    crt_date = Column(
        Date, nullable=True, default=date(1900, 1, 1)
    )  # Nullable for PostgreSQL compatibility
    crt_time = Column(
        Time, nullable=True, default=time(0, 0, 0)
    )  # Nullable for PostgreSQL compatibility
    upd_timestamp = Column(
        DateTime, nullable=True, default=datetime.now
    )  # Nullable for PostgreSQL compatibility

    # Display and search preferences
    online_map_type = Column(
        String(10), nullable=True, default=""
    )  # Nullable for PostgreSQL compatibility
    online_map_type2 = Column(
        String(10), nullable=True, default="lla"
    )  # Nullable for PostgreSQL compatibility


class TLog(Base):
    """TLog model for the tlog table."""

    __tablename__ = "tlog"

    id = Column(Integer, primary_key=True, index=True)
    trig_id = Column(
        Integer, index=True, nullable=True
    )  # Nullable for PostgreSQL compatibility
    user_id = Column(
        Integer, index=True, nullable=True
    )  # Nullable for PostgreSQL compatibility
    date = Column(Date, nullable=True)  # Nullable for PostgreSQL compatibility
    time = Column(Time, nullable=True)  # Nullable for PostgreSQL compatibility
    osgb_eastings = Column(Integer, nullable=True)
    osgb_northings = Column(Integer, nullable=True)
    osgb_gridref = Column(String(14), nullable=True)
    fb_number = Column(
        String(10), nullable=True
    )  # Nullable for PostgreSQL compatibility
    condition = Column(CHAR(1), nullable=True)  # Nullable for PostgreSQL compatibility
    comment = Column(Text, nullable=True)  # Nullable for PostgreSQL compatibility
    score = Column(SmallInteger, nullable=True)  # Nullable for PostgreSQL compatibility
    ip_addr = Column(String(15), nullable=True)  # Nullable for PostgreSQL compatibility
    source = Column(CHAR(1), nullable=True)  # Nullable for PostgreSQL compatibility
    upd_timestamp = Column(
        DateTime, nullable=True, default=datetime.now
    )  # Nullable for PostgreSQL compatibility


class TPhotoVote(Base):
    """TPhotoVote model for the tphotovote table."""

    __tablename__ = "tphotovote"

    id = Column(Integer, primary_key=True, index=True)
    tphoto_id = Column(Integer, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)
    score = Column(SmallInteger, nullable=False)
    upd_timestamp = Column(DateTime, nullable=True)


class TQuery(Base):
    """TQuery model for the tquery table."""

    __tablename__ = "tquery"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(CHAR(1), nullable=False)
    text = Column(Text, nullable=False)
    sql_from = Column(Text, nullable=False)
    sql_where = Column(Text, nullable=False)
    sql_having = Column(Text, nullable=False)
    sql_order = Column(Text, nullable=False)
    osgb_eastings = Column(Integer, nullable=False)
    osgb_northings = Column(Integer, nullable=False)
    user_id = Column(Integer, index=True, nullable=True)
    system_ind = Column(CHAR(1), nullable=False)
    upd_timestamp = Column(DateTime, nullable=True)
    crt_timestamp = Column(DateTime, nullable=True)


class TQuizScores(Base):
    """TQuizScores model for the tquizscores table."""

    __tablename__ = "tquizscores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    quiz_date = Column(Date, nullable=False)
    quiz_time = Column(Time, nullable=False)
    score = Column(SmallInteger, nullable=False)
    outof = Column(SmallInteger, nullable=False)
    upd_timestamp = Column(DateTime, nullable=True)
    crt_timestamp = Column(DateTime, nullable=True)
