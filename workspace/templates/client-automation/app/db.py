"""
Database setup using SQLAlchemy.
Supports SQLite (local) or PostgreSQL (Railway).
"""

from sqlalchemy import create_engine, Column, String, DateTime, JSON, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from .config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ExecutionLog(Base):
    """Log of automation executions with step-level detail."""

    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(36), unique=True, index=True)
    automation_id = Column(String(100), index=True)
    trigger = Column(String(50))  # "cron", "webhook", "manual"
    status = Column(String(20))   # "success", "failed", "auto_resolved"
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    steps = Column(JSON)  # List of step details
    error = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)


class AutomationSettings(Base):
    """Enable/disable state for each automation."""

    __tablename__ = "automation_settings"

    id = Column(Integer, primary_key=True, index=True)
    automation_id = Column(String(100), unique=True, index=True, nullable=False)
    enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_or_create_automation_setting(db: SessionLocal, automation_id: str) -> AutomationSettings:
    """Get existing setting or create new one (disabled by default)."""
    setting = db.query(AutomationSettings).filter(
        AutomationSettings.automation_id == automation_id
    ).first()

    if not setting:
        setting = AutomationSettings(automation_id=automation_id, enabled=False)
        db.add(setting)
        db.commit()
        db.refresh(setting)

    return setting


def init_db():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
