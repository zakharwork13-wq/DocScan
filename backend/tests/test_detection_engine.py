"""Тесты движка детекции ПДн."""

from app.detection.engine import DetectionEngine


class TestDetectionEngine:
    def setup_method(self):
        self.engine = DetectionEngine()

    def test_email_detection(self):
        findings = self.engine.scan("Свяжитесь со мной: ivan@example.com")
        types = {f["finding_type"] for f in findings}
        assert "email" in types

    def test_phone_detection(self):
        findings = self.engine.scan("Телефон: +7 (999) 123-45-67")
        types = {f["finding_type"] for f in findings}
        assert "phone" in types

    def test_bank_card_with_keyword(self):
        # С позитивным контекстом — должна найтись
        findings = self.engine.scan("Номер карты: 4111 1111 1111 1111")
        types = {f["finding_type"] for f in findings}
        assert "bank_card" in types

    def test_invalid_card_filtered_by_luhn(self):
        # Карта с неправильной контрольной суммой не должна пройти
        findings = self.engine.scan("Карта: 1234 5678 9012 3456")
        cards = [f for f in findings if f["finding_type"] == "bank_card"]
        # Либо нет вообще, либо с пониженной уверенностью
        for c in cards:
            assert c["confidence"] < 0.85

    def test_passport_with_context(self):
        text = "Паспорт 4507 123456 выдан 01.01.2020"
        findings = self.engine.scan(text)
        types = {f["finding_type"] for f in findings}
        assert "passport" in types

    def test_no_false_positives_in_plain_text(self):
        # Простой текст без ПДн
        findings = self.engine.scan("Это обычный текст без секретов.")
        assert len(findings) == 0

    def test_masking_applied(self):
        findings = self.engine.scan("Email: test@example.com")
        for f in findings:
            # В маске не должно быть полного email
            assert "test@example.com" not in f["masked_value"]

    def test_position_recorded(self):
        text = "Email: ivan@test.ru"
        findings = self.engine.scan(text)
        for f in findings:
            assert f["position_start"] is not None
            assert f["position_end"] is not None
            assert f["position_end"] > f["position_start"]


class TestClassification:
    def setup_method(self):
        self.engine = DetectionEngine()

    def test_public_no_findings(self):
        assert self.engine.classify([]) == "public"

    def test_internal_only_email(self):
        findings = [{"finding_type": "email"}]
        assert self.engine.classify(findings) == "internal"

    def test_internal_email_and_phone(self):
        findings = [{"finding_type": "email"}, {"finding_type": "phone"}]
        assert self.engine.classify(findings) == "internal"

    def test_confidential_with_passport(self):
        findings = [{"finding_type": "passport"}]
        assert self.engine.classify(findings) == "confidential"

    def test_strict_passport_with_fio(self):
        findings = [{"finding_type": "passport"}, {"finding_type": "fio"}]
        assert self.engine.classify(findings) == "strict"

    def test_confidential_with_bank_card(self):
        findings = [{"finding_type": "bank_card"}]
        assert self.engine.classify(findings) == "confidential"
