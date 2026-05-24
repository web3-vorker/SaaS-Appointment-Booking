# РџРѕР»СѓС‡РµРЅРёРµ СЃРІРѕР±РѕРґРЅС‹С… СЃР»РѕС‚РѕРІ РґР»СЏ Р·Р°РїРёСЃРё

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
    Р“РµРЅРµСЂРёСЂСѓРµС‚ СЃРїРёСЃРѕРє СЃРІРѕР±РѕРґРЅС‹С… РІСЂРµРјРµРЅРЅС‹С… СЃР»РѕС‚РѕРІ РґР»СЏ Р·Р°РїРёСЃРё.
    Р’СЃРµ datetime РѕР±СЉРµРєС‚С‹ РґРѕР»Р¶РЅС‹ Р±С‹С‚СЊ naive UTC.
    
    Р›РѕРіРёРєР° СЂР°Р±РѕС‚С‹:
    1. Р Р°Р±РѕС‡РµРµ РІСЂРµРјСЏ (work_start, work_end) Р·Р°РґР°РЅРѕ РІ Р›РћРљРђР›Р¬РќРћРњ РІСЂРµРјРµРЅРё Р±РёР·РЅРµСЃР°
    2. Р’СЃРµ РІС‹С‡РёСЃР»РµРЅРёСЏ РїСЂРѕРёР·РІРѕРґСЏС‚СЃСЏ РІ UTC
    3. Р”Р»СЏ СЃРµРіРѕРґРЅСЏС€РЅРµРіРѕ РґРЅСЏ СѓС‡РёС‚С‹РІР°РµС‚СЃСЏ РјРёРЅРёРјР°Р»СЊРЅС‹Р№ Р±СѓС„РµСЂ РІСЂРµРјРµРЅРё
    4. РЈС‡РёС‚С‹РІР°СЋС‚СЃСЏ РїРµСЂРµСЂС‹РІС‹ (РѕР±РµРґС‹)
    5. РЈС‡РёС‚С‹РІР°СЋС‚СЃСЏ РёСЃРєР»СЋС‡РµРЅРёСЏ РІ РіСЂР°С„РёРєРµ (РєР°СЃС‚РѕРјРЅРѕРµ СЂР°Р±РѕС‡РµРµ РІСЂРµРјСЏ)
    
    Args:
        busy_slots: РЎРїРёСЃРѕРє Р·Р°РЅСЏС‚С‹С… СЃР»РѕС‚РѕРІ (РІ UTC)
        date: Р”Р°С‚Р° РґР»СЏ РіРµРЅРµСЂР°С†РёРё СЃР»РѕС‚РѕРІ (naive UTC, РЅР°С‡Р°Р»Рѕ РґРЅСЏ 00:00:00)
        duration_minutes: Р”Р»РёС‚РµР»СЊРЅРѕСЃС‚СЊ СѓСЃР»СѓРіРё РІ РјРёРЅСѓС‚Р°С…
        work_start: Р’СЂРµРјСЏ РЅР°С‡Р°Р»Р° СЂР°Р±РѕС‚С‹ (time РѕР±СЉРµРєС‚ РІ Р»РѕРєР°Р»СЊРЅРѕРј РІСЂРµРјРµРЅРё)
        work_end: Р’СЂРµРјСЏ РѕРєРѕРЅС‡Р°РЅРёСЏ СЂР°Р±РѕС‚С‹ (time РѕР±СЉРµРєС‚ РІ Р»РѕРєР°Р»СЊРЅРѕРј РІСЂРµРјРµРЅРё)
        step_minutes: РЁР°Рі РјРµР¶РґСѓ СЃР»РѕС‚Р°РјРё РІ РјРёРЅСѓС‚Р°С…
        timezone_offset: РЎРјРµС‰РµРЅРёРµ timezone РѕС‚ UTC РІ С‡Р°СЃР°С… (РЅР°РїСЂРёРјРµСЂ, 3 РґР»СЏ UTC+3)
        business: РћР±СЉРµРєС‚ Р±РёР·РЅРµСЃР° (РґР»СЏ РїРѕР»СѓС‡РµРЅРёСЏ break_start, break_end)
        schedule_exception: РСЃРєР»СЋС‡РµРЅРёРµ РІ РіСЂР°С„РёРєРµ РґР»СЏ СЌС‚РѕР№ РґР°С‚С‹
    
    Returns:
        РЎРїРёСЃРѕРє СЃРІРѕР±РѕРґРЅС‹С… СЃР»РѕС‚РѕРІ РІ ISO С„РѕСЂРјР°С‚Рµ (UTC)
    """
    try:
        # РџСЂРёРІРѕРґРёРј date Рє naive UTC
        date = to_naive_utc(date)
        
        # РўРµРєСѓС‰РµРµ РІСЂРµРјСЏ РІ UTC
        now = now_utc()
        
        # Р•СЃР»Рё РїРµСЂРµРґР°РЅ timezone_offset, РёСЃРїРѕР»СЊР·СѓРµРј РµРіРѕ, РёРЅР°С‡Рµ Р±РµСЂРµРј РёР· РєРѕРЅС„РёРіР°
        if timezone_offset is None:
            timezone_offset = config.timezone_offset
        
        # РћРїСЂРµРґРµР»СЏРµРј СЂР°Р±РѕС‡РµРµ РІСЂРµРјСЏ
        # Р•СЃР»Рё РµСЃС‚СЊ РёСЃРєР»СЋС‡РµРЅРёРµ СЃ РєР°СЃС‚РѕРјРЅС‹Рј РІСЂРµРјРµРЅРµРј - РёСЃРїРѕР»СЊР·СѓРµРј РµРіРѕ
        if schedule_exception and schedule_exception.custom_start_time and schedule_exception.custom_end_time:
            work_start_hour_local = schedule_exception.custom_start_time.hour
            work_start_minute_local = schedule_exception.custom_start_time.minute
            work_end_hour_local = schedule_exception.custom_end_time.hour
            work_end_minute_local = schedule_exception.custom_end_time.minute
        else:
            # РСЃРїРѕР»СЊР·СѓРµРј СЃС‚Р°РЅРґР°СЂС‚РЅРѕРµ СЂР°Р±РѕС‡РµРµ РІСЂРµРјСЏ
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
        
        # РЎРѕР·РґР°РµРј datetime РґР»СЏ РЅР°С‡Р°Р»Р° Рё РєРѕРЅС†Р° СЂР°Р±РѕС‡РµРіРѕ РґРЅСЏ
        # РЁР°Рі 1: РџРѕР»СѓС‡Р°РµРј РґР°С‚Сѓ РІ Р»РѕРєР°Р»СЊРЅРѕРј РІСЂРµРјРµРЅРё
        local_date = date + timedelta(hours=timezone_offset)
        
        # РЁР°Рі 2: РЎРѕР·РґР°РµРј Р»РѕРєР°Р»СЊРЅРѕРµ СЂР°Р±РѕС‡РµРµ РІСЂРµРјСЏ
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
        
        # РЁР°Рі 3: РљРѕРЅРІРµСЂС‚РёСЂСѓРµРј Р»РѕРєР°Р»СЊРЅРѕРµ РІСЂРµРјСЏ РІ UTC
        work_start_time_utc = work_start_time_local - timedelta(hours=timezone_offset)
        work_end_time_utc = work_end_time_local - timedelta(hours=timezone_offset)
        
        # РџРѕР»СѓС‡Р°РµРј РІСЂРµРјСЏ РїРµСЂРµСЂС‹РІР° (РѕР±РµРґР°) РµСЃР»Рё РµСЃС‚СЊ
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

        # Р“РµРЅРµСЂРёСЂСѓРµРј СЃРїРёСЃРѕРє РІРѕР·РјРѕР¶РЅС‹С… СЃС‚Р°СЂС‚РѕРІС‹С… С‚РѕС‡РµРє РІ UTC
        candidate_slots = []
        current_time_utc = work_start_time_utc
        
        # РџСЂРѕРІРµСЂСЏРµРј, СЌС‚Рѕ СЃРµРіРѕРґРЅСЏС€РЅРёР№ РґРµРЅСЊ РёР»Рё Р±СѓРґСѓС‰РёР№
        today_utc = now.replace(hour=0, minute=0, second=0, microsecond=0)
        check_date_utc = date.replace(hour=0, minute=0, second=0, microsecond=0)
        is_today = check_date_utc == today_utc
        
        # Р”Р»СЏ СЃРµРіРѕРґРЅСЏС€РЅРµРіРѕ РґРЅСЏ СѓС‡РёС‚С‹РІР°РµРј РјРёРЅРёРјР°Р»СЊРЅС‹Р№ Р±СѓС„РµСЂ РІСЂРµРјРµРЅРё
        if is_today:
            min_booking_time_utc = now + timedelta(minutes=config.min_booking_buffer_minutes)
        
        while current_time_utc < work_end_time_utc:
            slot_end_utc = current_time_utc + timedelta(minutes=duration_minutes)
            
            # РџСЂРѕРІРµСЂСЏРµРј С‡С‚Рѕ СЃР»РѕС‚ РЅРµ РІС‹С…РѕРґРёС‚ Р·Р° СЂР°Р±РѕС‡РµРµ РІСЂРµРјСЏ
            if slot_end_utc <= work_end_time_utc:
                # РџСЂРѕРІРµСЂСЏРµРј С‡С‚Рѕ СЃР»РѕС‚ РЅРµ РїРµСЂРµСЃРµРєР°РµС‚СЃСЏ СЃ РїРµСЂРµСЂС‹РІРѕРј
                slot_overlaps_break = False
                if break_start_utc and break_end_utc:
                    # РЎР»РѕС‚ РїРµСЂРµСЃРµРєР°РµС‚СЃСЏ СЃ РїРµСЂРµСЂС‹РІРѕРј РµСЃР»Рё:
                    # slot_start < break_end AND slot_end > break_start
                    if current_time_utc < break_end_utc and slot_end_utc > break_start_utc:
                        slot_overlaps_break = True
                
                if not slot_overlaps_break:
                    # Р•СЃР»Рё СЌС‚Рѕ СЃРµРіРѕРґРЅСЏ, РїСЂРѕРІРµСЂСЏРµРј С‡С‚Рѕ СЃР»РѕС‚ РЅР°С‡РёРЅР°РµС‚СЃСЏ РїРѕСЃР»Рµ РјРёРЅРёРјР°Р»СЊРЅРѕРіРѕ РІСЂРµРјРµРЅРё
                    if is_today:
                        if current_time_utc >= min_booking_time_utc:
                            candidate_slots.append(current_time_utc)
                    else:
                        # Р”Р»СЏ Р±СѓРґСѓС‰РёС… РґРЅРµР№ РґРѕР±Р°РІР»СЏРµРј РІСЃРµ СЃР»РѕС‚С‹
                        candidate_slots.append(current_time_utc)
            
            current_time_utc += timedelta(minutes=step_minutes)
        
        # Р¤РёР»СЊС‚СЂСѓРµРј РєР°РЅРґРёРґР°С‚РѕРІ: РїСЂРѕРІРµСЂСЏРµРј РїРµСЂРµСЃРµС‡РµРЅРёСЏ СЃ Р·Р°РЅСЏС‚С‹РјРё СЃР»РѕС‚Р°РјРё
        free_slots = []
        
        for slot_start_utc in candidate_slots:
            slot_end_utc = slot_start_utc + timedelta(minutes=duration_minutes)
            is_free = True
            
            # РџСЂРѕРІРµСЂСЏРµРј РїРµСЂРµСЃРµС‡РµРЅРёРµ СЃ РєР°Р¶РґС‹Рј Р·Р°РЅСЏС‚С‹Рј РёРЅС‚РµСЂРІР°Р»РѕРј
            for busy in busy_slots:
                # РџСЂРёРІРѕРґРёРј busy РІСЂРµРјРµРЅР° Рє naive UTC
                busy_start_utc = to_naive_utc(busy.start_time)
                busy_end_utc = to_naive_utc(busy.end_time)

                # РџСЂРѕРІРµСЂРєР° РїРµСЂРµСЃРµС‡РµРЅРёСЏ: slot_start < busy_end AND slot_end > busy_start
                if slot_start_utc < busy_end_utc and slot_end_utc > busy_start_utc:
                    is_free = False
                    break
            
            if is_free:
                free_slots.append(slot_start_utc.isoformat())
        
        return free_slots
    
    except Exception as e:
        logger.error("error_calculating_free_slots", error=str(e), error_type=type(e).__name__, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
