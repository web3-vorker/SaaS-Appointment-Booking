from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.config import config


engine = create_async_engine(config.database_url)
new_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
  async with new_session() as session:
    yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]