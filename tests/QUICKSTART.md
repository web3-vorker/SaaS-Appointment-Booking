# Быстрый старт нагрузочного тестирования

## Шаг 1: Установка зависимостей

```bash
pip install locust aiohttp
```

## Шаг 2: Настройка

Откройте `tests/prepare_test_data.py` и укажите ваш `DEVELOPER_KEY`:

```python
DEVELOPER_KEY = "your-developer-key-here"  # Замените на ваш ключ из .env
```

## Шаг 3: Запуск backend и Redis

```bash
# Терминал 1: Backend
python -m app.main

# Терминал 2: Redis (должен быть запущен)
redis-server
```

## Шаг 4: Подготовка тестовых данных

```bash
python tests/prepare_test_data.py
```

Это создаст 10 тестовых бизнесов с сотрудниками и услугами.

## Шаг 5: Запуск теста

### Вариант A: С веб-интерфейсом

```bash
locust -f tests/load_test.py --host=http://localhost:8000
```
```bash
locust -f tests/load_test.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 1m --html=report.html
```

Откройте http://localhost:8089 и настройте:
- Users: 100
- Spawn rate: 10
- Нажмите "Start swarming"

### Вариант B: Headless (без интерфейса)

```bash
locust -f tests/load_test.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 5m --html=report.html
```

## Шаг 6: Анализ результатов

После завершения теста:
1. В консоли появится детальный отчет с аналитикой
2. Откройте `report.html` в браузере для визуализации

## Шаг 7: Очистка

```bash
python tests/prepare_test_data.py cleanup
```

---

## Быстрый тест (1 минута, 20 пользователей)

```bash
# Подготовка
python tests/prepare_test_data.py

# Тест
locust -f tests/load_test.py --host=http://localhost:8000 --users 20 --spawn-rate 5 --run-time 1m --html=quick_test.html

# Очистка
python tests/prepare_test_data.py cleanup
```

---

## Что смотреть в результатах

✅ **Хорошо:**
- Среднее время ответа < 100 мс
- Успешность > 99%
- RPS > 100

⚠️ **Требует внимания:**
- Среднее время ответа 100-300 мс
- Успешность 95-99%
- Много ошибок 429 (rate limit)

❌ **Плохо:**
- Среднее время ответа > 300 мс
- Успешность < 95%
- Ошибки 500 (internal server error)

---

Подробная документация: `tests/README.md`
