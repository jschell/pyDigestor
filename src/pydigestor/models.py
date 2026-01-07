"""Database models for pyDigestor."""

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlmodel import Column, Field, SQLModel
from sqlalchemy import Text, ForeignKey, TypeDecorator


class JSONText(TypeDecorator):
    """Custom type to store JSON as TEXT in SQLite."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Serialize dict to JSON string before storing."""
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        """Deserialize JSON string to dict when retrieving."""
        if value is not None:
            return json.loads(value)
        return None


class Article(SQLModel, table=True):
    """Article model for storing fetched content."""

    __tablename__ = "articles"

    # UUID stored as TEXT in SQLite
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        sa_column=Column(Text, primary_key=True),
    )
    source_id: str = Field(unique=True, index=True, description="Unique ID from source")
    url: str = Field(description="Target URL (actual content location)")
    title: str = Field(description="Article title")
    content: str | None = Field(default=None, description="Full extracted text")
    summary: str | None = Field(default=None, description="Local extractive summary")
    published_at: datetime | None = Field(default=None, description="Original publish date")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="When we fetched it")
    status: str = Field(
        default="pending",
        description="Processing status: pending, triaged, processed, failed",
    )
    # JSON stored as TEXT in SQLite with automatic serialization
    meta: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONText),
        description="Feed source, Reddit score, extraction method, etc.",
    )

    class Config:
        arbitrary_types_allowed = True


class TriageDecision(SQLModel, table=True):
    """Triage decisions from LLM."""

    __tablename__ = "triage_decisions"

    # UUID stored as TEXT in SQLite
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        sa_column=Column(Text, primary_key=True),
    )
    article_id: str = Field(
        sa_column=Column(Text, ForeignKey("articles.id"), index=True),
    )
    keep: bool = Field(description="Whether to keep this article")
    reasoning: str | None = Field(default=None, description="LLM reasoning for decision")
    confidence: float | None = Field(
        default=None, description="Confidence score (0-1)", ge=0, le=1
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True


class Signal(SQLModel, table=True):
    """Extracted signals/insights from articles."""

    __tablename__ = "signals"

    # UUID stored as TEXT in SQLite
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        sa_column=Column(Text, primary_key=True),
    )
    article_id: str = Field(
        sa_column=Column(Text, ForeignKey("articles.id"), index=True),
    )
    signal_type: str = Field(
        index=True,
        description="Type: vulnerability, tool, technique, trend, threat_actor, etc.",
    )
    content: str = Field(description="Signal content/description")
    confidence: float | None = Field(
        default=None, description="Confidence score (0-1)", ge=0, le=1
    )
    # JSON stored as TEXT in SQLite with automatic serialization
    meta: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONText),
        description="Additional signal metadata",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    class Config:
        arbitrary_types_allowed = True
