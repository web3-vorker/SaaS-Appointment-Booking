# Нагрузочное тестирование SaaS Appointment Booking System

## Описание

Набор тестов для проверки производительности backend под высокой нагрузкой. Симулирует работу 100 Telegram ботов, делающих одновременные запросы к API.

## Что тестируется

### Сценарии клиентов (90% нагрузки):
- Получение списка услуг
- Получение мастеров для услуги
- Получение свободных дней
- Получение свободных слотов
- Создание/получение клиентов
- Создание записей
- Получение записей клиента
- Получение событий

### Сценарии админов (10% нагрузки):
- Получение всех записей
- Получение неотмеченных записей
- Получение истории записей
- Получение списка сотрудников
- Получение списка услуг

## Установка

1. Установите зависимости:
```bash
pip install locust aiohttp
```

2. Убедитесь, что backend запущен:
```bash
python -m app.main
```

3. Убедитесь, что Redis запущен (для rate limiting)

## Подготовка тестовых данных

Перед запуском тестов нужно создать тестовые данные:

```bash
# Откройте tests/prepare_test_data.py и укажите ваш DEVELOPER_KEY
# Затем запустите:
python tests/prepare_test_data.py
```

Это создаст:
- 10 тестовых бизнесов
- 50 сотрудников (по 5 на бизнес)
- 100 услуг (по 10 на бизнес)
- Привязки услуг к сотрудникам

## Запуск тестов

### Вариант 1: С веб-интерфейсом (рекомендуется)

```bash
locust -f tests/load_test.py --host=http://localhost:8000
```

Затем откройте браузер: http://localhost:8089

Настройки для теста:
- **Number of users:** 100 (симулирует 100 ботов)
- **Spawn rate:** 10 (добавлять по 10 пользователей в секунду)
- **Host:** http://localhost:8000

### Вариант 2: Headless режим (без интерфейса)

```bash
locust -f tests/load_test.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --html=load_test_report.html
```

Параметры:
- `--users 100` - количество одновременных пользователей
- `--spawn-rate 10` - скорость добавления пользователей (10/сек)
- `--run-time 5m` - длительность теста (5 минут)
- `--html=load_test_report.html` - сохранить HTML отчет

### Вариант 3: Короткий тест для быстрой проверки

```bash
locust -f tests/load_test.py \
    --host=http://localhost:8000 \
    --users 20 \
    --spawn-rate 5 \
    --run-time 1m \
    --html=quick_test.html
```

## Интерпретация результатов

### В веб-интерфейсе Locust:

**Statistics:**
- **Requests** - общее количество запросов
- **Fails** - количество ошибок
- **Median** - медианное время ответа (50% запросов быстрее)
- **95%ile** - 95-й перцентиль (95% запросов быстрее)
- **Average** - среднее время ответа
- **RPS** - запросов в секунду

**Charts:**
- **Total Requests per Second** - пропускная способность
- **Response Times** - время ответа (медиана и 95-й перцентиль)
- **Number of Users** - количество активных пользователей

### В консоли (кастомная аналитика):

После завершения теста выводится детальный отчет:

```
📊 ОБЩАЯ СТАТИСТИКА:
  Всего запросов: 15000
  ✅ Успешных: 14850 (99.00%)
  ❌ Ошибок: 150 (1.00%)

⏱️  ВРЕМЯ ОТВЕТА:
  Среднее: 45.23 мс
  Минимальное: 12.45 мс
  Максимальное: 523.67 мс

📈 СТАТИСТИКА ПО ТИПАМ ЗАПРОСОВ:
  GET /services/:
    Запросов: 3000
    Успешных: 2985 (99.5%)
    Среднее время: 23.45 мс
  ...

🏢 СТАТИСТИКА ПО БИЗНЕСАМ:
  Бизнес #1:
    Запросов: 1523
    Успешных: 1510 (99.1%)
  ...

❌ ОШИБКИ:
  Rate limit exceeded: 120
  Status: 500: 30
```

## Что считается хорошим результатом

### Для production-ready системы:

**Время ответа:**
- ✅ Среднее < 100 мс - отлично
- ⚠️ Среднее 100-300 мс - приемлемо
- ❌ Среднее > 300 мс - требуется оптимизация

**Успешность запросов:**
- ✅ > 99% - отлично
- ⚠️ 95-99% - приемлемо
- ❌ < 95% - требуется исправление

**Пропускная способность:**
- ✅ > 100 RPS - отлично для малого/среднего бизнеса
- ✅ > 500 RPS - отлично для крупного бизнеса
- ⚠️ < 50 RPS - может быть недостаточно

**Rate limiting:**
- ✅ < 5% запросов с 429 - нормально
- ⚠️ 5-10% запросов с 429 - возможно, лимиты слишком строгие
- ❌ > 10% запросов с 429 - лимиты слишком строгие

## Типичные проблемы и решения

### 1. Много ошибок 429 (Rate Limit)

**Проблема:** Redis rate limiting слишком строгий

**Решение:**
- Увеличьте лимиты в `app/redis/limiter.py`
- Или уменьшите количество пользователей в тесте

### 2. Высокое время ответа (> 500 мс)

**Возможные причины:**
- Медленные запросы к БД (нужны индексы)
- Недостаточно соединений в пуле БД
- Блокирующие операции в async коде

