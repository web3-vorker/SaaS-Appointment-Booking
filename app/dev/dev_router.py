# Закрытые developer endpoints

from datetime import time
import os

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy import select
from app.redis.cache import cache_delete_pattern, delete_cache
from app.redis.cache_keys import (
    pattern_all_slots,
    pattern_all_free_days,
    key_business_by_api_key,
    key_services,
)
from app.redis.limiter import get_redis_client

from app.repository.repository import Repository
from app.services.service import Service
from app.db.database import SessionDep
from app.config.config import config
from app.models.staff_services import StaffServiceModel
from app.schemas.business import BusinessCreateSchema
from app.schemas.staff import StaffCreateSchema
from app.schemas.service import ServiceCreateSchema
from app.schemas.appointment import AppointmentCreateSchema
from app.schemas.staff_service import StaffServiceCreateSchema

from app.models.business import BusinessModel
from app.models.staffs import StaffModel
from app.models.service import ServiceModel
from app.models.appointments import AppointmentModel
from app.models.clients import ClientModel
from app.models.schedule_exceptions import ScheduleExceptionModel

dev_router = APIRouter(prefix="/dev", tags=["Developer"])


"""----- Проверка developer key для доступа к dev endpoints -----"""
async def verify_dev_api_key(x_api_key: str = Header(None, alias="X-API-Key")) -> None:
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Developer key required")

    if x_api_key != config.developer_key:
        raise HTTPException(status_code=401, detail="Invalid developer key")


"""----- Получение всех подключенных бизнесов -----"""
@dev_router.get("/businesses/", dependencies=[Depends(verify_dev_api_key)])
async def get_all_businesses(session: SessionDep) -> list:
    result = await session.execute(select(BusinessModel))
    businesses = result.scalars().all()
    return [{"id": b.id, "name": b.name, "is_active": b.is_active} for b in businesses]


"""----- Создание бизнеса через dev endpoint -----"""
@dev_router.post("/business/", dependencies=[Depends(verify_dev_api_key)])
async def create_business(
    session: SessionDep,
    business_data: BusinessCreateSchema
) -> dict:
    try:
        # Проверяем, не существует ли уже бизнес с таким именем
        result = await session.execute(
            select(BusinessModel).where(BusinessModel.name == business_data.name)
        )
        existing_business = result.scalars().first()
        if existing_business:
            raise HTTPException(status_code=400, detail="Business with this name already exists")

        # Парсим время работы
        start_hour, start_minute = map(int, business_data.working_hours_start.split(':'))
        end_hour, end_minute = map(int, business_data.working_hours_end.split(':'))
        
        # Создаем time объекты (только время, без даты)
        working_time_start = time(hour=start_hour, minute=start_minute)
        working_time_end = time(hour=end_hour, minute=end_minute)
        
        # Валидация: конец должен быть после начала
        if working_time_end <= working_time_start:
            raise HTTPException(status_code=400, detail="End time must be after start time")

        import uuid
        api_key = str(uuid.uuid4())

        new_business = BusinessModel(
            name=business_data.name,
            working_time_start=working_time_start,
            working_time_end=working_time_end,
            owner_tg_id=business_data.owner_tg_id,
            api_key=api_key
        )
        session.add(new_business)
        await session.commit()
        await session.refresh(new_business)
        return {
            "id": new_business.id,
            "name": new_business.name,
            "working_time_start": new_business.working_time_start.strftime("%H:%M"),
            "working_time_end": new_business.working_time_end.strftime("%H:%M"),
            "owner_tg_id": new_business.owner_tg_id,
            "api_key": api_key
        }
    except Exception:
        raise


"----- Удаление бизнеса через dev endpoint -----"
@dev_router.delete("/business/{business_id}", dependencies=[Depends(verify_dev_api_key)])
async def delete_business(
    session: SessionDep,
    business_id: int
) -> dict:
    try:
        result = await session.execute(
            select(BusinessModel).where(BusinessModel.id == business_id)
        )
        business = result.scalars().first()
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")

        await session.delete(business)

        # Сбрасываем кэш для этого бизнеса
        try:
            await cache_delete_pattern(pattern_all_slots(business_id))
            await cache_delete_pattern(pattern_all_free_days(business_id))
            await delete_cache(key_services(business_id))
            if business.api_key:
                await delete_cache(key_business_by_api_key(business.api_key))
        except Exception:
            pass

        await session.commit()
        return {"detail": "Business deleted successfully"}
    except Exception:
        raise


