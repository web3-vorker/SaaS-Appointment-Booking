import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import BusinessModel


ONBOARDING_HEADERS = {"X-Onboarding-Service-Key": "test-onboarding-key-12345"}


def create_payload(onboarding_id: str = "onboarding-001") -> dict:
    return {
        "onboarding_id": onboarding_id,
        "name": "Test Onboarding Salon",
        "owner_tg_id": 123456789,
        "working_hours_start": "09:00",
        "working_hours_end": "18:00",
        "break_start": "13:00",
        "break_end": "14:00",
        "weekend_days": [5, 6],
        "subscription_plan": "Base",
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_business_returns_key_and_starts_inactive(
    api_client: AsyncClient,
    db_session: AsyncSession,
):
    response = await api_client.post(
        "/internal/onboarding/businesses",
        json=create_payload(),
        headers=ONBOARDING_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["business_id"] > 0
    assert body["onboarding_id"] == "onboarding-001"
    assert body["api_key"]
    assert body["is_active"] is False
    assert body["status"] == "pending"

    business = await db_session.get(BusinessModel, body["business_id"])
    assert business is not None
    assert business.is_active is False
    assert business.api_key == body["api_key"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_business_is_idempotent(
    api_client: AsyncClient,
):
    first = await api_client.post(
        "/internal/onboarding/businesses",
        json=create_payload("same-onboarding"),
        headers=ONBOARDING_HEADERS,
    )
    second = await api_client.post(
        "/internal/onboarding/businesses",
        json=create_payload("same-onboarding"),
        headers=ONBOARDING_HEADERS,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["business_id"] == first.json()["business_id"]
    assert second.json()["api_key"] == first.json()["api_key"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_business_requires_service_key(api_client: AsyncClient):
    response = await api_client.post(
        "/internal/onboarding/businesses",
        json=create_payload(),
    )

    assert response.status_code == 422

    response = await api_client.post(
        "/internal/onboarding/businesses",
        json=create_payload(),
        headers={"X-Onboarding-Service-Key": "wrong-key"},
    )
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_business_rejects_invalid_working_hours(api_client: AsyncClient):
    payload = create_payload("invalid-hours")
    payload["working_hours_start"] = "18:00"
    payload["working_hours_end"] = "09:00"

    response = await api_client.post(
        "/internal/onboarding/businesses",
        json=payload,
        headers=ONBOARDING_HEADERS,
    )

    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_activate_status_and_deactivate_business(
    api_client: AsyncClient,
    mock_redis,
):
    create_response = await api_client.post(
        "/internal/onboarding/businesses",
        json=create_payload("lifecycle-onboarding"),
        headers=ONBOARDING_HEADERS,
    )
    business_id = create_response.json()["business_id"]

    activate_response = await api_client.post(
        f"/internal/onboarding/businesses/{business_id}/activate",
        json={"subscription_plan": "Pro"},
        headers=ONBOARDING_HEADERS,
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True
    assert activate_response.json()["status"] == "active"
    assert activate_response.json()["api_key"] is None

    status_response = await api_client.get(
        f"/internal/onboarding/businesses/{business_id}",
        headers=ONBOARDING_HEADERS,
    )
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is True
    assert status_response.json()["subscription_plan"] == "Pro"

    deactivate_response = await api_client.post(
        f"/internal/onboarding/businesses/{business_id}/deactivate",
        headers=ONBOARDING_HEADERS,
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False
    assert deactivate_response.json()["status"] == "pending"
    assert mock_redis.delete.await_count >= 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_returns_404_for_unknown_business(api_client: AsyncClient):
    response = await api_client.get(
        "/internal/onboarding/businesses/999999",
        headers=ONBOARDING_HEADERS,
    )

    assert response.status_code == 404
