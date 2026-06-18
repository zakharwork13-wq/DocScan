//! Маскирование найденных значений ПДн перед отправкой результата.
//! Соответствует backend/app/detection/masker.py

fn digits_str(s: &str) -> String {
    s.chars().filter(|c| c.is_ascii_digit()).collect()
}

pub fn mask_value(value: &str, finding_type: &str) -> String {
    let d = digits_str(value);
    match finding_type {
        "passport" if d.len() == 10 => {
            format!("{}** ***{}", &d[..2], &d[7..])
        }
        "snils" if d.len() == 11 => {
            format!("{}-***-*** {}", &d[..3], &d[9..])
        }
        "inn_person" | "inn_org" if d.len() >= 6 => {
            let stars = "*".repeat(d.len() - 6);
            format!("{}{}{}", &d[..4], stars, &d[d.len() - 2..])
        }
        "bank_card" if d.len() >= 8 => {
            format!("{} **** **** {}", &d[..4], &d[d.len() - 4..])
        }
        "phone" if d.len() >= 10 => {
            let first = &d[d.len() - 10..d.len() - 9];
            let last2 = &d[d.len() - 2..];
            format!("+7 ({}**) ***-**-{}", first, last2)
        }
        "email" => {
            if let Some((local, domain)) = value.split_once('@') {
                if local.len() > 2 {
                    format!("{}***@{}", &local[..2], domain)
                } else {
                    format!("***@{}", domain)
                }
            } else {
                "***".to_string()
            }
        }
        "date_of_birth" => "**.**.****".to_string(),
        _ => {
            if value.len() > 6 {
                let bytes = value.as_bytes();
                let head = std::str::from_utf8(&bytes[..2]).unwrap_or("");
                let tail = std::str::from_utf8(&bytes[bytes.len() - 2..]).unwrap_or("");
                let stars = "*".repeat(value.len() - 4);
                format!("{}{}{}", head, stars, tail)
            } else {
                "***".to_string()
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn passport() {
        assert_eq!(mask_value("4507 123456", "passport"), "45** ***456");
    }

    #[test]
    fn snils() {
        assert_eq!(mask_value("112-233-445 95", "snils"), "112-***-*** 95");
    }

    #[test]
    fn bank_card() {
        assert_eq!(
            mask_value("4111111111111111", "bank_card"),
            "4111 **** **** 1111"
        );
    }

    #[test]
    fn phone() {
        assert_eq!(
            mask_value("+7 (999) 123-45-67", "phone"),
            "+7 (9**) ***-**-67"
        );
    }

    #[test]
    fn email_normal() {
        assert_eq!(mask_value("ivanov@example.com", "email"), "iv***@example.com");
    }

    #[test]
    fn email_short() {
        assert_eq!(mask_value("ab@example.com", "email"), "***@example.com");
    }

    #[test]
    fn date_of_birth() {
        assert_eq!(mask_value("15.03.1985", "date_of_birth"), "**.**.****");
    }
}
