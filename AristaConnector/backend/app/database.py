from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import os
from urllib.parse import urlparse

# Convert postgresql:// to postgresql+asyncpg://
database_url = os.getenv("DATABASE_URL", "postgresql://arista:arista123@localhost:5432/arista")
parsed = urlparse(database_url)
if parsed.scheme == "postgresql":
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # Import models to register them
        from app.models import Device, DeviceIdentity, Event  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
