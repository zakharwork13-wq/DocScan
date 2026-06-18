"""Тесты валидаторов контрольных сумм."""

from app.detection.validators import (
    validate_inn_org,
    validate_inn_person,
    validate_luhn,
    validate_snils,
)


class TestSnils:
    def test_valid_snils(self):
        # Реальные тестовые номера СНИЛС (рассчитаны корректно)
        assert validate_snils("112-233-445 95") is True

    def test_invalid_snils_wrong_checksum(self):
        assert validate_snils("112-233-445 00") is False

    def test_invalid_snils_wrong_length(self):
        assert validate_snils("123-456") is False

    def test_snils_without_separators(self):
        assert validate_snils("11223344595") is True


class TestInnPerson:
    def test_valid_inn(self):
        # Известный валидный ИНН (12 цифр)
        assert validate_inn_person("500100732259") is True

    def test_invalid_inn(self):
        assert validate_inn_person("123456789012") is False

    def test_wrong_length(self):
        assert validate_inn_person("12345") is False


class TestInnOrg:
    def test_valid_inn_org(self):
        # ОАО "Газпром" — реальный ИНН для теста
        assert validate_inn_org("7736050003") is True

    def test_invalid_inn_org(self):
        assert validate_inn_org("1234567890") is False


class TestLuhn:
    def test_visa_test_card(self):
        # Тестовая Visa
        assert validate_luhn("4111111111111111") is True

    def test_mastercard_test(self):
        # Тестовая Mastercard
        assert validate_luhn("5555555555554444") is True

    def test_invalid_card(self):
        assert validate_luhn("1234567890123456") is False

    def test_with_spaces(self):
        assert validate_luhn("4111 1111 1111 1111") is True

    def test_too_short(self):
        assert validate_luhn("1234") is False
