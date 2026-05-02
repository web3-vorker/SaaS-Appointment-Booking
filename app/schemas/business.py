from pydantic import BaseModel, Field
from typing import Optional

class BusinessCreateSchema(BaseModel):
  name: str = Field(min_length=2, max_length=50)
  owner_tg_id: int
  bot_token: Optional[str] = Field(default=None, min_length=10, max_length=255)