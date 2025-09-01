# NOTE: This file is not currently used since we're using the Supabase client directly
# instead of SQLAlchemy. Keeping it here for potential future use.

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator


def _database_url() -> str:
    url = os.getenv("SUPABASE_DB_URL")
    if not url:
        # For now, we're using Supabase client directly, so this is optional
        return "sqlite:///./test.db"  # Fallback for local testing
    return url


engine = None
SessionLocal = None
Base = declarative_base()

# Only initialize if DB URL is provided
if os.getenv("SUPABASE_DB_URL"):
    engine = create_engine(
        _database_url(),
        future=True,
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Generator:
    if SessionLocal is None:
        raise RuntimeError("Database not configured. Using Supabase client instead.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
