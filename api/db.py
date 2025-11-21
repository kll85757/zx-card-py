from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus
from .config import settings


if getattr(settings, "use_sqlite", False):
    DATABASE_URL = f"sqlite:///{settings.sqlite_path}"
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # URL encode password to handle special characters like @
    encoded_password = quote_plus(settings.mysql_password)
    DATABASE_URL = (
        f"mysql+pymysql://{settings.mysql_user}:{encoded_password}"
        f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_db}?charset=utf8mb4"
    )
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
