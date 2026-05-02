# Получение свободных слотов для записи

from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from app.models.appointments import AppointmentModel
from app.utils.logger import logger


async def get_free_slots(
    busy_slots: list[AppointmentModel], 
    date: datetime,
    duration_minutes: int,
    work_start_hour: int = 9,
    work_end_hour: int = 18,
    step_minutes: int = 30,
) -> list[str]:
    """
    Генерирует список свободных временных слотов для записи.

    """
    try:
        # Убеждаемся, что date имеет timezone
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        
        # Определяем границы рабочего дня
        work_start = date.replace(hour=work_start_hour, minute=0, second=0, microsecond=0)
        work_end = date.replace(hour=work_end_hour, minute=0, second=0, microsecond=0)
        
        # Получаем текущее время
        now = datetime.now(timezone.utc)
        
        # Генерируем список возможных стартовых точек
        candidate_slots = []
        current_time = work_start
        
        while current_time < work_end:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            # Проверяем что слот не выходит за рабочее время И что слот в будущем
            if slot_end <= work_end and current_time > now:
                candidate_slots.append(current_time)
            
            current_time += timedelta(minutes=step_minutes)
        
        # Фильтруем кандидатов: проверяем пересечения с занятыми слотами
        free_slots = []
        
        for slot_start in candidate_slots:
            slot_end = slot_start + timedelta(minutes=duration_minutes)
            is_free = True
            
            # Проверяем пересечение с каждым занятым интервалом
            for busy in busy_slots:
                # Убеждаемся, что времена слотов имеют timezone
                busy_start = busy.start_time if busy.start_time.tzinfo else busy.start_time.replace(tzinfo=timezone.utc)
                busy_end = busy.end_time if busy.end_time.tzinfo else busy.end_time.replace(tzinfo=timezone.utc)
                
                # Проверка пересечения: slot_start < busy_end AND slot_end > busy_start
                if slot_start < busy_end and slot_end > busy_start:
                    is_free = False
                    break
            
            if is_free:
                free_slots.append(slot_start.isoformat())
        
        return free_slots
    
    except Exception as e:
        logger.error(f"Error calculating free slots: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")