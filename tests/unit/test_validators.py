"""
Unit тесты для app/utils/validators.py

Тестируем валидацию и нормализацию российских телефонных номеров.
Зависимостей нет — чистые unit тесты.
"""

import pytest
from fastapi import HTTPException

from app.utils.validators import validate_phone


class TestValidatePhone:
    """Тесты функции validate_phone."""

    # ──────────────────────────────────────────────
    # Корректные форматы
    # ──────────────────────────────────────────────

    def test_format_with_plus_7(self):
        """Номер +79991234567 → +79991234567 (без изменений)."""
        assert validate_phone("+79991234567") == "+79991234567"

    def test_format_starting_with_8(self):
        """Номер 89991234567 → +79991234567 (замена 8 на +7)."""
        assert validate_phone("89991234567") == "+79991234567"

    def test_format_starting_with_7(self):
        """Номер 79991234567 → +79991234567 (добавление +)."""
        assert validate_phone("79991234567") == "+79991234567"

    def test_format_10_digits(self):
        """10-значный номер 9991234567 → +79991234567 (добавление +7)."""
        assert validate_phone("9991234567") == "+79991234567"

    def test_phone_with_spaces_and_dashes(self):
        """+7 (999) 123-45-67 → нормализуется корректно."""
        result = validate_phone("+7 (999) 123-45-67")
        assert result == "+79991234567"

    def test_phone_with_spaces(self):
        """Пробелы убираются перед валидацией."""
        result = validate_phone("+7 999 123 45 67")
        assert result == "+79991234567"

    # ──────────────────────────────────────────────
    # Пустое значение
    # ──────────────────────────────────────────────

    def test_empty_phone_raises_400(self):
        """Пустая строка → HTTPException 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_phone("")
        assert exc_info.value.status_code == 400

    def test_none_raises_400(self):
        """None → HTTPException 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_phone(None)
        assert exc_info.value.status_code == 400

    # ──────────────────────────────────────────────
    # Невалидные форматы
    # ──────────────────────────────────────────────

    def test_too_short_raises_400(self):
        """Слишком короткий номер → HTTPException 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_phone("12345")
        assert exc_info.value.status_code == 400

    def test_too_long_raises_400(self):
        """Слишком длинный номер → HTTPException 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_phone("+7999123456789999")
        assert exc_info.value.status_code == 400

    def test_letters_raises_400(self):
        """Номер с буквами → HTTPException 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_phone("abc1234567")
        assert exc_info.value.status_code == 400

    def test_only_plus_raises_400(self):
        """Только символ + → HTTPException 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_phone("+")
        assert exc_info.value.status_code == 400

    # ──────────────────────────────────────────────
    # Возвращаемый тип
    # ──────────────────────────────────────────────

    def test_returns_string(self):
        """Результат всегда строка."""
        result = validate_phone("+79991234567")
        assert isinstance(result, str)

    def test_normalized_starts_with_plus(self):
        """Нормализованный номер всегда начинается с +."""
        result = validate_phone("89991234567")
        assert result.startswith("+")