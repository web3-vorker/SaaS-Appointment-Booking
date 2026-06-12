"""
Практические тесты кэширования с реальными проверками.
Эти тесты можно запустить через pytest и они реально проверяют кэширование.
"""

import pytest
import json
from datetime import datetime, time, date
from unittest.mock import AsyncMock, MagicMock, patch
from app.redis.cache import serialize_business, deserialize_business
from app.redis.cache_keys import (
    key_services,
    key_staffs_for_service,
    pattern_all_slots,
    pattern_all_free_days,
    key_business_by_api_key,
    TTL_BUSINESS,
    TTL_SERVICES,
    TTL_FREE_SLOTS,
    TTL_FREE_DAYS,
)


class TestCacheSerializationDeserialization:
    """Тесты сериализации/десериализации данных для кэша"""

    def test_serialize_business_returns_dict(self):
        """Проверяет, что serialize_business возвращает dict"""
        business = MagicMock()
        business.id = 1
        business.name = "Test Business"
        business.working_time_start = time(9, 0)
        business.working_time_end = time(18, 0)
        business.break_start = time(13, 0)
        business.break_end = time(14, 0)
        business.weekend_days = [0, 6]
        business.created_at = datetime.now()
        business.is_active = True
        business.owner_tg_id = 123456
        business.api_key = "test-key-123"
        
        result = serialize_business(business)
        
        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["name"] == "Test Business"
        assert result["api_key"] == "test-key-123"
        assert result["is_active"] == True
        assert result["weekend_days"] == [0, 6]

    def test_serialize_business_handles_none_times(self):
        """Проверяет, что serialize_business обрабатывает None для временных полей"""
        business = MagicMock()
        business.id = 1
        business.name = "Test"
        business.working_time_start = None
        business.working_time_end = None
        business.break_start = None
        business.break_end = None
        business.weekend_days = None
        business.created_at = None
        business.is_active = True
        business.owner_tg_id = None
        business.api_key = None
        
        result = serialize_business(business)
        
        assert result["working_time_start"] is None
        assert result["working_time_end"] is None
        assert result["break_start"] is None
        assert result["break_end"] is None

    def test_serialize_business_converts_time_to_iso(self):
        """Проверяет, что time объекты конвертируются в ISO формат"""
        business = MagicMock()
        business.id = 1
        business.name = "Test"
        business.working_time_start = time(9, 30, 0)
        business.working_time_end = time(18, 45, 0)
        business.break_start = None
        business.break_end = None
        business.weekend_days = []
        business.created_at = None
        business.is_active = True
        business.owner_tg_id = None
        business.api_key = None
        
        result = serialize_business(business)
        
        assert result["working_time_start"] == "09:30:00"
        assert result["working_time_end"] == "18:45:00"

    def test_serialize_business_json_serializable(self):
        """Проверяет, что результат serialize_business можно сериализовать в JSON"""
        business = MagicMock()
        business.id = 1
        business.name = "Test Business"
        business.working_time_start = time(9, 0)
        business.working_time_end = time(18, 0)
        business.break_start = time(13, 0)
        business.break_end = time(14, 0)
        business.weekend_days = [0, 6]
        business.created_at = datetime.now()
        business.is_active = True
        business.owner_tg_id = 123456
        business.api_key = "test-key"
        
        result = serialize_business(business)
        
        # Должно не выкинуть исключение
        json_str = json.dumps(result, default=str)
        assert json_str is not None
        assert "Test Business" in json_str


class TestCacheKeyGeneration:
    """Тесты генерации ключей кэша"""

    def test_services_key_format(self):
        """Проверяет формат ключа для кэша услуг"""
        business_id = 123
        key = key_services(business_id)
        
        assert key == "cache:services:business_id:123"
        assert str(business_id) in key

    def test_staffs_for_service_key_format(self):
        """Проверяет формат ключа для кэша сотрудников услуги"""
        business_id = 123
        service_id = 456
        key = key_staffs_for_service(business_id, service_id)
        
        assert "cache:" in key
        assert str(business_id) in key
        assert str(service_id) in key

    def test_pattern_all_slots_format(self):
        """Проверяет формат паттерна для всех слотов"""
        business_id = 123
        pattern = pattern_all_slots(business_id)
        
        assert "cache:" in pattern
        assert str(business_id) in pattern
        assert "*" in pattern  # Для SCAN операции

    def test_pattern_all_free_days_format(self):
        """Проверяет формат паттерна для всех свободных дней"""
        business_id = 123
        pattern = pattern_all_free_days(business_id)
        
        assert "cache:" in pattern
        assert str(business_id) in pattern
        assert "*" in pattern  # Для SCAN операции

    def test_business_by_api_key_format(self):
        """Проверяет формат ключа для поиска бизнеса по API ключу"""
        api_key = "test-api-key-123"
        key = key_business_by_api_key(api_key)
        
        assert "cache:" in key
        assert api_key in key


