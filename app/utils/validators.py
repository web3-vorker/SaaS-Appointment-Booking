import re
from fastapi import HTTPException


def validate_phone(phone: str) -> str:
    """
    Валидация номера телефона.
    Принимает форматы: +79991234567, 89991234567, 79991234567
    Возвращает нормализованный формат: +79991234567
    
    Args:
        phone: Номер телефона
        
    Returns:
        Нормализованный номер телефона
        
    Raises:
        HTTPException: Если номер телефона невалидный
    """
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    
    # Убираем все символы кроме цифр и +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Убираем + в начале для проверки
    digits_only = cleaned.lstrip('+')
    
    # Проверяем что остались только цифры
    if not digits_only.isdigit():
        raise HTTPException(status_code=400, detail="Invalid phone number format")
    
    # Проверяем длину (для российских номеров)
    if len(digits_only) < 10 or len(digits_only) > 11:
        raise HTTPException(status_code=400, detail="Phone number must be 10-11 digits")
    
    # Нормализуем формат
    if len(digits_only) == 10:
        # Если 10 цифр, добавляем 7 в начало
        normalized = f"+7{digits_only}"
    elif digits_only.startswith('8'):
        # Если начинается с 8, заменяем на 7
        normalized = f"+7{digits_only[1:]}"
    elif digits_only.startswith('7'):
        # Если начинается с 7, просто добавляем +
        normalized = f"+{digits_only}"
    else:
        # Для других стран оставляем как есть
        normalized = f"+{digits_only}"
    
    return normalized
