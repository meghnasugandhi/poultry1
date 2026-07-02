from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
engine = create_async_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA busy_timeout=30000")
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
            except Exception:
                pass
        finally:
            cursor.close()


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