"""----- Отключение бизнеса (деактивация) при истекании подписки через dev endpoint -----"""
@dev_router.patch("/business/{business_id}/deactivate", dependencies=[Depends(verify_dev_api_key)])
async def toggle_business_active(business_id: int, session: SessionDep) -> dict:
    try:
        result = await session.execute(
            select(BusinessModel).where(BusinessModel.id == business_id)
        )
        business = result.scalars().first()
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")

        # Переключаем статус
        business.is_active = not business.is_active
        await session.commit()

        status_text = "активирован" if business.is_active else "деактивирован"
        emoji = "✅" if business.is_active else "🔴"

        return {
            "message": f"{emoji} Бизнес {status_text}",
            "business_id": business.id,
            "is_active": business.is_active
        }
    except Exception:
        raise


"""----- Создание сотрудника через dev endpoint -----"""
@dev_router.post("/staff/", dependencies=[Depends(verify_dev_api_key)])
async def create_staff(
    session: SessionDep,
    staff_data: StaffCreateSchema
) -> dict:
    try:
        # Проверяем, существует ли бизнес
        result = await session.execute(
            select(BusinessModel).where(BusinessModel.id == staff_data.business_id)
        )
        business = result.scalars().first()
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")

        new_staff = StaffModel(
            name=staff_data.name,
            business_id=staff_data.business_id,
            role=staff_data.role
        )
        session.add(new_staff)
        await session.commit()
        await session.refresh(new_staff)
        return {
            "id": new_staff.id,
            "name": new_staff.name,
            "business_id": new_staff.business_id,
            "role": new_staff.role
        }
    except Exception:
        raise


"""----- Получение всех сотрудников для бизнеса через dev endpoint -----"""
@dev_router.get("/staffs/{business_id}", dependencies=[Depends(verify_dev_api_key)])
async def get_staffs(
    session: SessionDep,
    business_id: int
) -> list:
    try:
        result = await session.execute(
            select(StaffModel).where(StaffModel.business_id == business_id)
        )
        staffs = result.scalars().all()
        return [
            {
                "id": staff.id,
                "name": staff.name,
                "business_id": staff.business_id,
                "role": staff.role
            }
            for staff in staffs
        ]
    except Exception:
        raise


"""----- Удаление сотрудника через dev endpoint -----"""
@dev_router.delete("/staff/{staff_id}", dependencies=[Depends(verify_dev_api_key)])
async def delete_staff(
    session: SessionDep,
    business_id: int,
    staff_id: int
) -> dict:
    try:
        result = await session.execute(
            select(StaffModel)
            .where(StaffModel.id == staff_id)
            .where(StaffModel.business_id == business_id)
        )
        staff = result.scalars().first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")

        await session.delete(staff)
        await session.commit()
        return {"detail": "Staff deleted successfully"}
    except Exception:
        raise


"""----- Создание услуги через dev endpoint -----"""
@dev_router.post("/service/", dependencies=[Depends(verify_dev_api_key)])
async def create_service(
    session: SessionDep,
    service_data: ServiceCreateSchema
) -> dict:
    try:
        # Проверяем, существует ли бизнес
        result = await session.execute(
            select(BusinessModel).where(BusinessModel.id == service_data.business_id)
        )
        business = result.scalars().first()
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")

        new_service = ServiceModel(
            name=service_data.name,
            business_id=service_data.business_id,
            price=service_data.price,
            description=service_data.description,
            duration_minutes=service_data.duration_minutes
        )
        session.add(new_service)
        await session.commit()
        await session.refresh(new_service)
        return {
            "id": new_service.id,
            "name": new_service.name,
            "business_id": new_service.business_id,
            "price": new_service.price,
            "description": new_service.description,
            "duration_minutes": new_service.duration_minutes
        }
    except Exception:
        raise


"""----- Получение всех услуг для бизнеса через dev endpoint -----"""
@dev_router.get("/services/{business_id}", dependencies=[Depends(verify_dev_api_key)])
async def get_services(
    session: SessionDep,
    business_id: int
) -> list:
    try:
        result = await session.execute(
            select(ServiceModel).where(ServiceModel.business_id == business_id)
        )
        services = result.scalars().all()
        return [
            {
                "id": service.id,
                "name": service.name,
                "business_id": service.business_id,
                "price": service.price,
                "description": service.description,
                "duration_minutes": service.duration_minutes
            }
            for service in services
        ]
    except Exception:
        raise


"""----- Удаление услуги через dev endpoint -----"""
@dev_router.delete("/service/{service_id}", dependencies=[Depends(verify_dev_api_key)])
async def delete_service(
    session: SessionDep,
    business_id: int,
    service_id: int
) -> dict:
    try:
        result = await session.execute(
            select(ServiceModel)
            .where(ServiceModel.id == service_id)
            .where(ServiceModel.business_id == business_id)
        )
        service = result.scalars().first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        await session.delete(service)
        await session.commit()
        return {"detail": "Service deleted successfully"}
    except Exception:
        raise


