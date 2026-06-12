# Endpoint'С‹ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ Р±РёР·РЅРµСЃРѕРј, СЃРѕС‚СЂСѓРґРЅРёРєР°РјРё, РєР»РёРµРЅС‚Р°РјРё Рё Р·Р°РїРёСЃСЏРјРё

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header

from app.db.database import SessionDep
from app.models.business import BusinessModel
from app.redis.limiter import rate_limiter
from app.schemas.appointment import AppointmentCreateSchema
from app.schemas.event import EventSchema
from app.services.service import Service
from app.repository.repository import Repository
from app.utils.logger import logger
from app.redis.cache import get_cache, set_cache
from app.redis.cache_keys import key_business_by_api_key, TTL_BUSINESS


main_router = APIRouter(prefix="/api/v1", tags=["API"])


"""----- РџСЂРѕРІРµСЂРєР° API Key -----"""
async def get_current_business(session: SessionDep, x_api_key: str = Header(...)) -> BusinessModel:
    repository = Repository(session)
    service = Service(session, repository)

    # Проверяем есть ли бизнес в кэше Redis по API Key
    try:
        cached_business = await get_cache(key_business_by_api_key(x_api_key))
        if cached_business:
            logger.info(f"Cache hit for business by API Key, api_key: {x_api_key}")
            return BusinessModel(**cached_business)
    except Exception as e:
        # Если ошибка кэша, просто логируем и продолжаем
        logger.warning(f"Cache read error for business: {e}")
    
    business = await service.get_business_by_api_key(x_api_key)
    if not business:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    if not business.is_active:
        raise HTTPException(status_code=403, detail={"error": "subscription_inactive", "message": "РР·РІРёРЅРёС‚Рµ, Р±РѕС‚ РІСЂРµРјРµРЅРЅРѕ РЅРµ РґРѕСЃС‚СѓРїРµРЅ.", "business_id": business.id})
    
    # Сохраняем бизнес в кэш Redis
    try:
        await set_cache(key_business_by_api_key(x_api_key), business.dict(), TTL_BUSINESS)
    except Exception as e:
        # Если кэш недоступен, логируем но продолжаем (не критично)
        logger.warning(f"Cache write error for business: {e}")

    return business


"""----- Получение бизнеса по токену бота -----"""
async def get_current_business_by_bot_token(session: SessionDep, x_bot_token: str = Header(...)) -> BusinessModel:
    repository = Repository(session)
    service = Service(session, repository)
    business = await service.get_business_by_bot_token(x_bot_token)
    if not business:
        raise HTTPException(status_code=401, detail="Invalid Bot Token")
    if not business.is_active:
        raise HTTPException(status_code=403, detail={"error": "subscription_inactive", "message": "Sorry, your subscription is inactive.", "business_id": business.id})
    return business
    
    
