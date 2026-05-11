"""
Нагрузочное тестирование SaaS Appointment Booking System

Симулирует работу 100 Telegram ботов, делающих запросы к backend.
Имитирует реальные сценарии использования:
- Получение списка услуг
- Получение мастеров для услуги
- Получение свободных дней
- Получение свободных слотов
- Создание клиентов
- Создание записей
- Получение записей клиента
- Отмена записей

Запуск:
    locust -f tests/load_test.py --host=http://localhost:8000

Или headless режим:
    locust -f tests/load_test.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 5m --html=load_test_report.html
"""

import random
import time
import json
import os
from datetime import datetime, timedelta
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner


# Загрузка API ключей из файла
API_KEYS_FILE = "tests/test_api_keys.json"
API_KEYS = {}

try:
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, 'r') as f:
            API_KEYS = json.load(f)
        print(f"✅ Загружено {len(API_KEYS)} API ключей из {API_KEYS_FILE}")
    else:
        print(f"⚠️  Файл {API_KEYS_FILE} не найден!")
        print("   Запустите: python tests/prepare_test_data.py")
except Exception as e:
    print(f"❌ Ошибка загрузки API ключей: {e}")


# Глобальная статистика
class Stats:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_response_time = 0
        self.min_response_time = float('inf')
        self.max_response_time = 0
        
        # Статистика по типам запросов
        self.request_types = {}
        
        # Статистика по бизнесам
        self.business_stats = {}
        
        # Ошибки
        self.errors = {}
        
    def add_request(self, request_type, response_time, success, business_id=None, error=None):
        self.total_requests += 1
        self.total_response_time += response_time
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            
        self.min_response_time = min(self.min_response_time, response_time)
        self.max_response_time = max(self.max_response_time, response_time)
        
        # Статистика по типам
        if request_type not in self.request_types:
            self.request_types[request_type] = {
                'count': 0,
                'success': 0,
                'failed': 0,
                'total_time': 0
            }
        
        self.request_types[request_type]['count'] += 1
        self.request_types[request_type]['total_time'] += response_time
        if success:
            self.request_types[request_type]['success'] += 1
        else:
            self.request_types[request_type]['failed'] += 1
            
        # Статистика по бизнесам
        if business_id:
            if business_id not in self.business_stats:
                self.business_stats[business_id] = {
                    'requests': 0,
                    'success': 0,
                    'failed': 0
                }
            self.business_stats[business_id]['requests'] += 1
            if success:
                self.business_stats[business_id]['success'] += 1
            else:
                self.business_stats[business_id]['failed'] += 1
                
        # Ошибки
        if error:
            if error not in self.errors:
                self.errors[error] = 0
            self.errors[error] += 1
    
    def print_report(self):
        print("\n" + "="*80)
        print("ОТЧЕТ О НАГРУЗОЧНОМ ТЕСТИРОВАНИИ")
        print("="*80)
        
        print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
        print(f"  Всего запросов: {self.total_requests}")
        print(f"  ✅ Успешных: {self.successful_requests} ({self.successful_requests/self.total_requests*100:.2f}%)")
        print(f"  ❌ Ошибок: {self.failed_requests} ({self.failed_requests/self.total_requests*100:.2f}%)")
        
        if self.total_requests > 0:
            avg_response_time = self.total_response_time / self.total_requests
            print(f"\n⏱️  ВРЕМЯ ОТВЕТА:")
            print(f"  Среднее: {avg_response_time:.2f} мс")
            print(f"  Минимальное: {self.min_response_time:.2f} мс")
            print(f"  Максимальное: {self.max_response_time:.2f} мс")
        
        print(f"\n📈 СТАТИСТИКА ПО ТИПАМ ЗАПРОСОВ:")
        for req_type, stats in sorted(self.request_types.items(), key=lambda x: x[1]['count'], reverse=True):
            avg_time = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
            success_rate = stats['success'] / stats['count'] * 100 if stats['count'] > 0 else 0
            print(f"  {req_type}:")
            print(f"    Запросов: {stats['count']}")
            print(f"    Успешных: {stats['success']} ({success_rate:.1f}%)")
            print(f"    Среднее время: {avg_time:.2f} мс")
        
        if self.business_stats:
            print(f"\n🏢 СТАТИСТИКА ПО БИЗНЕСАМ:")
            for business_id, stats in sorted(self.business_stats.items(), key=lambda x: int(x[0]) if isinstance(x[0], str) else x[0]):
                success_rate = stats['success'] / stats['requests'] * 100 if stats['requests'] > 0 else 0
                print(f"  Бизнес #{business_id}:")
                print(f"    Запросов: {stats['requests']}")
                print(f"    Успешных: {stats['success']} ({success_rate:.1f}%)")
        
        if self.errors:
            print(f"\n❌ ОШИБКИ:")
            for error, count in sorted(self.errors.items(), key=lambda x: x[1], reverse=True):
                print(f"  {error}: {count}")
        
        print("\n" + "="*80)


