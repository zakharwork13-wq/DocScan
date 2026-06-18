//! Валидаторы контрольных сумм российских ПДн.
//! Полностью соответствуют Python-реализации в backend/app/detection/validators.py

fn digits(s: &str) -> Vec<u8> {
    s.chars()
        .filter_map(|c| c.to_digit(10).map(|d| d as u8))
        .collect()
}

/// СНИЛС — 11 цифр. Алгоритм: сумма произведений первых 9 цифр на (9..=1),
/// взять mod 101, если == 100 → 0, иначе остаток. Сравнить с двумя последними цифрами.
pub fn validate_snils(value: &str) -> bool {
    let d = digits(value);
    if d.len() != 11 {
        return false;
    }
    let total: u32 = (0..9).map(|i| d[i] as u32 * (9 - i as u32)).sum();
    let remainder = total % 101;
    let checksum: u32 = d[9] as u32 * 10 + d[10] as u32;
    if remainder == 100 {
        checksum == 0
    } else {
        checksum == remainder
    }
}

/// ИНН физлица — 12 цифр, две контрольные цифры (11-я и 12-я).
pub fn validate_inn_person(value: &str) -> bool {
    let d = digits(value);
    if d.len() != 12 {
        return false;
    }
    let k1: [u32; 10] = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8];
    let k2: [u32; 11] = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8];
    let c11: u32 = (0..10).map(|i| d[i] as u32 * k1[i]).sum::<u32>() % 11 % 10;
    let c12: u32 = (0..11).map(|i| d[i] as u32 * k2[i]).sum::<u32>() % 11 % 10;
    d[10] as u32 == c11 && d[11] as u32 == c12
}

/// ИНН юрлица — 10 цифр, одна контрольная цифра (10-я).
pub fn validate_inn_org(value: &str) -> bool {
    let d = digits(value);
    if d.len() != 10 {
        return false;
    }
    let k: [u32; 9] = [2, 4, 10, 3, 5, 9, 4, 6, 8];
    let c10: u32 = (0..9).map(|i| d[i] as u32 * k[i]).sum::<u32>() % 11 % 10;
    d[9] as u32 == c10
}

/// Универсальная проверка ИНН (по длине).
pub fn validate_inn(value: &str) -> bool {
    let d = digits(value);
    match d.len() {
        12 => validate_inn_person(value),
        10 => validate_inn_org(value),
        _ => false,
    }
}

/// Алгоритм Луна — для номеров банковских карт.
pub fn validate_luhn(value: &str) -> bool {
    let d = digits(value);
    if d.len() < 13 || d.len() > 19 {
        return false;
    }
    let total: u32 = d
        .iter()
        .rev()
        .enumerate()
        .map(|(i, &n)| {
            let mut x = n as u32;
            if i % 2 == 1 {
                x *= 2;
                if x > 9 {
                    x -= 9;
                }
            }
            x
        })
        .sum();
    total % 10 == 0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snils_valid() {
        assert!(validate_snils("112-233-445 95"));
        assert!(validate_snils("11223344595"));
    }

    #[test]
    fn snils_invalid() {
        assert!(!validate_snils("112-233-445 00"));
        assert!(!validate_snils("123-456"));
    }

    #[test]
    fn inn_person_valid() {
        assert!(validate_inn_person("500100732259"));
    }

    #[test]
    fn inn_person_invalid() {
        assert!(!validate_inn_person("123456789012"));
        assert!(!validate_inn_person("12345"));
    }

    #[test]
    fn inn_org_valid() {
        assert!(validate_inn_org("7736050003"));
    }

    #[test]
    fn inn_org_invalid() {
        assert!(!validate_inn_org("1234567890"));
    }

    #[test]
    fn luhn_visa_test_card() {
        assert!(validate_luhn("4111111111111111"));
        assert!(validate_luhn("4111 1111 1111 1111"));
    }

    #[test]
    fn luhn_mastercard_test() {
        assert!(validate_luhn("5555555555554444"));
    }

    #[test]
    fn luhn_invalid() {
        assert!(!validate_luhn("1234567890123456"));
    }

    #[test]
    fn luhn_too_short() {
        assert!(!validate_luhn("1234"));
    }
}
