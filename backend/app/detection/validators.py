"""
Валидаторы контрольных сумм для структурированных ПДн.
Алгоритмы из раздела 4.2 документации.
"""

import re


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def validate_snils(value: str) -> bool:
    d = _digits(value)
    if len(d) != 11:
        return False
    number = [int(c) for c in d[:9]]
    checksum = int(d[9:11])
    total = sum(number[i] * (9 - i) for i in range(9))
    remainder = total % 101
    if remainder == 100:
        return checksum == 0
    return checksum == remainder


def validate_inn_person(value: str) -> bool:
    d = _digits(value)
    if len(d) != 12:
        return False
    k1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    k2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    c11 = sum(int(d[i]) * k1[i] for i in range(10)) % 11 % 10
    c12 = sum(int(d[i]) * k2[i] for i in range(11)) % 11 % 10
    return int(d[10]) == c11 and int(d[11]) == c12


def validate_inn_org(value: str) -> bool:
    d = _digits(value)
    if len(d) != 10:
        return False
    k = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    c10 = sum(int(d[i]) * k[i] for i in range(9)) % 11 % 10
    return int(d[9]) == c10


def validate_inn(value: str) -> bool:
    d = _digits(value)
    if len(d) == 12:
        return validate_inn_person(value)
    if len(d) == 10:
        return validate_inn_org(value)
    return False


def validate_luhn(value: str) -> bool:
    d = _digits(value)
    if len(d) < 13 or len(d) > 19:
        return False
    total = 0
    for i, digit in enumerate(reversed(d)):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0
