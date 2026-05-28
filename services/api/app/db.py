"""
Database configuration and models for PR Review Agent.

Supports both SQLite (development) and PostgreSQL (production) via DATABASE_URL env var.
"""

import os
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Use SQLite for development, allow PostgreSQL for production
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./reviews.db")

# Configure engine based on database type
if "sqlite" in DB_URL:
    engine = create_engine(
        DB_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL or other databases
    engine = create_engine(DB_URL)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class ReviewRecord(Base):
    """Database model for storing PR reviews and feedback."""

    __tablename__ = "reviews"

    id = Column(String, primary_key=True, index=True)
    pr_url = Column(String, nullable=False, index=True)
    pr_title = Column(String, nullable=True)
    status = Column(String, default="completed")  # pending, in_progress, completed, failed
    result = Column(Text, nullable=True)  # JSON serialized ReviewSummary
    feedback = Column(JSON, nullable=True)  # User feedback from UI
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(String, nullable=True)

    def __repr__(self):
        return f"<ReviewRecord(id={self.id}, status={self.status}, score={self.result})>"


# Create tables on module import
Base.metadata.create_all(bind=engine)
