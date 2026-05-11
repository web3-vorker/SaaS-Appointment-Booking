from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointments import AppointmentModel
from app.models.clients import ClientModel
from app.models.service import ServiceModel
from app.models.staffs import StaffModel
from app.models.business import BusinessModel
from app.schemas.appointment import AppointmentCreateSchema
from app.repository.repository import Repository
from app.utils.datetime_utils import now_utc
from app.utils.free_slots import get_free_slots
from app.utils.logger import logger


class Service:
  def __init__(self, session: AsyncSession, repository: Repository):
      self.session = session
      self.repository = repository


  # Получаем список сотрудников для бизнеса
  async def get_business_staffs(self, business_id: int) -> list[dict]:
    try: 
      staffs = await self.repository.get_business_staffs(business_id)
      if not staffs:
        return []
      
      # Сериализуем сотрудников (оптимизировано через list comprehension)
      return [
        {
          "id": staff.id,
          "name": staff.name,
          "role": staff.role,
          "business_id": staff.business_id
        }
        for staff in staffs
      ]
    except Exception as e:
      logger.error(f"Error fetching business staffs: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # Получаем мастеров для услуги
  async def get_service_staffs(self, business_id: int, service_id: int) -> list[dict]:
    try:
      staffs = await self.repository.get_service_staffs(business_id, service_id)
      if not staffs:
        return []
      
      # Сериализуем сотрудников
      result = []
      for staff in staffs:
        result.append({
          "id": staff.id,
          "name": staff.name,
          "role": staff.role,
          "business_id": staff.business_id
        })
      
      return result
    except Exception as e:
      logger.error(f"Error fetching service staffs: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Получаем занятые слоты для сотрудника в заданный день
  async def get_busy_slots(self, business_id: int, staff_id: int, date: datetime) -> list[AppointmentModel]:
    try:
      appointments = await self.repository.get_busy_slots(business_id, staff_id, date)
      return appointments
    
    except Exception as e:
      logger.error(f"Error fetching busy slots: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # Получаем свободные слоты для сотрудника в заданный день
  async def get_available_slots(self, business: BusinessModel, staff_id: int, service_id: int, date: str) -> list[dict]:
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        
        # Получаем длительность услуги
        service_obj = await self.get_service_by_id(business.id, service_id)
        if not service_obj or service_obj["business_id"] != business.id:
            logger.warning(f"Service {service_id} not found for business {business.id}")
            raise HTTPException(status_code=404, detail="Service not found")
        
        duration_minutes = service_obj["duration_minutes"]
        
        # Проверяем исключения в графике для этой даты
        schedule_exception = await self.repository.get_schedule_exception(business.id, date_obj)
        
        # Если день не рабочий - возвращаем пустой список
        if schedule_exception and not schedule_exception.is_working:
            return []
        
        busy_slots = await self.get_busy_slots(business.id, staff_id, date_obj)
        
        free_slots = await get_free_slots(
            busy_slots, 
            date_obj, 
            duration_minutes=duration_minutes, 
            work_start=business.working_time_start, 
            work_end=business.working_time_end,
            business=business,
            schedule_exception=schedule_exception
        )

        return free_slots
    except Exception as e:
        logger.error(f"Error in get_available_slots: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

  # Получаем свободные дни для сотрудника на месяц
  async def get_free_days(self, business: BusinessModel, staff_id: int, service_id: int) -> list[dict]:
        # Начинаем с сегодняшнего дня (naive UTC)
        today = now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
        free_days = []

        # Получаем длительность услуги один раз
        service_obj = await self.get_service_by_id(business.id, service_id)
        if not service_obj or service_obj["business_id"] != business.id:
            logger.warning(f"Service {service_id} not found for business {business.id}")
            raise HTTPException(status_code=404, detail="Service not found")
        
        duration_minutes = service_obj["duration_minutes"]
        
        # Получаем выходные дни бизнеса
        weekend_days = business.weekend_days or []
        
        # Проверяем N дней вперед (из конфига)
        from app.config.config import config
        end_date = today + timedelta(days=config.free_days_lookahead)
        
        # Получаем все исключения в графике для этого диапазона
        schedule_exceptions = await self.repository.get_schedule_exceptions_range(business.id, today, end_date)
        exceptions_dict = {exc.date: exc for exc in schedule_exceptions}
        
        for i in range(config.free_days_lookahead):
            check_date = today + timedelta(days=i)
            
            # Проверяем день недели (0=Пн, 6=Вс)
            weekday = check_date.weekday()
            
            # Проверяем исключения в графике
            exception = exceptions_dict.get(check_date.date())
            
            # Если есть исключение и день не рабочий - пропускаем
            if exception and not exception.is_working:
                continue
            
            # Если нет исключения, но день в списке выходных - пропускаем
            if not exception and weekday in weekend_days:
                continue
            
            # Получаем занятые слоты
            busy_slots = await self.get_busy_slots(business.id, staff_id, check_date)
            
            # Генерируем свободные слоты с учетом исключений
            free_slots = await get_free_slots(
                busy_slots, 
                check_date, 
                duration_minutes, 
                business.working_time_start, 
                business.working_time_end,
                business=business,
                schedule_exception=exception
            )
            
            # Если есть хотя бы один свободный слот, добавляем день
            if free_slots:
                free_days.append({
                    "date": check_date.strftime("%Y-%m-%d"),
                    "slots_count": len(free_slots)
                })

        return free_days


  # Получаем все записи клиента
  async def get_client_appointments(self, business_id: int, client_id: int) -> list[dict]:
    try: 
      appointments = await self.repository.get_client_appointments(business_id, client_id)

      if not appointments:
        return []

      # Сериализуем записи
      result = []
      for apt in appointments:
        result.append({
          "id": apt.id,
          "client_id": apt.client_id,
          "client_name": apt.client_name,
          "client_tg_id": apt.client.tg_id if apt.client else None,
          "client_phone": apt.client.phone if apt.client else None,
          "staff_id": apt.staff_id,
          "service_id": apt.service_id,
          "start_time": apt.start_time.isoformat(),
          "end_time": apt.end_time.isoformat(),
          "status": apt.status,
          "staff": {
            "id": apt.staff.id,
            "name": apt.staff.name,
            "role": apt.staff.role
          } if apt.staff else None,
          "service": {
            "id": apt.service.id,
            "name": apt.service.name,
            "price": apt.service.price,
            "duration_minutes": apt.service.duration_minutes
          } if apt.service else None
        })
      
      return result
    
    except Exception as e:
      logger.error(f"Error fetching client appointments: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # Получаем все услуги бизнеса
  async def get_business_services(self, business_id: int) -> list[dict]:
    try:
      services = await self.repository.get_business_services(business_id)

      if not services:
        return []

      # Сериализуем услуги (оптимизировано через list comprehension)
      return [
        {
          "id": service.id,
          "name": service.name,
          "price": service.price,
          "description": service.description,
          "duration_minutes": service.duration_minutes,
          "business_id": service.business_id
        }
        for service in services
      ]
      
    except Exception as e:
      logger.error(f"Error fetching business services: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # Получаем все записи бизнеса
  async def get_business_appointments(self, business_id: int) -> list[dict]:
    try:
      appointments = await self.repository.get_business_appointments(business_id)

      if not appointments:
        return []

      # Сериализуем записи (оптимизировано через list comprehension)
      return [
        {
          "id": apt.id,
          "client_id": apt.client_id,
          "client_name": apt.client_name,
          "client_tg_id": apt.client.tg_id if apt.client else None,
          "client_phone": apt.client.phone if apt.client else None,
          "staff_id": apt.staff_id,
          "service_id": apt.service_id,
          "start_time": apt.start_time.isoformat(),
          "end_time": apt.end_time.isoformat(),
          "status": apt.status,
          "staff": {
            "id": apt.staff.id,
            "name": apt.staff.name,
            "role": apt.staff.role
          } if apt.staff else None,
          "service": {
            "id": apt.service.id,
            "name": apt.service.name,
            "price": apt.service.price,
            "duration_minutes": apt.service.duration_minutes
          } if apt.service else None
        }
        for apt in appointments
      ]
    except Exception as e:
      logger.error(f"Error fetching business appointments: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

    # Получение истории записей бизнеса (для админки)
  async def get_business_appointment_history(self, business_id: int) -> list[dict]:
    try:
      appointments = await self.repository.get_business_appointment_history(business_id)

      if not appointments:
        return []

      # Сериализуем записи (оптимизировано через list comprehension)
      return [
        {
          "id": apt.id,
          "client_id": apt.client_id,
          "client_name": apt.client_name,
          "client_tg_id": apt.client.tg_id if apt.client else None,
          "client_phone": apt.client.phone if apt.client else None,
          "staff_id": apt.staff_id,
          "service_id": apt.service_id,
          "start_time": apt.start_time.isoformat(),
          "end_time": apt.end_time.isoformat(),
          "status": apt.status,
          "staff": {
            "id": apt.staff.id,
            "name": apt.staff.name,
            "role": apt.staff.role
          } if apt.staff else None,
          "service": {
            "id": apt.service.id,
            "name": apt.service.name,
            "price": apt.service.price,
            "duration_minutes": apt.service.duration_minutes
          } if apt.service else None
        }
        for apt in appointments
      ]
    except Exception as e:
      logger.error(f"Error fetching business appointment history: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # Получаем услугу по id
  async def get_service_by_id(self, business_id: int, service_id: int) -> dict:
    try: 
      service = await self.repository.get_service_by_id(business_id, service_id)

      if not service:
        return None

      # Сериализуем услугу
      return {
        "id": service.id,
        "business_id": service.business_id,
        "name": service.name,
        "price": service.price,
        "description": service.description,
        "duration_minutes": service.duration_minutes
      }
      
    except Exception as e:
      logger.error(f"Error fetching business services: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Получаем ожидающие отправки события для бизнеса
  async def get_pending_events(self, business_id: int) -> list[dict]:
    try:
      events = await self.repository.get_pending_events(business_id)
      if not events:
        return []
      
      # Сериализуем события
      result = []
      for event in events:
        result.append({
          "id": event.id,
          "type": event.type,
          "business_id": event.business_id,
          "appointment_id": event.appointment_id,
          "payload": event.payload,
          "is_sent": event.is_sent,
          "created_at": event.created_at.isoformat() if event.created_at else None
        })
      
      return result
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
  async def create_appointment(self, business_id: int, appointment_data: AppointmentCreateSchema) -> dict:
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
        client_name=appointment_data.client_name,
        staff_id=appointment_data.staff_id,
        service_id=appointment_data.service_id,
        start_time=appointment_data.start_time,
        end_time=appointment_data.end_time
      )

      await self.repository.add_appointment(new_appointment)
      
      # Flush для получения ID без commit
      await self.session.flush()
      
      # Получаем данные для события
      business = await self.session.get(BusinessModel, business_id)
      client = await self.session.get(ClientModel, appointment_data.client_id)
      staff = await self.session.get(StaffModel, appointment_data.staff_id)
      service = await self.session.get(ServiceModel, appointment_data.service_id)

      # Создаем событие если нужно (только если клиент не владелец)
      if business and business.owner_tg_id and client and client.tg_id != business.owner_tg_id:
        event_payload = {
            'owner_tg_id': business.owner_tg_id,
            'client_name': appointment_data.client_name,
            'service_name': service.name if service else 'N/A',
            'staff_name': staff.name if staff else 'N/A',
            'date': appointment_data.start_time.strftime('%d.%m.%Y'),
            'time': f"{appointment_data.start_time.strftime('%H:%M')} - {appointment_data.end_time.strftime('%H:%M')}",
            'appointment_id': new_appointment.id
        }
        
        await self.repository.create_event(
            event_type='new_appointment',
            business_id=business_id,
            appointment_id=new_appointment.id,
            payload=event_payload
        )
        
      # Один commit для всей транзакции
      await self.session.commit()
      await self.session.refresh(new_appointment)
          
      logger.info(f"Created appointment id={new_appointment.id} for business_id={business_id}")

      # Возвращаем данные с вложенными объектами для бота
      return {
          'id': new_appointment.id,
          'start_time': new_appointment.start_time.isoformat(),
          'end_time': new_appointment.end_time.isoformat(),
          'service': {
              'name': service.name if service else 'N/A',
              'price': service.price if service else 0
          },
          'staff': {
              'name': staff.name if staff else 'N/A'
          }
      }
    
    except HTTPException as http_exc:
      raise http_exc
    
    except Exception as e:
      logger.error(f"Error creating appointment: {e}")
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # Отмена запись
  async def cancelled_appointment(self, business_id: int, client_id: int, appointment_id: int, cancelled_by_admin: bool = False) -> dict:
    try:
      # Проверяем, что запись принадлежит этому бизнесу и клиенту
      appointment = await self.repository.get_appointment_by_id(business_id, client_id, appointment_id)

      if not appointment:
        logger.warning(f"Attempt to delete non-existent appointment id={appointment_id} for client_id={client_id} in business_id={business_id}")
        raise HTTPException(status_code=404, detail="Appointment not found")

      # Сохраняем данные ДО удаления (связи уже загружены через selectinload в repository)
      business = await self.session.get(BusinessModel, business_id)
      client = await self.session.get(ClientModel, client_id)
      
      # Извлекаем данные из уже загруженных связей
      staff_name = appointment.staff.name if appointment.staff else 'N/A'
      service_name = appointment.service.name if appointment.service else 'N/A'
      client_name = appointment.client_name
      start_time = appointment.start_time
      end_time = appointment.end_time

      response = await self.repository.cancelled_appointment(appointment)
      
      # Логика создания событий в зависимости от того, кто отменяет
      if business and business.owner_tg_id and client:
        # Если клиент = владелец, события не создаем
        if client.tg_id == business.owner_tg_id:
          pass  # Skip event creation
        else:
          # Если отменяет админ - уведомляем клиента
          if cancelled_by_admin:
            event_payload = {
              'client_tg_id': client.tg_id,
              'client_name': client_name,
              'service_name': service_name,
              'staff_name': staff_name,
              'date': start_time.strftime('%d.%m.%Y'),
              'time': f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
            }
            
            await self.repository.create_event(
              event_type='cancelled_appointment_by_admin',
              business_id=business_id,
              appointment_id=appointment_id,
              payload=event_payload
            )
          # Если отменяет клиент - уведомляем владельца
          else:
            event_payload = {
              'owner_tg_id': business.owner_tg_id,
              'client_name': client_name,
              'service_name': service_name,
              'staff_name': staff_name,
              'date': start_time.strftime('%d.%m.%Y'),
              'time': f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
            }
            
            await self.repository.create_event(
              event_type='cancelled_appointment_by_client',
              business_id=business_id,
              appointment_id=appointment_id,
              payload=event_payload
            )
            
            logger.info(f"Created cancelled_appointment_by_client event for appointment_id={appointment_id}")
      
      await self.session.commit()

      return response

    except HTTPException as http_exc:
      raise http_exc
    
    except Exception as e:
      logger.error(f"Error deleting appointment: {e}", exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")
    

  # Изменение статуса записи для админки
  async def update_appointment_status(self, business_id: int, client_id: int, appointment_id: int, new_status: str) -> dict:
    try:
      # Проверяем, что запись принадлежит этому бизнесу и клиенту
      appointment = await self.repository.get_appointment_by_id(business_id, client_id, appointment_id)
      if not appointment:
        logger.warning(f"Attempt to update non-existent or unauthorized appointment with id={appointment_id} for client_id={client_id} in business_id={business_id}")
        raise HTTPException(status_code=404, detail="Appointment not found")
      
      # Обновляем статус
      result = await self.repository.update_appointment_status(appointment, new_status)

      # Один commit для всей транзакции
      await self.session.commit()
      await self.session.refresh(appointment)

      return result

    except HTTPException as http_exc:
      raise http_exc
    except Exception as e:
      logger.error(f"Error updating appointment status: {e}", exc_info=True)
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")     


  # Получение или создание клиента
  async def get_or_create_client(self, business_id: int, tg_id: int, client_name: str, phone: str = None) -> dict:
    try:
      result = await self.repository.get_or_create_client(business_id, tg_id, client_name, phone)
      
      # Repository уже возвращает словарь с client и is_owner
      client = result["client"]
      is_owner = result["is_owner"]
      updated = result.get("updated", False)
      
      # ВАЖНО: Всегда коммитим, чтобы клиент был доступен для других запросов
      await self.session.commit()
      await self.session.refresh(client)
      
      return {
          "client": {
              "id": client.id,
              "name": client.name,
              "tg_id": client.tg_id,
              "phone": client.phone,
              "business_id": client.business_id,
              "created_at": client.created_at.isoformat() if client.created_at else None
          },
          "is_owner": is_owner
      }
    except HTTPException as http_exc:
      raise http_exc
    except Exception as e:
      logger.error(f"Error getting or creating client: {e}")
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Получаем бизнес по API Key
  async def get_business_by_api_key(self, api_key: str) -> BusinessModel | None:
    try:
      return await self.repository.get_business_by_api_key(api_key)
    except Exception as e:
      logger.error(f"Error getting business by API key: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Получаем неотмеченные записи
  async def get_unmarked_appointments(self, business_id: int) -> list[dict]:
    try:
      appointments = await self.repository.get_unmarked_appointments(business_id)
      
      if not appointments:
        return []

      # Сериализуем записи (оптимизировано через list comprehension)
      return [
        {
          "id": apt.id,
          "client_id": apt.client_id,
          "client_name": apt.client_name,
          "client_tg_id": apt.client.tg_id if apt.client else None,
          "client_phone": apt.client.phone if apt.client else None,
          "staff_id": apt.staff_id,
          "service_id": apt.service_id,
          "start_time": apt.start_time.isoformat(),
          "end_time": apt.end_time.isoformat(),
          "status": apt.status,
          "staff": {
            "id": apt.staff.id,
            "name": apt.staff.name,
            "role": apt.staff.role
          } if apt.staff else None,
          "service": {
            "id": apt.service.id,
            "name": apt.service.name,
            "price": apt.service.price,
            "duration_minutes": apt.service.duration_minutes
          } if apt.service else None
        }
        for apt in appointments
      ]
    except Exception as e:
      logger.error(f"Error fetching unmarked appointments: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Создаем сотрудника (для админки)
  async def create_staff_admin(self, business_id: int, name: str, role: str) -> dict:
    try:
      new_staff = await self.repository.create_staff(business_id, name, role)
      await self.session.commit()
      await self.session.refresh(new_staff)
      
      return {
        "id": new_staff.id,
        "name": new_staff.name,
        "business_id": new_staff.business_id,
        "role": new_staff.role
      }
    except Exception as e:
      logger.error(f"Error creating staff: {e}")
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Удаляем сотрудника (для админки)
  async def delete_staff_admin(self, business_id: int, staff_id: int) -> dict:
    try:
      staff = await self.repository.delete_staff(business_id, staff_id)
      if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
      
      await self.session.commit()
      return {"detail": "Staff deleted successfully"}
    except HTTPException:
      raise
    except Exception as e:
      logger.error(f"Error deleting staff: {e}")
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Создаем услугу (для админки)
  async def create_service_admin(self, business_id: int, name: str, price: int, description: str, duration_minutes: int) -> dict:
    try:
      new_service = await self.repository.create_service(business_id, name, price, description, duration_minutes)
      await self.session.commit()
      await self.session.refresh(new_service)
      
      return {
        "id": new_service.id,
        "name": new_service.name,
        "business_id": new_service.business_id,
        "price": new_service.price,
        "description": new_service.description,
        "duration_minutes": new_service.duration_minutes
      }
    except Exception as e:
      logger.error(f"Error creating service: {e}")
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Удаляем услугу (для админки)
  async def delete_service_admin(self, business_id: int, service_id: int) -> dict:
    try:
      service = await self.repository.delete_service(business_id, service_id)
      if not service:
        raise HTTPException(status_code=404, detail="Service not found")
      
      await self.session.commit()
      return {"detail": "Service deleted successfully"}
    except HTTPException:
      raise
    except Exception as e:
      logger.error(f"Error deleting service: {e}")
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Создаем связь сотрудник-услуга (для админки)
  async def create_staff_service_admin(self, business_id: int, staff_id: int, service_id: int) -> dict:
    try:
      # Проверяем существование сотрудника
      staff = await self.repository.get_staff_by_id(business_id, staff_id)
      if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
      
      # Проверяем существование услуги
      service = await self.repository.get_service_by_id(business_id, service_id)
      if not service:
        raise HTTPException(status_code=404, detail="Service not found")
      
      new_staff_service = await self.repository.create_staff_service(business_id, staff_id, service_id)
      await self.session.commit()
      await self.session.refresh(new_staff_service)
      
      return {
        "id": new_staff_service.id,
        "staff_id": new_staff_service.staff_id,
        "service_id": new_staff_service.service_id,
        "business_id": new_staff_service.business_id
      }
    except HTTPException:
      raise
    except Exception as e:
      logger.error(f"Error creating staff service: {e}")
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Отменяем запись через админку
  async def cancel_appointment_admin(self, business_id: int, appointment_id: int) -> dict:
    try:
      appointment = await self.repository.get_appointment_for_cancel(business_id, appointment_id)
      if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
      
      # Используем существующий метод отмены с флагом cancelled_by_admin
      await self.cancelled_appointment(business_id, appointment.client_id, appointment_id, cancelled_by_admin=True)
      return {"message": "Запись успешно отменена"}
    except HTTPException:
      raise
    except Exception as e:
      logger.error(f"Error cancelling appointment: {e}")
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Создаем исключение в графике (для админки)
  async def create_schedule_exception_admin(self, business_id: int, date: str, is_working: bool, custom_start: str = None, custom_end: str = None) -> dict:
    try:
      exc = await self.repository.create_schedule_exception(business_id, date, is_working, custom_start, custom_end)
      await self.session.commit()
      await self.session.refresh(exc)
      
      return {
        "message": "Exception created",
        "id": exc.id,
        "date": exc.date.strftime("%Y-%m-%d"),
        "is_working": exc.is_working,
        "custom_start_time": exc.custom_start_time.strftime("%H:%M") if exc.custom_start_time else None,
        "custom_end_time": exc.custom_end_time.strftime("%H:%M") if exc.custom_end_time else None
      }
    except Exception as e:
      logger.error(f"Error creating schedule exception: {e}")
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Получаем все исключения в графике (для админки)
  async def get_schedule_exceptions_admin(self, business_id: int) -> list[dict]:
    try:
      exceptions = await self.repository.get_all_schedule_exceptions(business_id)
      
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
    except Exception as e:
      logger.error(f"Error fetching schedule exceptions: {e}")
      raise HTTPException(status_code=500, detail="Internal Server Error")


  # Удаляем исключение в графике (для админки)
  async def delete_schedule_exception_admin(self, business_id: int, exception_id: int) -> dict:
    try:
      exception = await self.repository.delete_schedule_exception(business_id, exception_id)
      if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
      
      await self.session.commit()
      return {"message": "Exception deleted successfully"}
    except HTTPException:
      raise
    except Exception as e:
      logger.error(f"Error deleting schedule exception: {e}")
      await self.session.rollback()
      raise HTTPException(status_code=500, detail="Internal Server Error")
    