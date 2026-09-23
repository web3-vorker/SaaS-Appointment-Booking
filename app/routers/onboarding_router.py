from datetime import datetime, time, timedelta
import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config.config import config
from app.db.database import SessionDep
from app.models.business import BusinessModel
from app.redis.cache_keys import key_business_by_api_key
from app.redis.redis_cache import redis_cache
from app.repository.repository import Repository
from app.schemas.onboarding import (
    OnboardingBusinessActivateRequest,
    OnboardingBusinessResponse,
    OnboardingBusinessStatusResponse,
)
from app.schemas.business import BusinessCreateSchema

onboarding_router = APIRouter(
    prefix="/internal/onboarding",
    tags=["Onboarding"],
)


async def verify_onboarding_service_key(
    x_onboarding_service_key: str = Header(..., alias="X-Onboarding-Service-Key"),
) -> None:
    if not config.onboarding_service_key or not secrets.compare_digest(
        x_onboarding_service_key,
        config.onboarding_service_key,
    ):
        raise HTTPException(status_code=401, detail="Invalid onboarding service key")


def _parse_time(value: str | None) -> time | None:
    if value is None:
        return None
    hour, minute = map(int, value.split(":"))
    return time(hour=hour, minute=minute)


def _status(business: BusinessModel) -> str:
    return "active" if business.is_active else "pending"


def _business_response(
    business: BusinessModel,
    *,
    include_api_key: bool,
) -> OnboardingBusinessResponse:
    return OnboardingBusinessResponse(
        business_id=business.id,
        onboarding_id=business.onboarding_id,
        name=business.name,
        owner_tg_id=business.owner_tg_id,
        api_key=business.api_key if include_api_key else None,
        is_active=business.is_active,
        subscription_plan=business.subscription_plan,
        subscription_expires_at=business.subscription_expires_at,
        status=_status(business),
    )


@onboarding_router.post(
    "/businesses",
    response_model=OnboardingBusinessResponse,
    dependencies=[Depends(verify_onboarding_service_key)],
)
async def create_onboarding_business(
    data: BusinessCreateSchema,
    session: SessionDep,
) -> OnboardingBusinessResponse:
    existing_result = await session.execute(
        select(BusinessModel).where(BusinessModel.onboarding_id == data.onboarding_id)
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return _business_response(existing, include_api_key=True)

    working_start = _parse_time(data.working_hours_start)
    working_end = _parse_time(data.working_hours_end)
    if working_end <= working_start:
        raise HTTPException(status_code=422, detail="working_hours_end must be after working_hours_start")

    business = BusinessModel(
        name=data.name,
        working_time_start=working_start,
        working_time_end=working_end,
        break_start=_parse_time(data.break_start),
        break_end=_parse_time(data.break_end),
        weekend_days=data.weekend_days,
        owner_tg_id=data.owner_tg_id,
        onboarding_id=data.onboarding_id,
        subscription_plan=data.subscription_plan,
        subscription_expires_at=None,
        is_active=False,
        api_key=str(uuid.uuid4()),
    )
    session.add(business)
    try:
        await session.commit()
        await session.refresh(business)
    except IntegrityError as exc:
        await session.rollback()
        existing_result = await session.execute(
            select(BusinessModel).where(BusinessModel.onboarding_id == data.onboarding_id)
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            return _business_response(existing, include_api_key=True)
        raise HTTPException(status_code=409, detail="Business registration conflict") from exc

    return _business_response(business, include_api_key=True)


@onboarding_router.post(
    "/businesses/{business_id}/activate",
    response_model=OnboardingBusinessResponse,
    dependencies=[Depends(verify_onboarding_service_key)],
)
async def activate_onboarding_business(
    business_id: int,
    data: OnboardingBusinessActivateRequest,
    session: SessionDep,
) -> OnboardingBusinessResponse:
    repository = Repository(session)
    business = await repository.get_business_by_id(business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")

    business.is_active = True
    business.subscription_plan = data.subscription_plan or business.subscription_plan
    business.subscription_expires_at = data.subscription_expires_at or (
        datetime.utcnow() + timedelta(days=config.subscription_duration)
    )
    await session.commit()
    await session.refresh(business)
    await redis_cache.delete_cache(key_business_by_api_key(business.api_key))

    return _business_response(business, include_api_key=False)


@onboarding_router.post(
    "/businesses/{business_id}/deactivate",
    response_model=OnboardingBusinessStatusResponse,
    dependencies=[Depends(verify_onboarding_service_key)],
)
async def deactivate_onboarding_business(
    business_id: int,
    session: SessionDep,
) -> OnboardingBusinessStatusResponse:
    repository = Repository(session)
    business = await repository.get_business_by_id(business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")

    business.is_active = False
    await session.commit()
    await session.refresh(business)
    await redis_cache.delete_cache(key_business_by_api_key(business.api_key))

    return OnboardingBusinessStatusResponse(
        business_id=business.id,
        onboarding_id=business.onboarding_id,
        owner_tg_id=business.owner_tg_id,
        is_active=business.is_active,
        subscription_plan=business.subscription_plan,
        subscription_expires_at=business.subscription_expires_at,
        status=_status(business),
    )


@onboarding_router.get(
    "/businesses/{business_id}",
    response_model=OnboardingBusinessStatusResponse,
    dependencies=[Depends(verify_onboarding_service_key)],
)
async def get_onboarding_business_status(
    business_id: int,
    session: SessionDep,
) -> OnboardingBusinessStatusResponse:
    repository = Repository(session)
    business = await repository.get_business_by_id(business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")

    return OnboardingBusinessStatusResponse(
        business_id=business.id,
        onboarding_id=business.onboarding_id,
        owner_tg_id=business.owner_tg_id,
        is_active=business.is_active,
        subscription_plan=business.subscription_plan,
        subscription_expires_at=business.subscription_expires_at,
        status=_status(business),
    )
