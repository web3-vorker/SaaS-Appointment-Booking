import asyncio
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointments import AppointmentModel
from app.models.clients import ClientModel
from app.models.service import ServiceModel
from app.models.staffs import StaffModel
from app.models.business import BusinessModel
from app.schemas.appointment import AppointmentCreateSchema
from app.repository.repository import Repository
from app.services.notification_service import NotificationService
from app.utils.logger import logger


class Service:
  def __init__(self, session: AsyncSession, repository: Repository, notification: NotificationService = None):
      self.session = session
      self.repository = repository
      self.notification = notification or NotificationService()


  # Получаем список сотрудников для бизнеса
  async def get_business_staffs(self, business_id: int) -> list[StaffModel]:
    try: 
      staffs = await self.repository.get_business_staffs(business_id)
      if not staffs:
        logger.info(f"No staffs found for business_id={business_id}")
      return staffs
    except Exception as e:
      logger.error(f"Error fetching business staffs: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Получаем занятые слоты для сотрудника в заданный день
  async def get_busy_slots(self, business_id: int, staff_id: int, date: datetime) -> list[AppointmentModel]:
    try:
      appointments = await self.repository.get_busy_slots(business_id, staff_id, date)

      if not appointments:
        logger.info(f"No appointments found for staff_id={staff_id} on {date.date()}")

      return appointments
    
    except Exception as e:
      logger.error(f"Error fetching busy slots: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Получаем все записи клиента
  async def get_client_appointments(self, business_id: int, client_id: int) -> list[AppointmentModel]:
    try: 
      appointments = await self.repository.get_client_appointments(business_id, client_id)

      if not appointments:
        logger.info(f"No appointments found for client_id={client_id} in business_id={business_id}")

      return appointments
    
    except Exception as e:
      logger.error(f"Error fetching client appointments: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # Получаем все услуги бизнеса
  async def get_business_services(self, business_id: int) -> list[ServiceModel]:
    try:
      services = await self.repository.get_business_services(business_id)

      if not services:
        logger.info(f"No services found for business_id={business_id}")

      return services
      
    except Exception as e:
      logger.error(f"Error fetching business services: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # Получаем услугу по id
  async def get_service_by_id(self, business_id: int, service_id: int) -> ServiceModel:
    try: 
      service = await self.repository.get_service_by_id(business_id, service_id)

      if not service:
        logger.info(f"No service found for business_id={business_id}")

      return service
      
    except Exception as e:
      logger.error(f"Error fetching business services: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Получаем ожидающие отправки события для бизнеса
  async def get_pending_events(self, business_id: int) -> list:
    try:
      events = await self.repository.get_pending_events(business_id)
      if not events:
        logger.info(f"No pending events found for business_id={business_id}")
      return events
    except Exception as e:
      logger.error(f"Error fetching pending events: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Помечаем событие как отправленное
  async def mark_event_sent(self, business_id: int, event_id: int):
    try:
      event = await self.repository.mark_event_sent(event_id, business_id)
      if not event:
        logger.warning(f"Event not found for event_id={event_id} business_id={business_id}")
        raise HTTPException(status_code=404, detail="Event not found")
      await self.session.commit()
      return event
    except HTTPException as http_exc:
      raise http_exc
    except Exception as e:
      logger.error(f"Error marking event sent: {e}")
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Создаем новую запись
  async def create_appointment(self, business_id: int, appointment_data: AppointmentCreateSchema) -> AppointmentModel:
    try:
      # Проверка принадлежности клиента и сотрудника к бизнесу
      client_and_staff_exists = await self.repository.client_and_staff_exists(business_id, appointment_data.client_id, appointment_data.staff_id)

      if not client_and_staff_exists:
        logger.warning(f"Client with id={appointment_data.client_id} or staff with id={appointment_data.staff_id} does not belong to business_id={business_id}")
        raise HTTPException(status_code=400, detail="Client or staff does not belong to this business")

      # Проверяем, нет ли пересечений с существующими записями для этого сотрудника
      has_overlap = await self.repository.has_overlapping_appointments(business_id, appointment_data)
      if has_overlap:
        logger.warning(f"Attempt to create overlapping appointment for staff_id={appointment_data.staff_id} in business_id={business_id}")
        raise HTTPException(status_code=400, detail="Appointment overlaps with existing booking")
          
      # Если все проверки пройдены, создаем запись
      new_appointment = AppointmentModel(
        business_id=business_id,
        client_id=appointment_data.client_id,
        staff_id=appointment_data.staff_id,
        service_id=appointment_data.service_id,
        start_time=appointment_data.start_time,
        end_time=appointment_data.end_time
      )

        # Отправляем уведомление владельцу
      business = await self.session.get(BusinessModel, business_id)
      if business and business.owner_tg_id:
        client = await self.session.get(ClientModel, appointment_data.client_id)
        staff = await self.session.get(StaffModel, appointment_data.staff_id)
        service = await self.session.get(ServiceModel, appointment_data.service_id)

      await self.repository.add_appointment(new_appointment)
      await self.session.commit()
      await self.session.refresh(new_appointment)
          
      logger.info(f"Created new appointment with id={new_appointment.id} for staff_id={appointment_data.staff_id} in business_id={business_id}")


      asyncio.create_task(self.notification.send_new_appointment_notification(
            owner_tg_id=business.owner_tg_id,
            appointment_details={
                'client_name': client.name if client else 'N/A',
                'service_name': service.name if service else 'N/A',
                'staff_name': staff.name if staff else 'N/A',
                'date': appointment_data.start_time.strftime('%d.%m.%Y'),
                'time': f"{appointment_data.start_time.strftime('%H:%M')} - {appointment_data.end_time.strftime('%H:%M')}",
                'appointment_id': new_appointment.id
            }
          )
        )
            
      logger.info(f"Created new appointment with id={new_appointment.id}")

      return new_appointment
    
    except HTTPException as http_exc:
      raise http_exc
    
    except Exception as e:
      logger.error(f"Error creating appointment: {e}")
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # Отмена запись
  async def cancelled_appointment(self, business_id: int, client_id: int, appointment_id: int) -> dict:
    try:
      logger.info(f"Attempting to delete appointment_id={appointment_id} for client_id={client_id} in business_id={business_id}")
      
      # Проверяем, что запись принадлежит этому бизнесу и клиенту
      appointment = await self.repository.get_appointment_by_id(business_id, client_id, appointment_id)

      if not appointment:
        logger.warning(f"Attempt to delete non-existent or unauthorized appointment with id={appointment_id} for client_id={client_id} in business_id={business_id}")
        raise HTTPException(status_code=404, detail="Appointment not found")

      logger.info(f"Found appointment: {appointment.id}, deleting...")
      response = await self.repository.cancelled_appointment(appointment)
      
      logger.info(f"Committing cancelled...")
      await self.session.commit()
      
      logger.info(f"Successfully deleted appointment with id={appointment_id} for client_id={client_id} in business_id={business_id}")

      business = await self.session.get(BusinessModel, business_id)
      if business and business.owner_tg_id:
        client = await self.session.get(ClientModel, client_id)
        service = appointment.service
        start_time = appointment.start_time
        end_time = appointment.end_time
     
      # Отпраляем уведомление владельцу бизнеса об отмене записи
      await self.notification.send_cancelled_appointment_notification(
        owner_tg_id=business.owner_tg_id,
        appointment_details={
          'client_name': client.name if client else 'N/A',
          'service_name': service.name if service else 'N/A',
          'date': start_time.strftime('%d.%m.%Y'),
          'time': f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
        }
      )

      return response

    except HTTPException as http_exc:
      raise http_exc
    
    except Exception as e:
      logger.error(f"Error deleting appointment: {e}", exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Получение или создание клиента
  async def get_or_create_client(self, business_id: int, tg_id: int, client_name: str) -> ClientModel:
    try:
      client = await self.repository.get_or_create_client(business_id, tg_id, client_name)
      return client
    except Exception as e:
      logger.error(f"Error getting or creating client: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Получаем бизнес по API Key
  async def get_business_by_api_key(self, api_key: str) -> BusinessModel | None:
    try:
      return await self.repository.get_business_by_api_key(api_key)
    except Exception as e:
      logger.error(f"Error getting business by API key: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")