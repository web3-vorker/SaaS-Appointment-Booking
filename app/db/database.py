from typing import Annotated
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


DATABASE_URL = os.getenv("DATABASE_URL")


engine = create_async_engine(DATABASE_URL)
new_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
  async with new_session() as session:
    yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]