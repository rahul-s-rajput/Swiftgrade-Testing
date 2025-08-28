from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import relationship
import uuid

from .db import Base


class SessionModel(Base):
    __tablename__ = "session"

    id = Column(String(36), primary_key=True, index=True)
    status = Column(String(32), nullable=False, default="created")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # relationships (not strictly needed for this story)
    # images = relationship("ImageModel", back_populates="session", cascade="all, delete-orphan")


class ImageModel(Base):
    __tablename__ = "image"
    __table_args__ = (
        UniqueConstraint("session_id", "url", name="uq_image_session_url"),
        UniqueConstraint("session_id", "role", "order_index", name="uq_image_session_role_order"),
        CheckConstraint("role in ('student','answer_key')", name="ck_image_role"),
        CheckConstraint("order_index >= 0", name="ck_image_order_index_nonneg"),
    )

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("session.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False)
    url = Column(Text, nullable=False)
    order_index = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # session = relationship("SessionModel", back_populates="images")
