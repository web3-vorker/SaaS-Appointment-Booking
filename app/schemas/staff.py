from pydantic import BaseModel, Field

class StaffCreateSchema(BaseModel):
  name: str
  business_id: int
  role: str