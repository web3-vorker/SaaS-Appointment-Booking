from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional

class BusinessCreateSchema(BaseModel):
    onboarding_id: str = Field(default=None, min_length=1, max_length=128)
    name: str = Field(min_length=2, max_length=50)
    owner_tg_id: int
    working_hours_start: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    working_hours_end: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    break_start: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    break_end: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    weekend_days: list[int] = Field(default_factory=list)
    subscription_plan: str = Field(default="Base", min_length=1, max_length=32)

    @field_validator("weekend_days")
    @classmethod
    def validate_weekend_days(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("weekend_days must contain values from 0 to 6")
        return sorted(set(value))

    @model_validator(mode="before")
    def normalize_subscription_plan(cls, data):
      if isinstance(data, dict) and data.get("subscription_plan") is None:
        data["subscription_plan"] = "Base"
      return data
