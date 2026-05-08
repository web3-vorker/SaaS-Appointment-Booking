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
) -> list[str]:
    """
    Генерирует список свободных временных слотов для записи.
    Все datetime объекты должны быть naive UTC.
    
    Логика работы:
    1. Рабочее время (work_start, work_end) задано в ЛОКАЛЬНОМ времени бизнеса
    2. Все вычисления производятся в UTC
    3. Для сегодняшнего дня учитывается минимальный буфер времени
    
    Args:
        busy_slots: Список занятых слотов (в UTC)
        date: Дата для генерации слотов (naive UTC, начало дня 00:00:00)
        duration_minutes: Длительность услуги в минутах
        work_start: Время начала работы (time объект в локальном времени)
        work_end: Время окончания работы (time объект в локальном времени)
        step_minutes: Шаг между слотами в минутах
        timezone_offset: Смещение timezone от UTC в часах (например, 3 для UTC+3)
    
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
        
        # Настраиваем рабочее время
        # work_start и work_end это time объекты в ЛОКАЛЬНОМ времени бизнеса
        # Нужно конвертировать их в UTC для корректных вычислений
        
        if work_start is None:
            # По умолчанию 09:00 локально
            work_start_hour_local = 9
            work_start_minute_local = 0
        else:
            # Извлекаем hour и minute из time объекта (это локальное время)
            work_start_hour_local = work_start.hour
            work_start_minute_local = work_start.minute
        
        if work_end is None:
            # По умолчанию 18:00 локально
            work_end_hour_local = 18
            work_end_minute_local = 0
        else:
            # Извлекаем hour и minute из time объекта (это локальное время)
            work_end_hour_local = work_end.hour
            work_end_minute_local = work_end.minute
        
        # Создаем datetime для начала и конца рабочего дня в локальном времени
        # date уже в UTC, но представляет начало дня (00:00:00)
        # Нам нужно создать локальное время для этой даты, а затем конвертировать в UTC
        
        # Шаг 1: Получаем дату в локальном времени
        # date в UTC 00:00:00 соответствует локальной дате + timezone_offset часов
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
        
        # Шаг 3: Конвертируем локальное время в UTC (вычитаем offset)
        work_start_time_utc = work_start_time_local - timedelta(hours=timezone_offset)
        work_end_time_utc = work_end_time_local - timedelta(hours=timezone_offset)
        
        logger.info(f"Date (UTC): {date}, Local date: {local_date.date()}")
        logger.info(f"Work hours (local): {work_start_hour_local}:00 - {work_end_hour_local}:00")
        logger.info(f"Work hours (UTC): {work_start_time_utc} - {work_end_time_utc}")

        # Генерируем список возможных стартовых точек в UTC
        candidate_slots = []
        current_time_utc = work_start_time_utc
        
        # Проверяем, это сегодняшний день или будущий
        today_utc = now.replace(hour=0, minute=0, second=0, microsecond=0)
        check_date_utc = date.replace(hour=0, minute=0, second=0, microsecond=0)
        is_today = check_date_utc == today_utc
        
        # Для сегодняшнего дня учитываем минимальный буфер времени
        if is_today:
            # Минимальное время для записи = текущее UTC время + буфер
            min_booking_time_utc = now + timedelta(minutes=config.min_booking_buffer_minutes)
            logger.info(f"Today: current UTC time = {now}, min booking time (UTC) = {min_booking_time_utc}")
        
        while current_time_utc < work_end_time_utc:
            slot_end_utc = current_time_utc + timedelta(minutes=duration_minutes)
            
            # Проверяем что слот не выходит за рабочее время
            if slot_end_utc <= work_end_time_utc:
                # Если это сегодня, проверяем что слот начинается после минимального времени
                if is_today:
                    if current_time_utc >= min_booking_time_utc:
                        candidate_slots.append(current_time_utc)
                else:
                    # Для будущих дней добавляем все слоты
                    candidate_slots.append(current_time_utc)
            
            current_time_utc += timedelta(minutes=step_minutes)
        
        logger.info(f"Generated {len(candidate_slots)} candidate slots")
        
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
        
        logger.info(f"Found {len(free_slots)} free slots after filtering")
        return free_slots
    
    except Exception as e:
        logger.error(f"Error calculating free slots: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")