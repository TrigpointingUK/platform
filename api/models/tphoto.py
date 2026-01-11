"""
SQLAlchemy model for the tphoto table - trigpoint photos and thumbnails.
"""

from datetime import datetime

from sqlalchemy import CHAR, TIMESTAMP, Column, ForeignKey, Integer, String, Text

from api.db.database import Base


class TPhoto(Base):
    """TPhoto model for the tphoto table.

    Note: MEDIUMINT mapped to Integer for cross-DB compatibility.
    """

    __tablename__ = "tphoto"

    id = Column(Integer, primary_key=True, index=True)
    tlog_id = Column(
        Integer, ForeignKey("tlog.id", ondelete="SET NULL"), nullable=True, index=True
    )
    server_id = Column(
        Integer,
        ForeignKey("server.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Photo type: e.g., 'T' (trig), 'F' (FB), 'L' (landscape), etc.
    type = Column(CHAR(1), nullable=False)

    # Filenames are relative to the server base URL and path
    filename = Column(String(255), nullable=False)
    filesize = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)

    # Thumbnail/icon information
    icon_filename = Column(String(255), nullable=False)
    icon_filesize = Column(Integer, nullable=False)
    icon_height = Column(Integer, nullable=False)
    icon_width = Column(Integer, nullable=False)

    # Metadata
    name = Column(String(80), nullable=False)
    text_desc = Column(Text, nullable=False)
    ip_addr = Column(String(15), nullable=False)
    public_ind = Column(CHAR(1), nullable=False)  # 'Y' or 'N'
    deleted_ind = Column(CHAR(1), nullable=False)  # 'Y' or 'N' (soft delete)
    source = Column(CHAR(1), nullable=False)
    crt_timestamp = Column(TIMESTAMP, nullable=True, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TPhoto(id={self.id}, tlog_id={self.tlog_id}, name='{self.name}')>"
