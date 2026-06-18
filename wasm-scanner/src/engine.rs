//! Движок детекции: применяет правила, считает уверенность,
//! классифицирует документ. Полностью соответствует Python-движку.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

use crate::masker;
use crate::rules::BUILTIN_RULES;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Finding {
    pub finding_type: String,
    pub masked_value: String,
    pub position_start: usize,
    pub position_end: usize,
    pub confidence: f32,
    pub context_masked: Option<String>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ScanResult {
    pub findings: Vec<Finding>,
    pub findings_summary: std::collections::BTreeMap<String, usize>,
    pub document_category: String,
}

const CONTEXT_WINDOW: usize = 50;
const MIN_CONFIDENCE: f32 = 0.5;

fn lowercase_window(text: &str, start: usize, end: usize) -> (String, usize, usize) {
    let bytes = text.as_bytes();
    let win_start = start.saturating_sub(CONTEXT_WINDOW);
    let win_end = (end + CONTEXT_WINDOW).min(bytes.len());
    // Аккуратно выравниваем по UTF-8 границам
    let safe_start = (win_start..=start)
        .rev()
        .find(|&i| text.is_char_boundary(i))
        .unwrap_or(0);
    let safe_end = (end..=win_end)
        .find(|&i| text.is_char_boundary(i))
        .unwrap_or(bytes.len());
    let slice = &text[safe_start..safe_end];
    (slice.to_lowercase(), safe_start, safe_end)
}

pub fn scan(text: &str) -> ScanResult {
    let mut findings: Vec<Finding> = Vec::new();

    for rule in BUILTIN_RULES.iter() {
        for m in rule.pattern.find_iter(text) {
            let raw = m.as_str();
            let mut confidence = rule.base_confidence;

            // Валидация контрольной суммы
            if let Some(validator) = rule.validator {
                if !validator(raw) {
                    confidence -= 0.5;
                }
            }
            if confidence <= 0.0 {
                continue;
            }

            // Контекстный анализ
            let (context, ctx_start, _) = lowercase_window(text, m.start(), m.end());
            for kw in rule.positive_keywords {
                if context.contains(*kw) {
                    confidence = (confidence + 0.1).min(1.0);
                }
            }
            for kw in rule.negative_keywords {
                if context.contains(*kw) {
                    confidence = (confidence - 0.1).max(0.0);
                }
            }

            if confidence < MIN_CONFIDENCE {
                continue;
            }

            let masked_value = masker::mask_value(raw, rule.finding_type);
            let context_raw = &text[ctx_start..ctx_start + context.len().min(text.len() - ctx_start)];
            let context_masked = masker::mask_value(context_raw, rule.finding_type);

            findings.push(Finding {
                finding_type: rule.finding_type.to_string(),
                masked_value,
                position_start: m.start(),
                position_end: m.end(),
                confidence: (confidence * 100.0).round() / 100.0,
                context_masked: Some(context_masked),
            });
        }
    }

    let mut findings_summary = std::collections::BTreeMap::new();
    for f in &findings {
        *findings_summary.entry(f.finding_type.clone()).or_insert(0) += 1;
    }

    let document_category = classify(&findings);

    ScanResult {
        findings,
        findings_summary,
        document_category,
    }
}

pub fn classify(findings: &[Finding]) -> String {
    let types: HashSet<&str> = findings.iter().map(|f| f.finding_type.as_str()).collect();

    if types.is_empty() {
        return "public".to_string();
    }

    let strict_types: HashSet<&str> = [
        "passport", "snils", "inn_person", "bank_card", "oms_policy", "driver_license",
    ]
    .into_iter()
    .collect();

    let contact_only: HashSet<&str> = ["phone", "email"].into_iter().collect();

    if !types.is_disjoint(&strict_types) {
        if types.contains("passport") && (types.contains("fio") || types.contains("address")) {
            return "strict".to_string();
        }
        return "confidential".to_string();
    }

    if types.is_subset(&contact_only) {
        return "internal".to_string();
    }

    "confidential".to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_email() {
        let r = scan("Свяжитесь: ivan@example.com");
        assert!(r.findings.iter().any(|f| f.finding_type == "email"));
    }

    #[test]
    fn detects_phone() {
        let r = scan("Телефон: +7 (999) 123-45-67");
        assert!(r.findings.iter().any(|f| f.finding_type == "phone"));
    }

    #[test]
    fn detects_valid_bank_card() {
        let r = scan("Номер карты: 4111 1111 1111 1111");
        assert!(r.findings.iter().any(|f| f.finding_type == "bank_card"));
    }

    #[test]
    fn no_findings_in_plain_text() {
        let r = scan("Это обычный текст без секретов.");
        assert_eq!(r.findings.len(), 0);
        assert_eq!(r.document_category, "public");
    }

    #[test]
    fn classify_internal() {
        let f = vec![Finding {
            finding_type: "email".to_string(),
            masked_value: "***".to_string(),
            position_start: 0,
            position_end: 1,
            confidence: 0.9,
            context_masked: None,
        }];
        assert_eq!(classify(&f), "internal");
    }

    #[test]
    fn classify_confidential_with_passport() {
        let f = vec![Finding {
            finding_type: "passport".to_string(),
            masked_value: "***".to_string(),
            position_start: 0,
            position_end: 1,
            confidence: 0.7,
            context_masked: None,
        }];
        assert_eq!(classify(&f), "confidential");
    }

    #[test]
    fn masked_values_dont_contain_originals() {
        let r = scan("email: test@gmail.com");
        for f in r.findings {
            assert!(!f.masked_value.contains("test@gmail.com"));
        }
    }
}
