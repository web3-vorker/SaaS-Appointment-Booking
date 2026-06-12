# Ключи для кэширования в Redis и их TTL (время жизни)

# TTL в секундах
TTL_SERVICES = 600      # 10 минут — услуги меняются редко
TTL_STAFFS = 600        # 10 минут — состав мастеров меняется редко
TTL_FREE_SLOTS = 120    # 2 минуты — слоты меняются при каждой записи
TTL_FREE_DAYS = 600     # 10 минут — свободные дни меняются редко
TTL_BUSINESS = 300      # 5 минут — для валидации api_key


def key_services(business_id: int) -> str:
    return f"cache:services:business_id:{business_id}"


def key_staffs_for_service(business_id: int, service_id: int) -> str:
    return f"cache:staffs:business_id:{business_id}:service_id:{service_id}"


def key_free_slots(business_id: int, staff_id: int, service_id: int, date: str) -> str:
    return f"cache:slots:business_id:{business_id}:staff:{staff_id}:service:{service_id}:date:{date}"


def key_free_days(business_id: int, staff_id: int, service_id: int) -> str:
    return f"cache:free_days:business_id:{business_id}:staff:{staff_id}:service:{service_id}"


def key_business_by_api_key(api_key: str) -> str:
    return f"cache:business:api_key:{api_key}"


def pattern_all_slots(business_id: int) -> str:
    return f"cache:slots:business_id:{business_id}:*"


def pattern_all_free_days(business_id: int) -> str:
    return f"cache:free_days:business_id:{business_id}:*"


def pattern_all_services(business_id: int) -> str:
    return f"cache:services:business_id:{business_id}"