"""
API клиент для взаимодействия с developer endpoints backend
"""

import aiohttp
from dev_bot.config.config import dev_bot_config


class DevAPI:
    """Класс для работы с developer API"""

    def __init__(self):
        self.base_url = dev_bot_config.api_url
        self.headers = {
            "X-API-Key": dev_bot_config.developer_key,
            "Content-Type": "application/json"
        }

    async def _make_request(self, method: str, endpoint: str, **kwargs):
        """Базовый метод для выполнения HTTP запросов"""
        url = f"{self.base_url}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=self.headers, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"API Error {response.status}: {error_text}")

    # ===== Бизнесы =====
    
    async def get_all_businesses(self):
        """Получить список всех бизнесов"""
        return await self._make_request("GET", "/dev/businesses/")

    async def create_business(self, name: str, working_hours_start: str, working_hours_end: str, owner_tg_id: int):
        """Создать новый бизнес"""
        data = {
            "name": name,
            "working_hours_start": working_hours_start,
            "working_hours_end": working_hours_end,
            "owner_tg_id": owner_tg_id,
        }
        return await self._make_request("POST", "/dev/business/", json=data)

    async def delete_business(self, business_id: int):
        """Удалить бизнес"""
        return await self._make_request("DELETE", f"/dev/business/{business_id}")

    # ===== Сотрудники =====
    
    async def get_staffs(self, business_id: int):
        """Получить всех сотрудников бизнеса"""
        return await self._make_request("GET", f"/dev/staffs/{business_id}")
    
    async def create_staff(self, business_id: int, name: str, role: str):
        """Создать сотрудника"""
        data = {
            "business_id": business_id,
            "name": name,
            "role": role
        }
        return await self._make_request("POST", "/dev/staff/", json=data)

    async def delete_staff(self, business_id: int, staff_id: int):
        """Удалить сотрудника"""
        params = {"business_id": business_id}
        return await self._make_request("DELETE", f"/dev/staff/{staff_id}", params=params)

    # ===== Услуги =====
    
    async def get_services(self, business_id: int):
        """Получить все услуги бизнеса"""
        return await self._make_request("GET", f"/dev/services/{business_id}")
    
    async def create_service(self, business_id: int, name: str, price: int, duration_minutes: int, description: str = ""):
        """Создать услугу"""
        data = {
            "business_id": business_id,
            "name": name,
            "price": price,
            "duration_minutes": duration_minutes,
            "description": description
        }
        return await self._make_request("POST", "/dev/service/", json=data)

    async def delete_service(self, business_id: int, service_id: int):
        """Удалить услугу"""
        params = {"business_id": business_id}
        return await self._make_request("DELETE", f"/dev/service/{service_id}", params=params)

    # ===== Привязка услуг к сотрудникам =====
    
    async def assign_service_to_staff(self, business_id: int, staff_id: int, service_id: int):
        """Привязать услугу к сотруднику"""
        data = {
            "business_id": business_id,
            "staff_id": staff_id,
            "service_id": service_id
        }
        return await self._make_request("POST", "/dev/staff-service/", json=data)

    async def get_staff_services(self, business_id: int):
        """Получить все привязки услуг к сотрудникам для бизнеса"""
        params = {"business_id": business_id}
        return await self._make_request("GET", "/dev/staff-services/", params=params)

    # ===== График работы =====
    
    async def update_schedule(self, business_id: int, break_start: str = None, break_end: str = None, weekend_days: list = None):
        """Обновить график работы бизнеса"""
        params = []
        if break_start:
            params.append(("break_start", break_start))
        if break_end:
            params.append(("break_end", break_end))
        if weekend_days is not None:
            for day in weekend_days:
                params.append(("weekend_days", day))
        
        return await self._make_request("PATCH", f"/dev/business/{business_id}/schedule/", params=params)

    async def create_schedule_exception(self, business_id: int, date: str, is_working: bool, custom_start: str = None, custom_end: str = None):
        """Создать исключение в графике"""
        params = {
            "date": date,
            "is_working": str(is_working).lower()
        }
        if custom_start:
            params["custom_start"] = custom_start
        if custom_end:
            params["custom_end"] = custom_end
        
        return await self._make_request("POST", f"/dev/business/{business_id}/schedule-exception/", params=params)

    async def get_schedule_exceptions(self, business_id: int):
        """Получить все исключения в графике"""
        return await self._make_request("GET", f"/dev/business/{business_id}/schedule-exceptions/")

    async def delete_schedule_exception(self, business_id: int, exception_id: int):
        """Удалить исключение в графике"""
        return await self._make_request("DELETE", f"/dev/business/{business_id}/schedule-exception/{exception_id}")


# Глобальный экземпляр API клиента
dev_api = DevAPI()
