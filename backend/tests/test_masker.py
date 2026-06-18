"""Тесты маскирования найденных значений."""

from app.detection.masker import mask_value


class TestMasker:
    def test_passport(self):
        assert mask_value("4507 123456", "passport") == "45** ***456"

    def test_snils(self):
        assert mask_value("112-233-445 95", "snils") == "112-***-*** 95"

    def test_inn_person(self):
        result = mask_value("500100732259", "inn_person")
        assert result.startswith("5001")
        assert result.endswith("59")
        assert "*" in result

    def test_bank_card(self):
        assert mask_value("4111111111111111", "bank_card") == "4111 **** **** 1111"

    def test_phone(self):
        assert mask_value("+7 (999) 123-45-67", "phone") == "+7 (9**) ***-**-67"

    def test_email_short_local(self):
        result = mask_value("ab@example.com", "email")
        assert result == "***@example.com"

    def test_email_normal_local(self):
        result = mask_value("ivanov@example.com", "email")
        assert result == "iv***@example.com"

    def test_date_of_birth(self):
        assert mask_value("15.03.1985", "date_of_birth") == "**.**.****"
