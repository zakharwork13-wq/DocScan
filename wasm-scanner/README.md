# DocScan WASM Scanner

Клиентский движок поиска персональных данных, скомпилированный в WebAssembly.

**Главная фишка проекта:** документ обрабатывается прямо в браузере, его содержимое никогда не покидает устройство пользователя. На сервер отправляются только агрегированные метаданные (количество и типы находок).

## Сборка

```bash
# Установить wasm-pack один раз
cargo install wasm-pack

# Сборка для использования в браузере
wasm-pack build --target web --out-dir ../frontend/src/wasm
```

## Тесты

```bash
cargo test
```

## Архитектура

```
src/
├── lib.rs        — точка входа, экспорт в JS
├── validators.rs — контрольные суммы (СНИЛС, ИНН, Луна)
├── masker.rs     — маскирование найденных значений
├── rules.rs      — 10 встроенных правил детекции
└── engine.rs     — главный движок: regex + контекст + классификация
```

## Использование из JS

```javascript
import init, { scanText, version } from "@/wasm/docscan_wasm_scanner";

await init();

const result = scanText("Мой телефон: +7 (999) 123-45-67");
// {
//   findings: [{ finding_type: "phone", masked_value: "+7 (9**) ***-**-67", ... }],
//   findings_summary: { phone: 1 },
//   document_category: "internal"
// }
```
