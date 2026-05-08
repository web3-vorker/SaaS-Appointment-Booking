from pydantic import BaseModel, Field

class StaffServiceCreateSchema(BaseModel):
  business_id: int
  staff_id: int
  service_id: int