//! Встроенные правила детекции — портированы из backend/app/detection/rules.py

use once_cell::sync::Lazy;
use regex::Regex;

use crate::validators;

pub type Validator = fn(&str) -> bool;

pub struct Rule {
    pub code: &'static str,
    pub finding_type: &'static str,
    pub pattern: Regex,
    pub base_confidence: f32,
    pub validator: Option<Validator>,
    pub positive_keywords: &'static [&'static str],
    pub negative_keywords: &'static [&'static str],
}

// Безопасное создание regex (паника при сборке если паттерн некорректный).
fn r(pattern: &str) -> Regex {
    Regex::new(&format!("(?i){}", pattern)).expect("invalid regex pattern")
}

pub static BUILTIN_RULES: Lazy<Vec<Rule>> = Lazy::new(|| {
    vec![
        Rule {
            code: "passport_rf",
            finding_type: "passport",
            pattern: r(r"\b\d{4}[\s\-]\d{6}\b"),
            base_confidence: 0.6,
            validator: None,
            positive_keywords: &["паспорт", "серия", "удостоверение личности", "выдан"],
            negative_keywords: &["договор", "счёт", "акт", "№"],
        },
        Rule {
            code: "snils",
            finding_type: "snils",
            pattern: r(r"\b\d{3}[\s\-]\d{3}[\s\-]\d{3}[\s\-]\d{2}\b"),
            base_confidence: 0.8,
            validator: Some(validators::validate_snils),
            positive_keywords: &["снилс", "страховое свидетельство", "пфр", "пенсионный"],
            negative_keywords: &[],
        },
        Rule {
            code: "inn_person",
            finding_type: "inn_person",
            pattern: r(r"\b\d{12}\b"),
            base_confidence: 0.7,
            validator: Some(validators::validate_inn_person),
            positive_keywords: &["инн", "налогоплательщик", "налоговый номер"],
            negative_keywords: &[],
        },
        Rule {
            code: "inn_org",
            finding_type: "inn_org",
            pattern: r(r"\b\d{10}\b"),
            base_confidence: 0.6,
            validator: Some(validators::validate_inn_org),
            positive_keywords: &["инн", "ооо", "ао", "ип", "организация"],
            negative_keywords: &[],
        },
        Rule {
            code: "bank_card",
            finding_type: "bank_card",
            pattern: r(r"\b(?:\d{4}[\s\-]){3}\d{4}\b"),
            base_confidence: 0.8,
            validator: Some(validators::validate_luhn),
            positive_keywords: &["карта", "номер карты", "оплата", "pan"],
            negative_keywords: &[],
        },
        Rule {
            code: "phone_rf",
            finding_type: "phone",
            pattern: r(r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"),
            base_confidence: 0.8,
            validator: None,
            positive_keywords: &["тел", "телефон", "моб", "звонок"],
            negative_keywords: &[],
        },
        Rule {
            code: "email",
            finding_type: "email",
            pattern: r(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"),
            base_confidence: 0.9,
            validator: None,
            positive_keywords: &[],
            negative_keywords: &["example.com", "test.ru", "noreply"],
        },
        Rule {
            code: "date_of_birth",
            finding_type: "date_of_birth",
            pattern: r(r"\b(?:0?[1-9]|[12]\d|3[01])[./\-](?:0?[1-9]|1[0-2])[./\-](?:19|20)\d{2}\b"),
            base_confidence: 0.5,
            validator: None,
            positive_keywords: &["рождения", "родился", "родилась", "д.р.", "г.р.", "дата рождения"],
            negative_keywords: &["договор", "акт", "дата"],
        },
        Rule {
            code: "oms_policy",
            finding_type: "oms_policy",
            pattern: r(r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b"),
            base_confidence: 0.5,
            validator: None,
            positive_keywords: &["полис", "омс", "медицинское страхование", "енп"],
            negative_keywords: &[],
        },
        Rule {
            code: "driver_license",
            finding_type: "driver_license",
            pattern: r(r"\b\d{2}\s?\d{2}\s?\d{6}\b"),
            base_confidence: 0.5,
            validator: None,
            positive_keywords: &["водительское", "удостоверение", "права", "ву", "категория"],
            negative_keywords: &[],
        },
    ]
});
