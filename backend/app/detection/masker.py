"""Маскирование найденных значений перед сохранением в БД."""

import re


def mask_value(value: str, finding_type: str) -> str:
    d = re.sub(r"\D", "", value)
    match finding_type:
        case "passport":
            # 4507 123456 → 45** ***456
            if len(d) == 10:
                return f"{d[:2]}** ***{d[7:]}"
        case "snils":
            # 123-456-789 01 → 123-***-*** 01
            if len(d) == 11:
                return f"{d[:3]}-***-*** {d[9:]}"
        case "inn_person" | "inn_org":
            # оставляем первые 4 и последние 2
            if len(d) >= 6:
                return d[:4] + "*" * (len(d) - 6) + d[-2:]
        case "bank_card":
            # 4111 1111 1111 1111 → 4111 **** **** 1111
            if len(d) >= 8:
                return f"{d[:4]} **** **** {d[-4:]}"
        case "phone":
            # +7 (999) 123-45-67 → +7 (9**) ***-**-67
            if len(d) >= 10:
                return f"+7 ({d[-10]}**) ***-**-{d[-2:]}"
        case "email":
            parts = value.split("@")
            if len(parts) == 2:
                local = parts[0]
                masked_local = local[:2] + "***" if len(local) > 2 else "***"
                return f"{masked_local}@{parts[1]}"
        case "date_of_birth":
            return "**.**.****"
        case _:
            # По умолчанию: показываем первые 2 и последние 2 символа
            if len(value) > 6:
                return value[:2] + "*" * (len(value) - 4) + value[-2:]
    return "***"
