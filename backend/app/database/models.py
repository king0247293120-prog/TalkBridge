from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    Float,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


class TranslationEntry(Base):
    __tablename__ = "translation_entries"

    id = Column(Integer, primary_key=True, index=True)

    source_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)

    source_language = Column(String(50), nullable=False, index=True)
    target_language = Column(String(50), nullable=False, index=True)

    # Examples: database, open_source_model, human
    provider = Column(String(100), default="open_source_model")

    # pending, verified, rejected
    status = Column(String(20), default="pending", nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    reports = relationship(
        "TranslationReport",
        back_populates="translation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_translation_language_pair",
            "source_language",
            "target_language",
        ),
    )
    # human or machine
    translation_method = Column(
        String(20),
        nullable=False,
        default="machine",
    )

    # Optional translation confidence score
    confidence = Column(Float, nullable=True)

class TranslationReport(Base):
    __tablename__ = "translation_reports"

    id = Column(Integer, primary_key=True, index=True)

    translation_id = Column(
        Integer,
        ForeignKey("translation_entries.id"),
        nullable=False,
    )

    reason = Column(Text, nullable=False)
    suggested_correction = Column(Text, nullable=True)

    # pending, reviewed, resolved
    status = Column(String(20), default="pending", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    translation = relationship(
        "TranslationEntry",
        back_populates="reports",
    )