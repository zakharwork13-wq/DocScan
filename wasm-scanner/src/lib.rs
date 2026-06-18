//! DocScan WASM Scanner — клиентский движок поиска ПДн.
//!
//! Главная цель проекта: текст документа никогда не покидает браузер пользователя.
//! Сервер получает только агрегированные метаданные (количество и типы находок).

mod engine;
mod masker;
mod rules;
mod validators;

pub use engine::{classify, scan, Finding, ScanResult};
pub use masker::mask_value;
pub use validators::{validate_inn, validate_inn_org, validate_inn_person, validate_luhn, validate_snils};

#[cfg(target_arch = "wasm32")]
mod wasm_api {
    use wasm_bindgen::prelude::*;

    /// Главная точка входа из JavaScript.
    /// Принимает текст документа, возвращает JS-объект с результатами.
    #[wasm_bindgen(js_name = scanText)]
    pub fn scan_text(text: &str) -> Result<JsValue, JsValue> {
        let result = super::engine::scan(text);
        serde_wasm_bindgen::to_value(&result).map_err(|e| JsValue::from_str(&e.to_string()))
    }

    /// Версия движка (для диагностики).
    #[wasm_bindgen(js_name = version)]
    pub fn version() -> String {
        env!("CARGO_PKG_VERSION").to_string()
    }

    /// Тип находок, которые умеет определять движок.
    #[wasm_bindgen(js_name = supportedTypes)]
    pub fn supported_types() -> Vec<JsValue> {
        super::rules::BUILTIN_RULES
            .iter()
            .map(|r| JsValue::from_str(r.finding_type))
            .collect()
    }

    /// Хеширование SHA-256 (используется фронтом перед отправкой результата).
    /// Реализуем простой враппер чтобы не тащить wasm-bindgen-crypto.
    /// На фронте всё равно есть crypto.subtle, поэтому не дублируем.

    /// Установка panic-хука для удобной отладки.
    #[wasm_bindgen(start)]
    pub fn main() {
        std::panic::set_hook(Box::new(console_error_panic_hook));
    }

    fn console_error_panic_hook(info: &std::panic::PanicHookInfo<'_>) {
        web_sys_console_error(&info.to_string());
    }

    fn web_sys_console_error(msg: &str) {
        let _ = js_sys::eval(&format!("console.error({:?})", msg));
    }
}
