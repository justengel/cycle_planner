from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, create_engine
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid

from app.config import get_settings

Base = declarative_base()


class LessonPlanDB(Base):
    __tablename__ = "lesson_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Text, nullable=False, default="default-dev-user", index=True)
    theme = Column(Text, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    plan_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


def get_database_url() -> str:
    """Get PostgreSQL URL from config."""
    settings = get_settings()
    if not settings.database_url:
        raise ValueError("DATABASE_URL not set in .env")
    return settings.database_url


def get_engine():
    return create_engine(get_database_url())


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
