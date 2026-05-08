# Admin endpoints

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import SessionDep
from app.models.appointments import AppointmentModel
from app.models.staff_services import StaffServiceModel
from app.repository.repository import Repository
from app.routers.route import get_current_business
from app.schemas.appointment import AppointmentCreateSchema
from app.schemas.staff_service import StaffServiceCreateSchema
from app.services.service import Service
from app.schemas.staff import StaffCreateSchema
from app.schemas.service import ServiceCreateSchema

from app.models.business import BusinessModel
from app.models.staffs import StaffModel
from app.models.service import ServiceModel


admin_router = APIRouter(prefix="/admin", tags=["Admin"])


"""----- Получение услуг для бизнеса -----"""
@admin_router.get("/services/")
async def get_services(session: SessionDep, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        services = await service.get_business_services(business.id)
        return services
    except HTTPException:
        raise   
    

"""----- Получение сотрудников бизнеса -----"""
@admin_router.get("/staffs/")
async def get_staffs(session: SessionDep, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        staffs = await service.get_business_staffs(business.id)
        return staffs
    except HTTPException:
        raise    


"""----- Получение всех записей бизнеса -----"""
@admin_router.get("/appointments/")
async def get_business_appointments(session: SessionDep, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        appointments = await service.get_business_appointments(business.id)
        return appointments
    except HTTPException:
        raise    
    

"""----- Создание сотрудника через admin endpoint -----"""
@admin_router.post("/staff/")
async def create_staff(
    session: SessionDep,
    staff_data: StaffCreateSchema,
    business: BusinessModel = Depends(get_current_business)
) -> dict:
    try:
        # Проверяем, что сотрудник создается для бизнеса владельца
        if staff_data.business_id != business.id:
            raise HTTPException(status_code=403, detail="You can only create staff for your own business")

        new_staff = StaffModel(
            name=staff_data.name,
            business_id=business.id,
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
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")


"""----- Удаление сотрудника через admin endpoint -----"""
@admin_router.delete("/staff/{staff_id}")
async def delete_staff(
    session: SessionDep,
    staff_id: int,
    business: BusinessModel = Depends(get_current_business)
) -> dict:
    try:
        result = await session.execute(
            select(StaffModel)
            .where(StaffModel.id == staff_id)
            .where(StaffModel.business_id == business.id)
        )
        staff = result.scalars().first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")

        await session.delete(staff)
        await session.commit()
        return {"detail": "Staff deleted successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")


"""----- Создание услуги через admin endpoint -----"""
@admin_router.post("/service/")
async def create_service(
    session: SessionDep,
    service_data: ServiceCreateSchema,
    business: BusinessModel = Depends(get_current_business)
) -> dict:
    try:
        # Проверяем, что услуга создается для бизнеса владельца
        if service_data.business_id != business.id:
            raise HTTPException(status_code=403, detail="You can only create services for your own business")

        new_service = ServiceModel(
            name=service_data.name,
            business_id=business.id,
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
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")


"""----- Удаление услуги через admin endpoint -----"""
@admin_router.delete("/service/{service_id}")
async def delete_service(
    session: SessionDep,
    service_id: int,
    business: BusinessModel = Depends(get_current_business)
) -> dict:
    try:
        result = await session.execute(
            select(ServiceModel)
            .where(ServiceModel.id == service_id)
            .where(ServiceModel.business_id == business.id)
        )
        service = result.scalars().first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        await session.delete(service)
        await session.commit()
        return {"detail": "Service deleted successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

"""----- Привязка услуги к сотруднику через dev endpoint -----"""
@admin_router.post("/staff-service/")
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


"""----- Создание записи через admin endpoint -----"""
@admin_router.post("/create-appointment/")
async def create_appointment(
    session: SessionDep,
    appointment_data: AppointmentCreateSchema,
    business: BusinessModel = Depends(get_current_business)
) -> dict:
    try:
        repository = Repository(session)
        service = Service(session, repository)
        new_appointment = await service.create_appointment(business.id, appointment_data)
        return new_appointment
    except HTTPException:
        raise 
    

"""----- Отмена записи через admin endpoint -----"""
@admin_router.post("/appointments/{appointment_id}/cancel/")
async def cancel_appointment_by_id(
    session: SessionDep, 
    appointment_id: int, 
    business: BusinessModel = Depends(get_current_business)
):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        
        # Получаем запись чтобы узнать client_id
        from sqlalchemy.orm import selectinload
        result = await session.execute(
            select(AppointmentModel)
            .options(selectinload(AppointmentModel.client))
            .where(AppointmentModel.id == appointment_id)
            .where(AppointmentModel.business_id == business.id)
        )
        appointment = result.scalars().first()
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        # Передаем cancelled_by_admin=True
        await service.cancelled_appointment(business.id, appointment.client_id, appointment_id, cancelled_by_admin=True)
        return {"message": "Запись успешно отменена"}
    except HTTPException:
        raise