**Решение:**
- Проверьте логи PostgreSQL на медленные запросы
- Добавьте индексы для часто используемых запросов
- Увеличьте размер пула соединений

### 3. Ошибки 500 (Internal Server Error)

**Проблема:** Ошибки в коде backend

**Решение:**
- Проверьте логи backend: `python -m app.main`
- Исправьте найденные ошибки
- Добавьте обработку edge cases

### 4. Connection errors

**Проблема:** Backend не справляется с количеством соединений

**Решение:**
- Увеличьте `worker_connections` в uvicorn
- Запустите несколько инстансов backend за load balancer
- Используйте gunicorn с несколькими workers

## Мониторинг во время теста

### 1. Мониторинг backend:

```bash
# В отдельном терминале
python -m app.main
```

Следите за логами на наличие ошибок.

### 2. Мониторинг PostgreSQL:

```bash
# Подключитесь к PostgreSQL
psql -U your_user -d your_database

# Посмотрите активные запросы
SELECT pid, query, state, query_start 
FROM pg_stat_activity 
WHERE state != 'idle' 
ORDER BY query_start;

# Посмотрите медленные запросы
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

### 3. Мониторинг Redis:

```bash
redis-cli INFO stats
redis-cli MONITOR  # Показывает все команды в реальном времени
```

### 4. Мониторинг системных ресурсов:

**Windows:**
```powershell
# CPU и память
Get-Process python | Select-Object CPU, WorkingSet, ProcessName
```

**Linux/Mac:**
```bash
# CPU и память
top -p $(pgrep -f "python.*app.main")

# Сетевые соединения
netstat -an | grep :8000 | wc -l
```

## Оптимизация после тестирования

### Если время ответа высокое:

1. **Добавьте индексы в БД:**
```sql
-- Проверьте, какие запросы медленные
EXPLAIN ANALYZE SELECT ...;

-- Добавьте нужные индексы
CREATE INDEX idx_name ON table_name(column_name);
```

2. **Включите кэширование:**
- Кэшируйте список услуг/сотрудников
- Используйте Redis для кэширования свободных слотов

3. **Оптимизируйте запросы:**
- Используйте `selectinload` для eager loading
- Избегайте N+1 проблем
- Используйте `select` вместо `filter`

### Если много ошибок:

1. **Добавьте retry логику:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def make_request():
    ...
```

2. **Улучшите обработку ошибок:**
- Добавьте try/except блоки
- Логируйте все ошибки
- Возвращайте понятные сообщения об ошибках

3. **Добавьте валидацию:**
- Проверяйте входные данные
- Используйте Pydantic схемы
- Добавьте проверки на существование записей

## Очистка после тестирования

После завершения тестов удалите тестовые данные:

```bash
python tests/prepare_test_data.py cleanup
```

Это удалит все 10 тестовых бизнесов и связанные данные.

## Расширенные сценарии

### Тест на выносливость (Endurance Test)

Проверка стабильности при длительной работе:

```bash
locust -f tests/load_test.py \
    --host=http://localhost:8000 \
    --users 50 \
    --spawn-rate 5 \
    --run-time 30m \
    --html=endurance_test.html
```

### Стресс-тест (Stress Test)

Проверка максимальной нагрузки:

```bash
locust -f tests/load_test.py \
    --host=http://localhost:8000 \
    --users 500 \
    --spawn-rate 50 \
    --run-time 5m \
    --html=stress_test.html
```

### Spike Test

Проверка поведения при резком скачке нагрузки:

```bash
# Запустите с 10 пользователями
# Затем в веб-интерфейсе резко увеличьте до 200
# Наблюдайте за поведением системы
```

## Автоматизация тестирования

Создайте скрипт для автоматического запуска тестов:

```bash
# run_load_tests.sh
#!/bin/bash

echo "Подготовка тестовых данных..."
python tests/prepare_test_data.py

echo "Запуск нагрузочного теста..."
locust -f tests/load_test.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --html=reports/load_test_$(date +%Y%m%d_%H%M%S).html \
    --csv=reports/load_test_$(date +%Y%m%d_%H%M%S)

echo "Очистка тестовых данных..."
python tests/prepare_test_data.py cleanup

echo "Тестирование завершено!"
```

## CI/CD интеграция

Добавьте нагрузочные тесты в CI/CD pipeline:

```yaml
# .github/workflows/load-test.yml
name: Load Testing

on:
  schedule:
    - cron: '0 2 * * *'  # Каждую ночь в 2:00
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install locust aiohttp
      
      - name: Start services
        run: |
          docker-compose up -d
          sleep 10
      
      - name: Prepare test data
        run: python tests/prepare_test_data.py
      
      - name: Run load test
        run: |
          locust -f tests/load_test.py \
            --host=http://localhost:8000 \
            --users 100 \
            --spawn-rate 10 \
            --run-time 5m \
            --html=load_test_report.html \
            --headless
      
      - name: Upload report
        uses: actions/upload-artifact@v2
        with:
          name: load-test-report
          path: load_test_report.html
      
      - name: Cleanup
        run: python tests/prepare_test_data.py cleanup
```

## Полезные ссылки

- [Locust документация](https://docs.locust.io/)
- [FastAPI Performance](https://fastapi.tiangolo.com/deployment/concepts/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Redis Performance](https://redis.io/topics/benchmarks)

---

**Последнее обновление:** 2026-05-10
