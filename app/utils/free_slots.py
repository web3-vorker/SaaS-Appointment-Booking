# Получение свободных слотов для записи

from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from app.models.appointments import AppointmentModel
from app.utils.logger import logger
from app.utils.datetime_utils import now_utc, to_naive_utc
from app.config.config import config


async def get_free_slots(
    busy_slots: list[AppointmentModel], 
    date: datetime,
    duration_minutes: int,
    work_start: datetime = None,
    work_end: datetime = None,
    step_minutes: int = 30,
    timezone_offset: int = None,
    business = None,
    schedule_exception = None,
) -> list[str]:
    """
    Генерирует список свободных временных слотов для записи.
    Все datetime объекты должны быть naive UTC.
    
    Логика работы:
    1. Рабочее время (work_start, work_end) задано в ЛОКАЛЬНОМ времени бизнеса
    2. Все вычисления производятся в UTC
    3. Для сегодняшнего дня учитывается минимальный буфер времени
    4. Учитываются перерывы (обеды)
    5. Учитываются исключения в графике (кастомное рабочее время)
    
    Args:
        busy_slots: Список занятых слотов (в UTC)
        date: Дата для генерации слотов (naive UTC, начало дня 00:00:00)
        duration_minutes: Длительность услуги в минутах
        work_start: Время начала работы (time объект в локальном времени)
        work_end: Время окончания работы (time объект в локальном времени)
        step_minutes: Шаг между слотами в минутах
        timezone_offset: Смещение timezone от UTC в часах (например, 3 для UTC+3)
        business: Объект бизнеса (для получения break_start, break_end)
        schedule_exception: Исключение в графике для этой даты
    
    Returns:
        Список свободных слотов в ISO формате (UTC)
    """
    try:
        # Приводим date к naive UTC
        date = to_naive_utc(date)
        
        # Текущее время в UTC
        now = now_utc()
        
        # Если передан timezone_offset, используем его, иначе берем из конфига
        if timezone_offset is None:
            timezone_offset = config.timezone_offset
        
        # Определяем рабочее время
        # Если есть исключение с кастомным временем - используем его
        if schedule_exception and schedule_exception.custom_start_time and schedule_exception.custom_end_time:
            work_start_hour_local = schedule_exception.custom_start_time.hour
            work_start_minute_local = schedule_exception.custom_start_time.minute
            work_end_hour_local = schedule_exception.custom_end_time.hour
            work_end_minute_local = schedule_exception.custom_end_time.minute
        else:
            # Используем стандартное рабочее время
            if work_start is None:
                work_start_hour_local = 9
                work_start_minute_local = 0
            else:
                work_start_hour_local = work_start.hour
                work_start_minute_local = work_start.minute
            
            if work_end is None:
                work_end_hour_local = 18
                work_end_minute_local = 0
            else:
                work_end_hour_local = work_end.hour
                work_end_minute_local = work_end.minute
        
        # Создаем datetime для начала и конца рабочего дня
        # Шаг 1: Получаем дату в локальном времени
        local_date = date + timedelta(hours=timezone_offset)
        
        # Шаг 2: Создаем локальное рабочее время
        work_start_time_local = local_date.replace(
            hour=work_start_hour_local, 
            minute=work_start_minute_local, 
            second=0, 
            microsecond=0
        )
        work_end_time_local = local_date.replace(
            hour=work_end_hour_local, 
            minute=work_end_minute_local, 
            second=0, 
            microsecond=0
        )
        
        # Шаг 3: Конвертируем локальное время в UTC
        work_start_time_utc = work_start_time_local - timedelta(hours=timezone_offset)
        work_end_time_utc = work_end_time_local - timedelta(hours=timezone_offset)
        
        # Получаем время перерыва (обеда) если есть
        break_start_utc = None
        break_end_utc = None
        if business and business.break_start and business.break_end:
            break_start_local = local_date.replace(
                hour=business.break_start.hour,
                minute=business.break_start.minute,
                second=0,
                microsecond=0
            )
            break_end_local = local_date.replace(
                hour=business.break_end.hour,
                minute=business.break_end.minute,
                second=0,
                microsecond=0
            )
            break_start_utc = break_start_local - timedelta(hours=timezone_offset)
            break_end_utc = break_end_local - timedelta(hours=timezone_offset)

        # Генерируем список возможных стартовых точек в UTC
        candidate_slots = []
        current_time_utc = work_start_time_utc
        
        # Проверяем, это сегодняшний день или будущий
        today_utc = now.replace(hour=0, minute=0, second=0, microsecond=0)
        check_date_utc = date.replace(hour=0, minute=0, second=0, microsecond=0)
        is_today = check_date_utc == today_utc
        
        # Для сегодняшнего дня учитываем минимальный буфер времени
        if is_today:
            min_booking_time_utc = now + timedelta(minutes=config.min_booking_buffer_minutes)
        
        while current_time_utc < work_end_time_utc:
            slot_end_utc = current_time_utc + timedelta(minutes=duration_minutes)
            
            # Проверяем что слот не выходит за рабочее время
            if slot_end_utc <= work_end_time_utc:
                # Проверяем что слот не пересекается с перерывом
                slot_overlaps_break = False
                if break_start_utc and break_end_utc:
                    # Слот пересекается с перерывом если:
                    # slot_start < break_end AND slot_end > break_start
                    if current_time_utc < break_end_utc and slot_end_utc > break_start_utc:
                        slot_overlaps_break = True
                
                if not slot_overlaps_break:
                    # Если это сегодня, проверяем что слот начинается после минимального времени
                    if is_today:
                        if current_time_utc >= min_booking_time_utc:
                            candidate_slots.append(current_time_utc)
                    else:
                        # Для будущих дней добавляем все слоты
                        candidate_slots.append(current_time_utc)
            
            current_time_utc += timedelta(minutes=step_minutes)
        
        # Фильтруем кандидатов: проверяем пересечения с занятыми слотами
        free_slots = []
        
        for slot_start_utc in candidate_slots:
            slot_end_utc = slot_start_utc + timedelta(minutes=duration_minutes)
            is_free = True
            
            # Проверяем пересечение с каждым занятым интервалом
            for busy in busy_slots:
                # Приводим busy времена к naive UTC
                busy_start_utc = to_naive_utc(busy.start_time)
                busy_end_utc = to_naive_utc(busy.end_time)

                # Проверка пересечения: slot_start < busy_end AND slot_end > busy_start
                if slot_start_utc < busy_end_utc and slot_end_utc > busy_start_utc:
                    is_free = False
                    break
            
            if is_free:
                free_slots.append(slot_start_utc.isoformat())
        
        return free_slots
    
    except Exception as e:
        logger.error(f"Error calculating free slots: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")