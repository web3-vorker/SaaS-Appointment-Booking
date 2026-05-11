"""
Скрипт для подготовки тестовых данных перед нагрузочным тестированием.

Создает:
- 10 тестовых бизнесов
- По 5 сотрудников для каждого бизнеса
- По 10 услуг для каждого бизнеса
- Привязывает услуги к сотрудникам
- Сохраняет API ключи в файл для использования в тестах

Запуск:
    python tests/prepare_test_data.py
"""

import asyncio
import aiohttp
import sys
import json
import os
import random

# Конфигурация
API_URL = "http://localhost:8000"
DEVELOPER_KEY = "mGaMuzn0a-rBRnOa08pomLzwgUwxbkPX-4SZ5uenpEA" 

# Количество тестовых данных
NUM_BUSINESSES = 10
NUM_STAFFS_PER_BUSINESS = 5
NUM_SERVICES_PER_BUSINESS = 10

# Файл для сохранения API ключей
API_KEYS_FILE = "tests/test_api_keys.json"


async def create_business(session, business_num):
    """Создание тестового бизнеса"""
    data = {
        "name": f"Test Business {business_num}",
        "working_hours_start": "09:00",
        "working_hours_end": "20:00",
        "owner_tg_id": 100000 + business_num,
        "bot_token": f"test_token_{business_num}"
    }
    
    async with session.post(
        f"{API_URL}/dev/business/",
        json=data,
        headers={"X-API-Key": DEVELOPER_KEY}
    ) as response:
        if response.status == 200:
            result = await response.json()
            print(f"✅ Создан бизнес #{result['id']}: {result['name']}")
            return result
        else:
            error = await response.text()
            print(f"[ERROR] Ошибка создания бизнеса: {error}")
            return None


async def create_staff(session, business_id, staff_num):
    """Создание тестового сотрудника"""
    data = {
        "name": f"Staff {staff_num}",
        "role": f"Master",
        "business_id": business_id
    }
    
    async with session.post(
        f"{API_URL}/dev/staff/",
        json=data,
        headers={"X-API-Key": DEVELOPER_KEY}
    ) as response:
        if response.status == 200:
            result = await response.json()
            print(f"  ✅ Создан сотрудник #{result['id']}: {result['name']}")
            return result
        else:
            error = await response.text()
            print(f"  [ERROR] Ошибка создания сотрудника: {error}")
            return None


async def create_service(session, business_id, service_num):
    """Создание тестовой услуги"""
    services = [
        {"name": "Стрижка", "price": 1000, "duration": 60},
        {"name": "Окрашивание", "price": 3000, "duration": 120},
        {"name": "Укладка", "price": 800, "duration": 45},
        {"name": "Маникюр", "price": 1200, "duration": 60},
        {"name": "Педикюр", "price": 1500, "duration": 90},
        {"name": "Массаж", "price": 2000, "duration": 60},
        {"name": "Консультация", "price": 500, "duration": 30},
        {"name": "Уход за лицом", "price": 2500, "duration": 90},
        {"name": "Эпиляция", "price": 1800, "duration": 60},
        {"name": "Макияж", "price": 1500, "duration": 60},
    ]
    
    service_template = services[service_num % len(services)]
    
    data = {
        "name": f"{service_template['name']} {service_num}",
        "price": service_template['price'],
        "duration_minutes": service_template['duration'],
        "description": f"Тестовая услуга {service_num}",
        "business_id": business_id
    }
    
    async with session.post(
        f"{API_URL}/dev/service/",
        json=data,
        headers={"X-API-Key": DEVELOPER_KEY}
    ) as response:
        if response.status == 200:
            result = await response.json()
            print(f"  ✅ Создана услуга #{result['id']}: {result['name']}")
            return result
        else:
            error = await response.text()
            print(f"  [ERROR] Ошибка создания услуги: {error}")
            return None


async def assign_service_to_staff(session, business_id, staff_id, service_id):
    """Привязка услуги к сотруднику"""
    data = {
        "staff_id": staff_id,
        "service_id": service_id,
        "business_id": business_id
    }
    
    async with session.post(
        f"{API_URL}/dev/staff-service/",
        json=data,
        headers={"X-API-Key": DEVELOPER_KEY}
    ) as response:
        if response.status == 200:
            return True
        else:
            return False


