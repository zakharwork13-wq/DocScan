"""
Встроенные правила детекции ПДн граждан РФ.
Паттерны соответствуют разделу 4.2 документации.
"""

from .validators import validate_snils, validate_inn_person, validate_inn_org, validate_luhn

BUILTIN_RULES = [
    {
        "code": "passport_rf",
        "finding_type": "passport",
        "pattern": r"\b\d{4}[\s\-]\d{6}\b",
        "base_confidence": 0.6,
        "validator": None,
        "positive_keywords": ["паспорт", "серия", "удостоверение личности", "выдан"],
        "negative_keywords": ["договор", "счёт", "акт", "№"],
    },
    {
        "code": "snils",
        "finding_type": "snils",
        "pattern": r"\b\d{3}[\s\-]\d{3}[\s\-]\d{3}[\s\-]\d{2}\b",
        "base_confidence": 0.8,
        "validator": validate_snils,
        "positive_keywords": ["снилс", "страховое свидетельство", "пфр", "пенсионный"],
        "negative_keywords": [],
    },
    {
        "code": "inn_person",
        "finding_type": "inn_person",
        "pattern": r"\b\d{12}\b",
        "base_confidence": 0.7,
        "validator": validate_inn_person,
        "positive_keywords": ["инн", "налогоплательщик", "налоговый номер"],
        "negative_keywords": [],
    },
    {
        "code": "inn_org",
        "finding_type": "inn_org",
        "pattern": r"\b\d{10}\b",
        "base_confidence": 0.6,
        "validator": validate_inn_org,
        "positive_keywords": ["инн", "ооо", "ао", "ип", "организация"],
        "negative_keywords": [],
    },
    {
        "code": "bank_card",
        "finding_type": "bank_card",
        "pattern": r"\b(?:\d{4}[\s\-]){3}\d{4}\b",
        "base_confidence": 0.8,
        "validator": validate_luhn,
        "positive_keywords": ["карта", "номер карты", "оплата", "pan"],
        "negative_keywords": [],
    },
    {
        "code": "phone_rf",
        "finding_type": "phone",
        "pattern": r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",
        "base_confidence": 0.8,
        "validator": None,
        "positive_keywords": ["тел", "телефон", "моб", "звонок"],
        "negative_keywords": [],
    },
    {
        "code": "email",
        "finding_type": "email",
        "pattern": r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
        "base_confidence": 0.9,
        "validator": None,
        "positive_keywords": [],
        "negative_keywords": ["example.com", "test.ru", "noreply"],
    },
    {
        "code": "date_of_birth",
        "finding_type": "date_of_birth",
        "pattern": r"\b(?:0?[1-9]|[12]\d|3[01])[./\-](?:0?[1-9]|1[0-2])[./\-](?:19|20)\d{2}\b",
        "base_confidence": 0.5,
        "validator": None,
        "positive_keywords": ["рождения", "родился", "родилась", "д.р.", "г.р.", "дата рождения"],
        "negative_keywords": ["договор", "акт", "дата"],
    },
    {
        "code": "oms_policy",
        "finding_type": "oms_policy",
        "pattern": r"\b\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}\b",
        "base_confidence": 0.5,
        "validator": None,
        "positive_keywords": ["полис", "омс", "медицинское страхование", "енп"],
        "negative_keywords": [],
    },
    {
        "code": "driver_license",
        "finding_type": "driver_license",
        "pattern": r"\b\d{2}[\s]?\d{2}[\s]?\d{6}\b",
        "base_confidence": 0.5,
        "validator": None,
        "positive_keywords": ["водительское", "удостоверение", "права", "ву", "категория"],
        "negative_keywords": [],
    },
    {
        # ФИО — три слова с заглавной буквы подряд (Иванов Иван Иванович).
        # Не идеально, но контекст ("ФИО:", "от Иванова") поднимает уверенность.
        "code": "fio_ru",
        "finding_type": "fio",
        "pattern": r"\b[А-ЯЁ][а-яё]{1,20}\s+[А-ЯЁ][а-яё]{1,20}\s+[А-ЯЁ][а-яё]{1,20}\b",
        "base_confidence": 0.5,
        "validator": None,
        "positive_keywords": ["фио", "фамилия", "имя", "отчество", "от", "гражданин", "представитель", "заявитель"],
        "negative_keywords": ["российская федерация", "вооружённые силы"],
    },
    {
        # Адрес — улица/проспект/город + название и номер дома.
        "code": "address_ru",
        "finding_type": "address",
        "pattern": (
            r"(?:г\.|город|ул\.|улица|просп\.|проспект|пр\-?кт|пер\.|переулок|"
            r"ш\.|шоссе|наб\.|набережная|пл\.|площадь|б\-р|бульвар)"
            r"\s+[А-ЯЁа-яё0-9\s\.,\-]{3,80}?"
            r"(?:д\.\s*\d+[А-Яа-я]?|дом\s*\d+[А-Яа-я]?|кв\.\s*\d+|квартира\s*\d+|\d{1,5})"
        ),
        "base_confidence": 0.6,
        "validator": None,
        "positive_keywords": ["адрес", "регистрации", "проживания", "прописан", "место жительства"],
        "negative_keywords": [],
    },
]
