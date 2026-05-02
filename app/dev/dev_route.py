# Закрытые developer endpoints

from fastapi import APIRouter, Depends, HTTPException, Header
from dotenv import load_dotenv
from sqlalchemy import select
import os

from app.db.database import SessionDep
from app.schemas.business import BusinessCreateSchema
from app.schemas.staff import StaffCreateSchema
from app.schemas.service import ServiceCreateSchema
from app.schemas.appointment import AppointmentCreateSchema

from app.models.business import BusinessModel
from app.models.staffs import StaffModel
from app.models.service import ServiceModel
from app.models.appointments import AppointmentModel
from app.models.clients import ClientModel

load_dotenv()

dev_router = APIRouter()


async def verify_dev_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """
    Проверяет, что предоставленный ключ совпадает с ключом из .env
    """
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Developer key required")
    
    DEV_API_KEY = os.getenv("DEVELOPER_KEY")
    if x_api_key != DEV_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid developer key")


@dev_router.post("/business/", dependencies=[Depends(verify_dev_api_key)])
async def create_business(
    session: SessionDep,
    business_data: BusinessCreateSchema
):
    """
    Создает новый бизнес.
    Доступно только с правильным DEVELOPER_KEY.
    """
    try:
        # Проверяем, не существует ли уже бизнес с таким именем
        result = await session.execute(
            select(BusinessModel).where(BusinessModel.name == business_data.name)
        )
        existing_business = result.scalars().first()
        if existing_business:
            raise HTTPException(status_code=400, detail="Business with this name already exists")

        new_business = BusinessModel(
            name=business_data.name,
            owner_tg_id=business_data.owner_tg_id,
            # Генерируем случайный API ключ для нового бизнеса
            api_key=os.urandom(16).hex()
        )
        session.add(new_business)
        await session.commit()
        await session.refresh(new_business)
        return {
            "id": new_business.id,
            "name": new_business.name,
            "owner_tg_id": new_business.owner_tg_id,
            "api_key": new_business.api_key
        }
    except Exception:
        raise


@dev_router.post("/staff/", dependencies=[Depends(verify_dev_api_key)])
async def create_staff(
    session: SessionDep,
    staff_data: StaffCreateSchema
):
    try:
        """
        Добавляет нового сотрудника к бизнесу.
        Доступно только с правильным DEVELOPER_KEY.
        """
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


@dev_router.post("/service/", dependencies=[Depends(verify_dev_api_key)])
async def create_service(
    session: SessionDep,
    service_data: ServiceCreateSchema
):
    try:
        """
        Добавляет новую услугу к бизнесу.
        Доступно только с правильным DEVELOPER_KEY.
        """
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


@dev_router.post("/appointment/", dependencies=[Depends(verify_dev_api_key)])
async def create_appointment_by_dev(
    session: SessionDep,
    appointment_data: AppointmentCreateSchema
):
    try: 
        """
        Создает новую запись (для разработки).
        Доступно только с правильным DEVELOPER_KEY.
        Выводит бизнес из staff_id и service_id (должны принадлежать одному бизнесу).
        Также проверяет, что клиент принадлежит тому же бизнесу.
        """
        from app.repository.repository import Repository
        from app.services.service import Service

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
        # Возвращаем запись в виде dict (как делает основной endpoint)
        return {
            "id": appointment.id,
            "business_id": appointment.business_id,
            "client_id": appointment.client_id,
            "staff_id": appointment.staff_id,
            "service_id": appointment.service_id,
            "start_time": appointment.start_time.isoformat() if appointment.start_time else None,
            "end_time": appointment.end_time.isoformat() if appointment.end_time else None,
            "status": appointment.status
        }
    except Exception:
        raise