"""----- Привязка услуги к сотруднику через dev endpoint -----"""
@dev_router.post("/staff-service/", dependencies=[Depends(verify_dev_api_key)])
async def assign_service_to_staff(
    session: SessionDep,
    staff_service_data: StaffServiceCreateSchema
) -> dict:
    try:
        # Проверяем, существует ли сотрудник и принадлежит ли он бизнесу
        result = await session.execute(
            select(StaffModel)
            .where(StaffModel.id == staff_service_data.staff_id)
            .where(StaffModel.business_id == staff_service_data.business_id)
        )
        staff = result.scalars().first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")

        # Проверяем, существует ли услуга и принадлежит ли она тому же бизнесу
        result = await session.execute(
            select(ServiceModel)
            .where(ServiceModel.id == staff_service_data.service_id)
            .where(ServiceModel.business_id == staff_service_data.business_id)
        )
        service = result.scalars().first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")


        # Создаем связь между сотрудником и услугой
        new_staff_service = StaffServiceModel(
            staff_id=staff_service_data.staff_id,
            service_id=staff_service_data.service_id,
            business_id=staff_service_data.business_id
        )
        session.add(new_staff_service)
        await session.commit()
        await session.refresh(new_staff_service)
        return {
            "id": new_staff_service.id,
            "staff_id": new_staff_service.staff_id,
            "service_id": new_staff_service.service_id,
            "business_id": new_staff_service.business_id
        }
    except Exception:
        raise


"""----- Получение всех связей мастеров и услуг для бизнеса -----"""
@dev_router.get("/staff-services/", dependencies=[Depends(verify_dev_api_key)])
async def get_staff_services(
    session: SessionDep,
    business_id: int
) -> list[dict]:
    try:
        result = await session.execute(
            select(StaffServiceModel)
            .where(StaffServiceModel.business_id == business_id)
        )
        staff_services = result.scalars().all()

        return [
            {
                "id": ss.id,
                "staff_id": ss.staff_id,
                "service_id": ss.service_id,
                "business_id": ss.business_id
            }
            for ss in staff_services
        ]
    except Exception:
        raise


"""----- Создание записи через dev endpoint -----"""
@dev_router.post("/appointment/", dependencies=[Depends(verify_dev_api_key)])
async def create_appointment_by_dev(
    session: SessionDep,
    appointment_data: AppointmentCreateSchema
) -> dict:
    try: 
        # Получаем сотрудника
        staff_result = await session.execute(
            select(StaffModel).where(StaffModel.id == appointment_data.staff_id)
        )
        staff = staff_result.scalars().first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")

        # Получаем услугу
        service_result = await session.execute(
            select(ServiceModel).where(ServiceModel.id == appointment_data.service_id)
        )
        service = service_result.scalars().first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        # Проверяем, что сотрудник и услуга принадлежат одному бизнесу
        if staff.business_id != service.business_id:
            raise HTTPException(status_code=400, detail="Staff and service belong to different businesses")

        business_id = staff.business_id

        # Проверяем, что клиент существует и принадлежит тому же бизнесу
        client_result = await session.execute(
            select(ClientModel).where(ClientModel.id == appointment_data.client_id)
        )
        client = client_result.scalars().first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        if client.business_id != business_id:
            raise HTTPException(status_code=400, detail="Client does not belong to the same business")

        # Используем существующий сервис для создания записи (с проверками на overlaps и т.д.)
        repository = Repository(session)
        service_service = Service(session, repository)

        appointment = await service_service.create_appointment(
            business_id=business_id,
            appointment_data=appointment_data
        )
        # appointment уже dict с нужными полями
        return appointment
    except Exception:
        raise



"""----- Удаление записи через dev endpoint -----"""
@dev_router.delete("/appointment/{appointment_id}", dependencies=[Depends(verify_dev_api_key)])
async def delete_appointment(
    session: SessionDep,
    business_id: int,
    appointment_id: int
) -> dict:
    try:
        result = await session.execute(
            select(AppointmentModel)
            .where(AppointmentModel.id == appointment_id)
            .where(AppointmentModel.business_id == business_id)
        )
        appointment = result.scalars().first()
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        await session.delete(appointment)
        await session.commit()
        return {"detail": "Appointment deleted successfully"}
    except Exception:
        raise


