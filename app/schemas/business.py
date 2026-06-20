from pydantic import BaseModel, Field, model_validator
from typing import Optional

class BusinessCreateSchema(BaseModel):
  name: str = Field(min_length=2, max_length=50)
  working_hours_start: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
  working_hours_end: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
  break_start: str = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
  break_end: str = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
  weekend_days: str = Field(default=None, pattern=r"^(?:[1-7],)*[1-7]$")  # Например: "6,7" для выходных в субботу и воскресенье
  owner_tg_id: int
  subscription_plan: str = Field(default="Base")

  @model_validator(mode="before")
  def normalize_subscription_plan(cls, data):
    if isinstance(data, dict) and data.get("subscription_plan") is None:
      data["subscription_plan"] = "Base"
    return data