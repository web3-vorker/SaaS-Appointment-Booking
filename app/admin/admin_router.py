# Admin endpoints

from fastapi import APIRouter, Depends, HTTPException

from app.db.database import SessionDep
from app.repository.repository import Repository
from app.routers.route import get_current_business
from app.schemas.appointment import AppointmentCreateSchema
from app.schemas.staff_service import StaffServiceCreateSchema
from app.services.service import Service
from app.schemas.staff import StaffCreateSchema
from app.schemas.service import ServiceCreateSchema

from app.models.business import BusinessModel


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


"""----- Получение истории записей бизнеса -----"""
@admin_router.get("/appointments/history/")
async def get_business_appointment_history(session: SessionDep, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        history = await service.get_business_appointment_history(business.id)
        return history
    except HTTPException:
        raise


"""----- Получение неотмеченных записей (прошедшие со статусом scheduled) -----"""
@admin_router.get("/appointments/unmarked/")
async def get_unmarked_appointments(session: SessionDep, business: BusinessModel = Depends(get_current_business)):
    try:
        repository = Repository(session)
        service = Service(session, repository)
        appointments = await service.get_unmarked_appointments(business.id)
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

        repository = Repository(session)
        service = Service(session, repository)
        result = await service.create_staff_admin(business.id, staff_data.name, staff_data.role)
        return result
    except HTTPException:
        raise


"""----- Удаление сотрудника через admin endpoint -----"""
@admin_router.delete("/staff/{staff_id}")
async def delete_staff(
    session: SessionDep,
    staff_id: int,
    business: BusinessModel = Depends(get_current_business)
) -> dict:
    try:
        repository = Repository(session)
        service = Service(session, repository)
        result = await service.delete_staff_admin(business.id, staff_id)
        return result
    except HTTPException:
        raise


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

        repository = Repository(session)
        service = Service(session, repository)
        result = await service.create_service_admin(
            business.id, 
            service_data.name, 
            service_data.price, 
            service_data.description, 
            service_data.duration_minutes
        )
        return result
    except HTTPException:
        raise


"""----- Удаление услуги через admin endpoint -----"""
@admin_router.delete("/service/{service_id}")
async def delete_service(
    session: SessionDep,
    service_id: int,
    business: BusinessModel = Depends(get_current_business)
) -> dict:
    try:
        repository = Repository(session)
        service = Service(session, repository)
        result = await service.delete_service_admin(business.id, service_id)
        return result
    except HTTPException:
        raise
    

"""----- Привязка услуги к сотруднику через admin endpoint -----"""
@admin_router.post("/staff-service/")
async def assign_service_to_staff(
    session: SessionDep,
    staff_service_data: StaffServiceCreateSchema
) -> dict:
    try:
        repository = Repository(session)
        service = Service(session, repository)
        result = await service.create_staff_service_admin(
            staff_service_data.business_id,
            staff_service_data.staff_id,
            staff_service_data.service_id
        )
        return result
    except HTTPException:
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
        result = await service.cancel_appointment_admin(business.id, appointment_id)
        return result
    except HTTPException:
        raise


"""----- Создание исключения в графике работы -----"""
@admin_router.post("/schedule-exception/")
async def create_schedule_exception(
    session: SessionDep,
    date: str,
    is_working: bool,
    custom_start: str = None,
    custom_end: str = None,
    business: BusinessModel = Depends(get_current_business)
) -> dict:
    try:
        repository = Repository(session)
        service = Service(session, repository)
        result = await service.create_schedule_exception_admin(business.id, date, is_working, custom_start, custom_end)
        return result
    except HTTPException:
        raise


"""----- Получение всех исключений в графике -----"""
@admin_router.get("/schedule-exceptions/")
async def get_schedule_exceptions(
    session: SessionDep,
    business: BusinessModel = Depends(get_current_business)
) -> list[dict]:
    try:
        repository = Repository(session)
        service = Service(session, repository)
        exceptions = await service.get_schedule_exceptions_admin(business.id)
        return exceptions
    except HTTPException:
        raise


"""----- Удаление исключения в графике -----"""
@admin_router.delete("/schedule-exception/{exception_id}")
async def delete_schedule_exception(
    session: SessionDep,
    exception_id: int,
    business: BusinessModel = Depends(get_current_business)
) -> dict:
    try:
        repository = Repository(session)
        service = Service(session, repository)
        result = await service.delete_schedule_exception_admin(business.id, exception_id)
        return result
    except HTTPException:
        raise
    

"""----- Изменение статуса записи через admin endpoint -----"""
@admin_router.post("/appointments/{appointment_id}/update-status/")
async def update_appointment_status(
    session: SessionDep, 
    appointment_id: int, 
    client_id: int,
    new_status: str, 
    business: BusinessModel = Depends(get_current_business)
) -> dict:
    try:
        repository = Repository(session)
        service = Service(session, repository)
        
        result = await service.update_appointment_status(business.id, client_id, appointment_id, new_status)
        return result
    except HTTPException:
        raise