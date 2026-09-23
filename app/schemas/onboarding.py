from datetime import datetime

from pydantic import BaseModel, Field


class OnboardingBusinessActivateRequest(BaseModel):
    subscription_plan: str | None = Field(default=None, min_length=1, max_length=32)
    subscription_expires_at: datetime | None = None


class OnboardingBusinessResponse(BaseModel):
    business_id: int
    onboarding_id: str
    name: str
    owner_tg_id: int
    api_key: str | None = None
    is_active: bool
    subscription_plan: str | None = None
    subscription_expires_at: datetime | None = None
    status: str


class OnboardingBusinessStatusResponse(BaseModel):
    business_id: int
    onboarding_id: str
    owner_tg_id: int
    is_active: bool
    subscription_plan: str | None = None
    subscription_expires_at: datetime | None = None
    status: str
