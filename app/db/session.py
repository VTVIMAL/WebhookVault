from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import get_settings

settings = get_settings()

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()