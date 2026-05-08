# Endpoint'ы для работы с бизнесом, сотрудниками, клиентами и записями

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header

from app.db.database import SessionDep
from app.models.service import ServiceModel
from app.models.business import BusinessModel
from app.schemas.appointment import AppointmentCreateSchema
from app.schemas.event import EventSchema
from app.services.service import Service
from app.repository.repository import Repository
from app.utils.free_slots import get_free_slots
from app.utils.logger import logger
from app.redis.limiter import rate_limiter
from app.utils.datetime_utils import now_utc


main_router = APIRouter(prefix="/api/v1", tags=["API"])


"""----- Проверка API Key -----"""
async def get_current_business(session: SessionDep, x_api_key: str = Header(...)) -> BusinessModel:
    repository = Repository(session)
    service = Service(session, repository)
    business = await service.get_business_by_api_key(x_api_key)
    if not business:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return business
    
    
"""----- Получение услуг для бизнеса -----"""
@main_router.get("/services/")
async def get_services(session: SessionDep, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        services = await service.get_business_services(business.id)
        return services
    except HTTPException:
        raise    
    

"""----- Получение мастеров для услуги -----"""
@main_router.get("/services/{service_id}/staffs/")
async def get_service_staffs(session: SessionDep, service_id: int, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        staffs = await service.get_service_staffs(business.id, service_id)
        return staffs
    except HTTPException:
        raise


"""----- Получение свободных дней для сотрудника на месяц -----"""
@main_router.get("/staffs/{staff_id}/free-days/", dependencies=[Depends(rate_limiter(30, 60, "free_days"))])
async def get_free_days(
    session: SessionDep,
    staff_id: int,
    service_id: int,
    business: BusinessModel = Depends(get_current_business)
):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        
        # Начинаем с сегодняшнего дня (naive UTC)
        today = now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
        free_days = []

        # Проверяем N дней вперед (из конфига)
        from app.config.config import config
        for i in range(config.free_days_lookahead):
            check_date = today + timedelta(days=i)
            
            # Получаем длительность услуги
            service_obj = await service.get_service_by_id(business.id, service_id)
            if not service_obj or service_obj["business_id"] != business.id:
                logger.warning(f"Service {service_id} not found for business {business.id}")
                raise HTTPException(status_code=404, detail="Service not found")
            
            duration_minutes = service_obj["duration_minutes"]
            logger.info(f"Service duration: {duration_minutes} minutes")


            busy_slots = await service.get_busy_slots(business.id, staff_id, check_date)
            free_slots = await get_free_slots(busy_slots, check_date, duration_minutes, business.working_time_start, business.working_time_end)
            
            # Если есть хотя бы один свободный слот, добавляем день
            if free_slots:
                free_days.append({
                    "date": check_date.strftime("%Y-%m-%d"),
                    "slots_count": len(free_slots)
                })
        
        return free_days
    except HTTPException:
        raise    
    

"""----- Получение свободных слотов для сотрудника в заданный день -----"""
@main_router.get("/staffs/{staff_id}/free-slots/", dependencies=[Depends(rate_limiter(30, 60, "free_slots"))])
async def get_available_slots(
    session: SessionDep,
    staff_id: int,
    date: str,
    service_id: int,
    business: BusinessModel = Depends(get_current_business)
):
    try:
        logger.info(f"free_slots called: staff_id={staff_id}, date={date}, service_id={service_id}, business_id={business.id}")
        
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        
        repository = Repository(session)
        service = Service(session, repository)
        
        # Получаем длительность услуги
        service_obj = await service.get_service_by_id(business.id, service_id)
        if not service_obj or service_obj["business_id"] != business.id:
            logger.warning(f"Service {service_id} not found for business {business.id}")
            raise HTTPException(status_code=404, detail="Service not found")
        
        duration_minutes = service_obj["duration_minutes"]
        logger.info(f"Service duration: {duration_minutes} minutes")
        
        busy_slots = await service.get_busy_slots(business.id, staff_id, date_obj)
        logger.info(f"Found {len(busy_slots)} busy slots")
        
        free_slots = await get_free_slots(busy_slots, date_obj, duration_minutes=duration_minutes, work_start=business.working_time_start, work_end=business.working_time_end)
        logger.info(f"Calculated {len(free_slots)} free slots")
        
        return free_slots
    except HTTPException:
        raise    
    except Exception as e:
        logger.error(f"Error in free_slots: {type(e).__name__} - {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    

"""----- Получение всех записей клиента -----"""
@main_router.get("/clients/{client_id}/appointments/", dependencies=[Depends(rate_limiter(30, 60, "get_client_appointments"))])
async def get_client_appointments(session: SessionDep, client_id: int, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        appointments = await service.get_client_appointments(business.id, client_id)
        return appointments
    except HTTPException:
        raise    


"""----- Получение ожидающих отправки событий -----"""
@main_router.get("/events/", response_model=List[EventSchema])
async def get_pending_events(session: SessionDep, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        events = await service.get_pending_events(business.id)
        return events
    except HTTPException:
        raise



"""----- Пометить событие как отправленное -----"""
@main_router.post("/events/{event_id}/mark-sent/")
async def mark_event_sent(session: SessionDep, event_id: int, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        event = await service.mark_event_sent(business.id, event_id)
        return {"message": "Event marked as sent", "event_id": event.id}
    except HTTPException:
        raise


"""----- Создание новой записи -----"""
@main_router.post("/appointments/create/", dependencies=[Depends(rate_limiter(10, 60, "create_appointment"))])
async def create_appointment(session: SessionDep, appointment_data: AppointmentCreateSchema, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        new_appointment = await service.create_appointment(business.id, appointment_data)
        return new_appointment
    except HTTPException:
        raise 


"""----- Получение или создание клиента -----"""
@main_router.post("/clients/get-or-create/", dependencies=[Depends(rate_limiter(20, 60, "get_or_create_client"))])
async def get_or_create_client(session: SessionDep, tg_id: int, client_name: str, phone: str = None, business: BusinessModel = Depends(get_current_business)) -> dict:
    try:
        repository = Repository(session)
        service = Service(session, repository)
        result = await service.get_or_create_client(business.id, tg_id, client_name, phone)
        return result
    except HTTPException:
        raise    


"""----- Отмена записи клиента -----"""
@main_router.post("/clients/{client_id}/appointments/{appointment_id}/", dependencies=[Depends(rate_limiter(10, 60, "cancel_appointment"))])
async def cancelled_appointment(session: SessionDep, client_id: int, appointment_id: int, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        await service.cancelled_appointment(business.id, client_id, appointment_id)
        return {"message": "Запись успешно отменена"}
    except HTTPException:
        raise