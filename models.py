from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Boolean, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class TechCard(Base):
    """
    SQLAlchemy ORM Model representing a technical news card in the database.
    """
    __tablename__ = "tech_cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    replaces_or_differs_from: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technical_tradeoffs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    core_concept: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    concept_definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_analyzed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<TechCard id={self.id} title='{self.title[:30]}' source='{self.source}' is_analyzed={self.is_analyzed}>"


class PoliticsCard(Base):
    """
    SQLAlchemy ORM Model representing a politics news card in the database.
    """
    __tablename__ = "politics_cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    today_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rational_arguments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    historical_background: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    core_concept: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    concept_definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_analyzed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<PoliticsCard id={self.id} title='{self.title[:30]}' source='{self.source}' is_analyzed={self.is_analyzed}>"


class FootballCard(Base):
    """
    SQLAlchemy ORM Model representing a football news card in the database.
    """
    __tablename__ = "football_cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    today_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rational_arguments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    historical_background: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    core_concept: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    concept_definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_analyzed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<FootballCard id={self.id} title='{self.title[:30]}' source='{self.source}' is_analyzed={self.is_analyzed}>"