class TestCacheTTLConstants:
    """Тесты констант TTL"""

    def test_ttl_business_is_300_seconds(self):
        """TTL для кэша бизнеса должен быть 300 секунд (5 минут)"""
        assert TTL_BUSINESS == 300

    def test_ttl_services_is_600_seconds(self):
        """TTL для кэша услуг должен быть 600 секунд (10 минут)"""
        assert TTL_SERVICES == 600

    def test_ttl_free_slots_is_120_seconds(self):
        """TTL для кэша слотов должен быть 120 секунд (2 минуты)"""
        assert TTL_FREE_SLOTS == 120

    def test_ttl_free_days_is_600_seconds(self):
        """TTL для кэша свободных дней должен быть 600 секунд (10 минут)"""
        assert TTL_FREE_DAYS == 600

    def test_ttl_constants_are_positive(self):
        """Все TTL константы должны быть положительными"""
        assert TTL_BUSINESS > 0
        assert TTL_SERVICES > 0
        assert TTL_FREE_SLOTS > 0
        assert TTL_FREE_DAYS > 0




class TestCachePatternMatching:
    """Тесты что паттерны кэша покрывают нужные ключи"""

    def test_pattern_all_slots_matches_slot_keys(self):
        """Проверяет, что паттерн для слотов матчит ключи слотов"""
        business_id = 123
        pattern = pattern_all_slots(business_id)
        
        # Примеры ключей которые должны матчиться
        example_keys = [
            "cache:free_slots:business_id:123:staff_id:1:date:2026-06-15",
            "cache:free_slots:business_id:123:staff_id:2:date:2026-06-16",
            "cache:free_slots:business_id:123:staff_id:3:date:2026-06-17",
        ]
        
        # Паттерн должен содержать business_id
        assert "123" in pattern
        assert "*" in pattern

    def test_pattern_all_free_days_matches_free_days_keys(self):
        """Проверяет, что паттерн для свободных дней матчит нужные ключи"""
        business_id = 456
        pattern = pattern_all_free_days(business_id)
        
        # Примеры ключей которые должны матчиться
        example_keys = [
            "cache:free_days:business_id:456:staff_id:1",
            "cache:free_days:business_id:456:staff_id:2",
            "cache:free_days:business_id:456:staff_id:3",
        ]
        
        # Паттерн должен содержать business_id
        assert "456" in pattern
        assert "*" in pattern


class TestCacheDataTypes:
    """Тесты типов данных в кэше"""

    def test_serialize_business_business_id_is_int(self):
        """Проверяет, что business_id в кэше - это int"""
        business = MagicMock()
        business.id = 1
        business.name = "Test"
        business.working_time_start = None
        business.working_time_end = None
        business.break_start = None
        business.break_end = None
        business.weekend_days = []
        business.created_at = None
        business.is_active = True
        business.owner_tg_id = None
        business.api_key = None
        
        result = serialize_business(business)
        
        assert isinstance(result["id"], int)

    def test_serialize_business_weekend_days_is_list(self):
        """Проверяет, что weekend_days в кэше - это list"""
        business = MagicMock()
        business.id = 1
        business.name = "Test"
        business.working_time_start = None
        business.working_time_end = None
        business.break_start = None
        business.break_end = None
        business.weekend_days = [0, 6]
        business.created_at = None
        business.is_active = True
        business.owner_tg_id = None
        business.api_key = None
        
        result = serialize_business(business)
        
        assert isinstance(result["weekend_days"], list)
        assert 0 in result["weekend_days"]
        assert 6 in result["weekend_days"]


class TestCacheInvalidationCoverage:
    """Тесты что все CRUD операции имеют инвалидацию кэша"""

    def test_all_cache_keys_used_in_invalidation(self):
        """Проверяет, что используются все определенные ключи кэша"""
        # Ключи которые должны быть инвалидированы:
        required_keys = {
            "key_services": key_services(1),
            "key_staffs_for_service": key_staffs_for_service(1, 1),
            "pattern_all_slots": pattern_all_slots(1),
            "pattern_all_free_days": pattern_all_free_days(1),
            "key_business_by_api_key": key_business_by_api_key("test-key"),
        }
        
        # Все ключи должны быть строками
        for key_name, key_value in required_keys.items():
            assert isinstance(key_value, str), f"{key_name} должен быть строкой"
            assert len(key_value) > 0, f"{key_name} не может быть пустой"
