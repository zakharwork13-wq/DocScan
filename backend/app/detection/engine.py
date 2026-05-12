"""
Движок детекции персональных данных.

Текущее состояние: базовые regex-правила для всех типов ПДн из ТЗ.
Этап 3 роадмапа добавит: морфологический анализ ФИО/адресов через pymorphy3,
контекстный анализатор, полную систему уверенности.
"""

import re
from typing import Any

from .rules import BUILTIN_RULES
from .validators import validate_snils, validate_inn, validate_luhn
from .masker import mask_value


class DetectionEngine:
    def __init__(self) -> None:
        self.rules = BUILTIN_RULES

    def scan(self, text: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        for rule in self.rules:
            for match in re.finditer(rule["pattern"], text, re.IGNORECASE):
                raw = match.group(0)
                confidence = rule["base_confidence"]

                # Валидация контрольной суммы
                if rule.get("validator"):
                    if not rule["validator"](raw):
                        confidence -= 0.5
                if confidence <= 0:
                    continue

                # Контекстный анализ
                window_start = max(0, match.start() - 50)
                window_end = min(len(text), match.end() + 50)
                context = text[window_start:window_end]

                for kw in rule.get("positive_keywords", []):
                    if kw.lower() in context.lower():
                        confidence = min(1.0, confidence + 0.1)
                for kw in rule.get("negative_keywords", []):
                    if kw.lower() in context.lower():
                        confidence = max(0.0, confidence - 0.1)

                if confidence < 0.5:
                    continue

                findings.append({
                    "finding_type": rule["finding_type"],
                    "masked_value": mask_value(raw, rule["finding_type"]),
                    "position_start": match.start(),
                    "position_end": match.end(),
                    "confidence": round(confidence, 2),
                    "context_masked": mask_value(context, rule["finding_type"]),
                })

        return findings

    def classify(self, findings: list[dict]) -> str:
        types = {f["finding_type"] for f in findings}

        if not types:
            return "public"

        strict_types = {"passport", "snils", "inn_person", "bank_card", "oms_policy", "driver_license"}
        contact_only = {"phone", "email"}

        if types & strict_types:
            # Строго конфиденциальный: комбинация паспорт+ФИО или медицинские данные
            if "passport" in types and ("fio" in types or "address" in types):
                return "strict"
            return "confidential"

        if types <= contact_only:
            return "internal"

        return "confidential"
