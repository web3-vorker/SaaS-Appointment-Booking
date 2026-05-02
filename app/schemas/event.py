from pydantic import BaseModel, Field
from pydantic import ConfigDict
from typing import Any
from datetime import datetime


class EventPayloadSchema(BaseModel):
    client_tg_id: int = Field(...)
    text: str = Field(...)


class EventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    business_id: int
    appointment_id: int
    payload: EventPayloadSchema
    is_sent: bool
    created_at: datetime