async def prepare_test_data():
    """Основная функция подготовки тестовых данных"""
    print("="*80)
    print("ПОДГОТОВКА ТЕСТОВЫХ ДАННЫХ ДЛЯ НАГРУЗОЧНОГО ТЕСТИРОВАНИЯ")
    print("="*80)
    print()
    
    # Словарь для хранения API ключей
    api_keys = {}
    
    async with aiohttp.ClientSession() as session:
        # Создаем бизнесы
        print(f"[*] Создание {NUM_BUSINESSES} тестовых бизнесов...")
        businesses = []
        for i in range(1, NUM_BUSINESSES + 1):
            business = await create_business(session, i)
            if business:
                businesses.append(business)
                # Сохраняем API ключ
                api_keys[business['id']] = business['api_key']
            await asyncio.sleep(0.1)  # Небольшая задержка
        
        print(f"\n✅ Создано бизнесов: {len(businesses)}")
        print()
        
        # Для каждого бизнеса создаем сотрудников и услуги
        for business in businesses:
            business_id = business['id']
            print(f"\n[*] Настройка бизнеса #{business_id}: {business['name']}")
            
            # Создаем сотрудников
            print(f"  [*] Создание {NUM_STAFFS_PER_BUSINESS} сотрудников...")
            staffs = []
            for i in range(1, NUM_STAFFS_PER_BUSINESS + 1):
                staff = await create_staff(session, business_id, i)
                if staff:
                    staffs.append(staff)
                await asyncio.sleep(0.05)
            
            # Создаем услуги
            print(f"  [*] Создание {NUM_SERVICES_PER_BUSINESS} услуг...")
            services = []
            for i in range(1, NUM_SERVICES_PER_BUSINESS + 1):
                service = await create_service(session, business_id, i)
                if service:
                    services.append(service)
                await asyncio.sleep(0.05)
            
            # Привязываем услуги к сотрудникам
            print(f"  [*] Привязка услуг к сотрудникам...")
            assignments = 0
            for staff in staffs:
                # Каждый сотрудник может оказывать 3-5 случайных услуг
                num_services = random.randint(3, min(5, len(services)))
                staff_services = random.sample(services, num_services)
                
                for service in staff_services:
                    success = await assign_service_to_staff(
                        session, 
                        business_id, 
                        staff['id'], 
                        service['id']
                    )
                    if success:
                        assignments += 1
                    await asyncio.sleep(0.02)
            
            print(f"  ✅ Создано привязок: {assignments}")
    
    # Сохраняем API ключи в файл
    with open(API_KEYS_FILE, 'w') as f:
        json.dump(api_keys, f, indent=2)
    
    print("\n" + "="*80)
    print("✅ ПОДГОТОВКА ДАННЫХ ЗАВЕРШЕНА")
    print("="*80)
    print()
    print("Создано:")
    print(f"  - Бизнесов: {len(businesses)}")
    print(f"  - Сотрудников: {len(businesses) * NUM_STAFFS_PER_BUSINESS}")
    print(f"  - Услуг: {len(businesses) * NUM_SERVICES_PER_BUSINESS}")
    print(f"  - API ключи сохранены в: {API_KEYS_FILE}")
    print()
    print("🚀 Теперь можно запускать нагрузочное тестирование:")
    print("   locust -f tests/load_test.py --host=http://localhost:8000")
    print()


async def cleanup_test_data():
    """Очистка тестовых данных после тестирования"""
    print("="*80)
    print("ОЧИСТКА ТЕСТОВЫХ ДАННЫХ")
    print("="*80)
    print()
    
    # Загружаем API ключи - в них сохранены ID бизнесов
    if not os.path.exists(API_KEYS_FILE):
        print(f"[ERROR] Файл {API_KEYS_FILE} не найден. Запустите prepare сначала.")
        return
    
    with open(API_KEYS_FILE, 'r') as f:
        api_keys = json.load(f)
    
    if not api_keys:
        print("[ERROR] Список бизнесов пуст.")
        return
    
    print(f"[*] Найдено {len(api_keys)} бизнесов для удаления: {list(api_keys.keys())}")
    print()
    
    deleted = 0
    async with aiohttp.ClientSession() as session:
        for business_id in api_keys.keys():
            async with session.delete(
                f"{API_URL}/dev/business/{business_id}",
                headers={"X-API-Key": DEVELOPER_KEY}
            ) as response:
                if response.status == 200:
                    print(f"✅ Удален бизнес #{business_id}")
                    deleted += 1
                else:
                    error = await response.text()
                    print(f"[WARN] Бизнес #{business_id}: {error}")
    
    # Удаляем файл с API ключами
    os.remove(API_KEYS_FILE)
    
    print()
    print(f"✅ Очистка завершена. Удалено бизнесов: {deleted}")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        asyncio.run(cleanup_test_data())
    else:
        asyncio.run(prepare_test_data())
