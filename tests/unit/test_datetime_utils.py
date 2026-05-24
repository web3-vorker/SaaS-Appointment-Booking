"""
Unit тесты для app/utils/datetime_utils.py

Тестируем утилиты работы с naive UTC datetime.
"""

import pytest
from datetime import datetime, timezone, timedelta

from app.utils.datetime_utils import now_utc, to_naive_utc


class TestNowUtc:
    """Тесты функции now_utc()."""

    def test_returns_datetime(self):
        """Возвращает объект datetime."""
        result = now_utc()
        assert isinstance(result, datetime)

    def test_is_naive(self):
        """Результат не содержит timezone info (naive)."""
        result = now_utc()
        assert result.tzinfo is None

    def test_approximately_current_time(self):
        """Время близко к текущему UTC (±2 секунды)."""
        result = now_utc()
        expected = datetime.now(timezone.utc).replace(tzinfo=None)
        delta = abs((result - expected).total_seconds())
        assert delta < 2

    def test_consecutive_calls_increase(self):
        """Каждый вызов возвращает время не меньше предыдущего."""
        t1 = now_utc()
        t2 = now_utc()
        assert t2 >= t1


class TestToNaiveUtc:
    """Тесты функции to_naive_utc()."""

    def test_none_returns_none(self):
        """None → None."""
        assert to_naive_utc(None) is None

    def test_naive_datetime_returned_unchanged(self):
        """Naive datetime возвращается как есть."""
        dt = datetime(2025, 6, 15, 12, 0, 0)
        result = to_naive_utc(dt)
        assert result == dt
        assert result.tzinfo is None

    def test_aware_utc_becomes_naive(self):
        """Aware UTC datetime → naive datetime (те же значения)."""
        dt_aware = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = to_naive_utc(dt_aware)
        assert result.tzinfo is None
        assert result == datetime(2025, 6, 15, 12, 0, 0)

    def test_aware_offset_converted_to_utc(self):
        """Aware datetime с UTC+3 → naive UTC (вычитаем 3 часа)."""
        utc_plus_3 = timezone(timedelta(hours=3))
        dt_aware = datetime(2025, 6, 15, 15, 0, 0, tzinfo=utc_plus_3)  # 15:00 UTC+3 = 12:00 UTC
        result = to_naive_utc(dt_aware)
        assert result.tzinfo is None
        assert result == datetime(2025, 6, 15, 12, 0, 0)

    def test_result_is_naive(self):
        """Результат всегда naive."""
        dt_aware = datetime.now(timezone.utc)
        result = to_naive_utc(dt_aware)
        assert result.tzinfo is None

    def test_preserves_microseconds(self):
        """Микросекунды сохраняются."""
        dt = datetime(2025, 6, 15, 12, 30, 45, 123456)
        result = to_naive_utc(dt)
        assert result.microsecond == 123456