"""----- Обновление графика работы бизнеса -----"""
@dev_router.patch("/business/{business_id}/schedule/", dependencies=[Depends(verify_dev_api_key)])
async def update_business_schedule(
    session: SessionDep,
    business_id: int,
    break_start: str = None,
    break_end: str = None,
    weekend_days: list[int] = Query(None)
) -> dict:
    try:
        business = await session.get(BusinessModel, business_id)
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        if break_start:
            h, m = map(int, break_start.split(':'))
            business.break_start = time(h, m)
        
        if break_end:
            h, m = map(int, break_end.split(':'))
            business.break_end = time(h, m)
        
        if weekend_days is not None:
            business.weekend_days = weekend_days
        
        await session.commit()
        await session.refresh(business)
        
        return {
            "message": "Schedule updated",
            "break_start": business.break_start.strftime("%H:%M") if business.break_start else None,
            "break_end": business.break_end.strftime("%H:%M") if business.break_end else None,
            "weekend_days": business.weekend_days
        }
    except Exception:
        raise


"""----- Создание исключения в графике -----"""
@dev_router.post("/business/{business_id}/schedule-exception/", dependencies=[Depends(verify_dev_api_key)])
async def create_schedule_exception(
    session: SessionDep,
    business_id: int,
    date: str,  # "2026-05-09"
    is_working: bool,
    custom_start: str = None,  # "10:00"
    custom_end: str = None     # "16:00"
) -> dict:
    try:
        from datetime import datetime, time
        
        # Проверяем существование бизнеса
        business = await session.get(BusinessModel, business_id)
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        exc = ScheduleExceptionModel(
            business_id=business_id,
            date=datetime.strptime(date, "%Y-%m-%d").date(),
            is_working=is_working
        )
        
        if custom_start:
            h, m = map(int, custom_start.split(':'))
            exc.custom_start_time = time(h, m)
        
        if custom_end:
            h, m = map(int, custom_end.split(':'))
            exc.custom_end_time = time(h, m)
        
        session.add(exc)
        await session.commit()
        await session.refresh(exc)
        
        return {
            "message": "Exception created",
            "id": exc.id,
            "date": exc.date.strftime("%Y-%m-%d"),
            "is_working": exc.is_working,
            "custom_start_time": exc.custom_start_time.strftime("%H:%M") if exc.custom_start_time else None,
            "custom_end_time": exc.custom_end_time.strftime("%H:%M") if exc.custom_end_time else None
        }
    except Exception:
        raise


"""----- Получение всех исключений в графике для бизнеса -----"""
@dev_router.get("/business/{business_id}/schedule-exceptions/", dependencies=[Depends(verify_dev_api_key)])
async def get_schedule_exceptions(
    session: SessionDep,
    business_id: int
) -> list[dict]:
    try:
        result = await session.execute(
            select(ScheduleExceptionModel)
            .where(ScheduleExceptionModel.business_id == business_id)
            .order_by(ScheduleExceptionModel.date)
        )
        exceptions = result.scalars().all()
        
        return [
            {
                "id": exc.id,
                "date": exc.date.strftime("%Y-%m-%d"),
                "is_working": exc.is_working,
                "custom_start_time": exc.custom_start_time.strftime("%H:%M") if exc.custom_start_time else None,
                "custom_end_time": exc.custom_end_time.strftime("%H:%M") if exc.custom_end_time else None
            }
            for exc in exceptions
        ]
    except Exception:
        raise


"""----- Удаление исключения в графике -----"""
@dev_router.delete("/business/{business_id}/schedule-exception/{exception_id}", dependencies=[Depends(verify_dev_api_key)])
async def delete_schedule_exception(
    session: SessionDep,
    business_id: int,
    exception_id: int
) -> dict:
    try:
        result = await session.execute(
            select(ScheduleExceptionModel)
            .where(ScheduleExceptionModel.id == exception_id)
            .where(ScheduleExceptionModel.business_id == business_id)
        )
        exception = result.scalars().first()
        
        if not exception:
            raise HTTPException(status_code=404, detail="Exception not found")
        
        await session.delete(exception)
        await session.commit()
        
        return {"detail": "Exception deleted successfully"}
    except Exception:
        raise


"""----- Проверка работы системы -----"""
@dev_router.get("/health/", dependencies=[Depends(verify_dev_api_key)])
async def health_check(session: SessionDep) -> dict:
    result = {"status": "ok"}

    try:
        # Проверка PostgreSQL подключения
        await session.execute(select(1))
        result["database"] = "ok"

        # Проверка Redis подключения
        redis_client = await get_redis_client()
        await redis_client.ping()
        result["redis"] = "ok"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
    
    return result
