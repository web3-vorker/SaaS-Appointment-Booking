from pydantic import BaseModel, Field
from typing import Optional

class BusinessCreateSchema(BaseModel):
  name: str = Field(min_length=2, max_length=50)
  working_hours_start: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
  working_hours_end: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
  owner_tg_id: int
  bot_token: Optional[str] = Field(default=None, min_length=10, max_length=255)