# Закрытые developer endpoints

import os

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select

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

dev_router = APIRouter(prefix="/dev", tags=["Developer"])


"""----- Проверка developer key для доступа к dev endpoints -----"""
async def verify_dev_api_key(x_api_key: str = Header(None, alias="X-API-Key")) -> None:
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Developer key required")

    if x_api_key != config.developer_key:
        raise HTTPException(status_code=401, detail="Invalid developer key")


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
        from datetime import time
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
            bot_token=business_data.bot_token,
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
            "bot_token": new_business.bot_token,
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
        await session.commit()
        return {"detail": "Business deleted successfully"}
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