"""----- РџРѕР»СѓС‡РµРЅРёРµ СѓСЃР»СѓРі РґР»СЏ Р±РёР·РЅРµСЃР° -----"""
@main_router.get("/services/", dependencies=[Depends(rate_limiter(5, 20, "get_services"))])
async def get_services(session: SessionDep, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        services = await service.get_business_services(business.id)
        return services
    except HTTPException:
        raise    
    

"""----- РџРѕР»СѓС‡РµРЅРёРµ РјР°СЃС‚РµСЂРѕРІ РґР»СЏ СѓСЃР»СѓРіРё -----"""
@main_router.get("/services/{service_id}/staffs/", dependencies=[Depends(rate_limiter(5, 20, "get_service_staffs"))])
async def get_service_staffs(session: SessionDep, service_id: int, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        staffs = await service.get_service_staffs(business.id, service_id)
        return staffs
    except HTTPException:
        raise


"""----- РџРѕР»СѓС‡РµРЅРёРµ СЃРІРѕР±РѕРґРЅС‹С… РґРЅРµР№ РґР»СЏ СЃРѕС‚СЂСѓРґРЅРёРєР° РЅР° РјРµСЃСЏС† -----"""
@main_router.get("/staffs/{staff_id}/free-days/", dependencies=[Depends(rate_limiter(5, 20, "free_days"))])
async def get_free_days(
    session: SessionDep,
    staff_id: int,
    service_id: int,
    business: BusinessModel = Depends(get_current_business)
):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        free_days = await service.get_free_days(business, staff_id, service_id)
        return free_days
    except HTTPException:
        raise    
    

"""----- РџРѕР»СѓС‡РµРЅРёРµ СЃРІРѕР±РѕРґРЅС‹С… СЃР»РѕС‚РѕРІ РґР»СЏ СЃРѕС‚СЂСѓРґРЅРёРєР° РІ Р·Р°РґР°РЅРЅС‹Р№ РґРµРЅСЊ -----"""
@main_router.get("/staffs/{staff_id}/free-slots/", dependencies=[Depends(rate_limiter(5, 20, "free_slots"))]) 
async def get_available_slots(
    session: SessionDep,
    staff_id: int,
    date: str,
    service_id: int,
    business: BusinessModel = Depends(get_current_business)
):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        free_slots = await service.get_available_slots(business, staff_id, service_id, date)
        
        return free_slots
    except HTTPException:
        raise    
    except Exception as e:
        logger.error("error_in_free_slots", staff_id=staff_id, date=date, service_id=service_id, error=str(e), error_type=type(e).__name__, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    

"""----- РџРѕР»СѓС‡РµРЅРёРµ РІСЃРµС… Р·Р°РїРёСЃРµР№ РєР»РёРµРЅС‚Р° -----"""
@main_router.get("/clients/{client_id}/appointments/", dependencies=[Depends(rate_limiter(5, 20, "get_client_appointments"))])
async def get_client_appointments(session: SessionDep, client_id: int, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        appointments = await service.get_client_appointments(business.id, client_id)
        return appointments
    except HTTPException:
        raise    


"""----- РџРѕР»СѓС‡РµРЅРёРµ РѕР¶РёРґР°СЋС‰РёС… РѕС‚РїСЂР°РІРєРё СЃРѕР±С‹С‚РёР№ -----"""
@main_router.get("/events/", response_model=List[EventSchema])
async def get_pending_events(session: SessionDep, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        events = await service.get_pending_events(business.id)
        return events
    except HTTPException:
        raise



"""----- РџРѕРјРµС‚РёС‚СЊ СЃРѕР±С‹С‚РёРµ РєР°Рє РѕС‚РїСЂР°РІР»РµРЅРЅРѕРµ -----"""
@main_router.post("/events/{event_id}/mark-sent/")
async def mark_event_sent(session: SessionDep, event_id: int, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        event = await service.mark_event_sent(business.id, event_id)
        return {"message": "Event marked as sent", "event_id": event.id}
    except HTTPException:
        raise


"""----- РЎРѕР·РґР°РЅРёРµ РЅРѕРІРѕР№ Р·Р°РїРёСЃРё -----"""
@main_router.post("/appointments/create/", dependencies=[Depends(rate_limiter(10, 60, "create_appointment"))]) 
async def create_appointment(session: SessionDep, appointment_data: AppointmentCreateSchema, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        new_appointment = await service.create_appointment(business.id, appointment_data)
        return new_appointment
    except HTTPException:
        raise 


"""----- РџРѕР»СѓС‡РµРЅРёРµ РёР»Рё СЃРѕР·РґР°РЅРёРµ РєР»РёРµРЅС‚Р° -----"""
@main_router.post("/clients/get-or-create/", dependencies=[Depends(rate_limiter(20, 60, "get_or_create_client"))])
async def get_or_create_client(session: SessionDep, tg_id: int, client_name: str, phone: str = None, business: BusinessModel = Depends(get_current_business)) -> dict:
    try:
        repository = Repository(session)
        service = Service(session, repository)
        result = await service.get_or_create_client(business.id, tg_id, client_name, phone)
        return result
    except HTTPException:
        raise    


"""----- РћС‚РјРµРЅР° Р·Р°РїРёСЃРё РєР»РёРµРЅС‚Р° -----"""
@main_router.post("/clients/{client_id}/appointments/{appointment_id}/", dependencies=[Depends(rate_limiter(10, 60, "cancel_appointment"))])
async def cancelled_appointment(session: SessionDep, client_id: int, appointment_id: int, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        await service.cancelled_appointment(business.id, client_id, appointment_id)
        return {"message": "Р—Р°РїРёСЃСЊ СѓСЃРїРµС€РЅРѕ РѕС‚РјРµРЅРµРЅР°"}
    except HTTPException:
        raise