# Глобальный объект статистики
global_stats = Stats()


# События для сбора статистики
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    success = exception is None
    error = str(exception) if exception else None
    business_id = context.get('business_id') if context else None
    
    global_stats.add_request(
        request_type=name,
        response_time=response_time,
        success=success,
        business_id=business_id,
        error=error
    )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Вывод отчета после завершения теста"""
    global_stats.print_report()


class TelegramBotUser(HttpUser):
    """
    Симулирует работу одного Telegram бота.
    Каждый бот представляет один бизнес и делает запросы от имени клиентов.
    """
    
    # Время ожидания между запросами (имитация реального использования)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Инициализация при старте пользователя"""
        # Проверяем, что API ключи загружены
        if not API_KEYS:
            print("❌ API ключи не загружены! Запустите: python tests/prepare_test_data.py")
            self.environment.runner.quit()
            return
        
        # Каждый бот представляет один бизнес
        # Выбираем случайный бизнес из доступных
        available_business_ids = list(API_KEYS.keys())
        business_id_str = random.choice(available_business_ids)
        self.business_id = int(business_id_str)  # Конвертируем в число
        self.api_key = API_KEYS[business_id_str]
        
        # Кэш данных для оптимизации
        self.services = []
        self.staffs = []
        self.clients = []
        
        # Загружаем начальные данные
        self._load_initial_data()
    
    def _load_initial_data(self):
        """Загрузка начальных данных (услуги, сотрудники)"""
        # Получаем услуги
        with self.client.get(
            "/api/v1/services/",
            headers={"X-API-Key": self.api_key},
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                self.services = response.json()
                # Проверяем, что все услуги принадлежат этому бизнесу
                for service in self.services:
                    if service.get('business_id') != int(self.business_id):
                        print(f"⚠️  WARNING: Service {service['id']} belongs to business {service.get('business_id')}, but loaded for business {self.business_id} - MISMATCH!")
            else:
                response.failure(f"Failed to load services: {response.status_code}")
        
        # Создаем маппинг услуга -> сотрудники
        self.service_staffs_map = {}
        if self.services:
            for service in self.services:
                with self.client.get(
                    f"/api/v1/services/{service['id']}/staffs/",
                    headers={"X-API-Key": self.api_key},
                    catch_response=True,
                    context={'business_id': self.business_id}
                ) as response:
                    if response.status_code == 200:
                        staffs = response.json()
                        if staffs:
                            # Проверяем, что все сотрудники принадлежат этому бизнесу
                            for staff in staffs:
                                if staff.get('business_id') != int(self.business_id):
                                    print(f"⚠️  WARNING: Staff {staff['id']} belongs to business {staff.get('business_id')}, but loaded for business {self.business_id} - MISMATCH!")
                            self.service_staffs_map[service['id']] = staffs
                    else:
                        response.failure(f"Failed to load staffs for service {service['id']}: {response.status_code}")
    
    @task(10)
    def get_services(self):
        """Получение списка услуг (частый запрос)"""
        with self.client.get(
            "/api/v1/services/",
            headers={"X-API-Key": self.api_key},
            name="GET /services/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                self.services = response.json()
                # Очищаем маппинг, чтобы избежать рассинхронизации
                self.service_staffs_map = {}
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(8)
    def get_service_staffs(self):
        """Получение мастеров для услуги"""
        if not self.services:
            return
        
        service = random.choice(self.services)
        with self.client.get(
            f"/api/v1/services/{service['id']}/staffs/",
            headers={"X-API-Key": self.api_key},
            name="GET /services/{id}/staffs/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                # Обновляем маппинг для этой услуги
                staffs = response.json()
                if staffs:
                    self.service_staffs_map[service['id']] = staffs
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(6)
    def get_free_days(self):
        """Получение свободных дней для сотрудника"""
        if not self.services or not self.service_staffs_map:
            return
        
        # Выбираем услугу, для которой есть сотрудники
        available_services = [s for s in self.services if s['id'] in self.service_staffs_map]
        if not available_services:
            return
        
        service = random.choice(available_services)
        staff = random.choice(self.service_staffs_map[service['id']])
        
        with self.client.get(
            f"/api/v1/staffs/{staff['id']}/free-days/",
            params={"service_id": service['id']},
            headers={
                "X-API-Key": self.api_key,
                "X-TG-ID": str(random.randint(100000, 999999))
            },
            name="GET /staffs/{id}/free-days/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(5)
    def get_free_slots(self):
        """Получение свободных слотов на конкретную дату"""
        if not self.services or not self.service_staffs_map:
            return
        
        # Выбираем услугу, для которой есть сотрудники
        available_services = [s for s in self.services if s['id'] in self.service_staffs_map]
        if not available_services:
            return
        
        service = random.choice(available_services)
        staff = random.choice(self.service_staffs_map[service['id']])
        
        # Генерируем дату в ближайшие 7 дней
        date = (datetime.now() + timedelta(days=random.randint(1, 7))).strftime("%Y-%m-%d")
        
        with self.client.get(
            f"/api/v1/staffs/{staff['id']}/free-slots/",
            params={"date": date, "service_id": service['id']},
            headers={
                "X-API-Key": self.api_key,
                "X-TG-ID": str(random.randint(100000, 999999))
            },
            name="GET /staffs/{id}/free-slots/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(3)
    def get_or_create_client(self):
        """Получение или создание клиента"""
        tg_id = random.randint(100000, 999999)
        client_name = f"Client_{tg_id}"
        phone = f"+7999{random.randint(1000000, 9999999)}"
        
        with self.client.post(
            "/api/v1/clients/get-or-create/",
            params={
                "tg_id": tg_id,
                "client_name": client_name,
                "phone": phone
            },
            headers={
                "X-API-Key": self.api_key,
                "X-TG-ID": str(tg_id)
            },
            name="POST /clients/get-or-create/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                client_data = response.json()
                if client_data.get('client'):
                    client = client_data['client']
                    # Добавляем business_id для изоляции
                    client['_business_id'] = self.business_id
                    self.clients.append(client)
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(2)
    def create_appointment(self):
        """Создание записи"""
        if not self.services or not self.service_staffs_map or not self.clients:
            return
        
        # Выбираем услугу, для которой есть сотрудники
        available_services = [s for s in self.services if s['id'] in self.service_staffs_map]
        if not available_services:
            return
        
        service = random.choice(available_services)
        
        # КРИТИЧЕСКИ ВАЖНО: Проверяем, что услуга принадлежит этому бизнесу
        if service.get('business_id') != self.business_id:
            return
        
        # Фильтруем только сотрудников этого бизнеса для этой услуги
        staffs_for_service = [
            st for st in self.service_staffs_map[service['id']] 
            if st.get('business_id') == self.business_id
        ]
        if not staffs_for_service:
            return
        
        staff = random.choice(staffs_for_service)
        
        # Фильтруем только клиентов этого бизнеса
        my_clients = [c for c in self.clients if c.get('_business_id') == self.business_id]
        if not my_clients:
            return
        
        client = random.choice(my_clients)
        
        # Генерируем валидное время записи в рабочие часы (09:00-20:00 локального времени)
        # Выбираем случайный день в будущем (1-7 дней)
        future_date = datetime.utcnow().date() + timedelta(days=random.randint(1, 7))
        # Выбираем случайный час в рабочее время (09:00-19:00, чтобы запись поместилась до 20:00)
        work_hour = random.randint(9, 19)
        # Выбираем минуты (0 или 30 для ровных слотов)
        work_minute = random.choice([0, 30])
        
        # Создаем локальное время
        local_time = datetime.combine(future_date, datetime.min.time().replace(hour=work_hour, minute=work_minute))
        # Конвертируем в UTC (вычитаем TIMEZONE_OFFSET = 3 часа)
        start_time = local_time - timedelta(hours=3)
        end_time = start_time + timedelta(minutes=service['duration_minutes'])
        
        appointment_data = {
            "client_id": client['id'],
            "client_name": client['name'],
            "staff_id": staff['id'],
            "service_id": service['id'],
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z"
        }
        
        with self.client.post(
            "/api/v1/appointments/create/",
            json=appointment_data,
            headers={
                "X-API-Key": self.api_key,
                "X-TG-ID": str(client.get('tg_id', random.randint(100000, 999999)))
            },
            name="POST /appointments/create/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(4)
    def get_client_appointments(self):
        """Получение записей клиента"""
        if not self.clients:
            return
        
        # Фильтруем только клиентов этого бизнеса
        my_clients = [c for c in self.clients if c.get('_business_id') == self.business_id]
        if not my_clients:
            return
        
        client = random.choice(my_clients)
        
        with self.client.get(
            f"/api/v1/clients/{client['id']}/appointments/",
            headers={
                "X-API-Key": self.api_key,
                "X-TG-ID": str(client.get('tg_id', random.randint(100000, 999999)))
            },
            name="GET /clients/{id}/appointments/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(1)
    def get_events(self):
        """Получение событий (для бота)"""
        with self.client.get(
            "/api/v1/events/",
            headers={"X-API-Key": self.api_key},
            name="GET /events/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")


class AdminUser(HttpUser):
    """
    Симулирует работу админов (владельцев бизнесов).
    Делает запросы к админским endpoints.
    """
    
    wait_time = between(3, 8)  # Админы делают запросы реже
    
    # Вес этого класса меньше, чем у TelegramBotUser
    weight = 1
    
    def on_start(self):
        """Инициализация при старте админа"""
        # Проверяем, что API ключи загружены
        if not API_KEYS:
            print("❌ API ключи не загружены! Запустите: python tests/prepare_test_data.py")
            self.environment.runner.quit()
            return
        
        # Выбираем случайный бизнес из доступных
        available_business_ids = list(API_KEYS.keys())
        self.business_id = random.choice(available_business_ids)
        self.api_key = API_KEYS[self.business_id]
    
    @task(5)
    def get_appointments(self):
        """Получение всех записей"""
        with self.client.get(
            "/admin/appointments/",
            headers={"X-API-Key": self.api_key},
            name="GET /admin/appointments/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(3)
    def get_unmarked_appointments(self):
        """Получение неотмеченных записей"""
        with self.client.get(
            "/admin/appointments/unmarked/",
            headers={"X-API-Key": self.api_key},
            name="GET /admin/appointments/unmarked/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(2)
    def get_appointment_history(self):
        """Получение истории записей"""
        with self.client.get(
            "/admin/appointments/history/",
            headers={"X-API-Key": self.api_key},
            name="GET /admin/appointments/history/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(2)
    def get_staffs(self):
        """Получение списка сотрудников"""
        with self.client.get(
            "/admin/staffs/",
            headers={"X-API-Key": self.api_key},
            name="GET /admin/staffs/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(2)
    def get_services(self):
        """Получение списка услуг"""
        with self.client.get(
            "/admin/services/",
            headers={"X-API-Key": self.api_key},
            name="GET /admin/services/",
            catch_response=True,
            context={'business_id': self.business_id}
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")


# Настройка весов для разных типов пользователей
# TelegramBotUser будет в 10 раз чаще, чем AdminUser
TelegramBotUser.weight = 10
AdminUser.weight = 1
