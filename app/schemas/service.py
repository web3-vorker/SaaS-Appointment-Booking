from pydantic import BaseModel, Field

class ServiceCreateSchema(BaseModel):
  business_id: int
  name: str
  price: int
  description: str | None = None
  duration_minutes: int