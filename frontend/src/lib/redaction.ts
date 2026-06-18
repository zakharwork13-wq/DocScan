/**
 * Обезличивание (redaction) документов.
 *
 * Логика: WASM возвращает каждую находку с позициями (position_start, position_end)
 * и маской (masked_value). Мы идём по находкам в обратном порядке и заменяем
 * исходный фрагмент текста на маску — позиции остальных находок не сдвигаются.
 */

import type { WasmFinding } from "./wasmScanner";

/**
 * Применить маски к тексту по найденным позициям.
 *
 * Если несколько находок перекрываются (например, одна и та же строка
 * матчится двумя правилами), оставляем только одну — с наибольшей
 * уверенностью. Иначе при замене получится мешанина из частично
 * подставленных масок.
 */
export function redactText(text: string, findings: WasmFinding[]): string {
  // 1. Отбрасываем находки с битыми позициями
  const valid = findings.filter(
    (f) =>
      f.position_start != null &&
      f.position_end != null &&
      f.position_start >= 0 &&
      f.position_end <= text.length &&
      f.position_start < f.position_end,
  );

  // 2. Сортируем по началу, при равенстве — длинная находка раньше
  valid.sort((a, b) => {
    if (a.position_start !== b.position_start) return a.position_start - b.position_start;
    return b.position_end - a.position_end;
  });

  // 3. Жадно убираем перекрывающиеся: оставляем находку с большей уверенностью
  const nonOverlapping: WasmFinding[] = [];
  for (const f of valid) {
    const last = nonOverlapping[nonOverlapping.length - 1];
    if (!last || f.position_start >= last.position_end) {
      nonOverlapping.push(f);
    } else if (f.confidence > last.confidence) {
      nonOverlapping[nonOverlapping.length - 1] = f;
    }
    // иначе пропускаем — текущая находка перекрывается с уже выбранной
    // и имеет меньшую/равную уверенность
  }

  // 4. Заменяем с конца, чтобы не сдвигать остальные позиции
  let result = text;
  for (let i = nonOverlapping.length - 1; i >= 0; i--) {
    const f = nonOverlapping[i];
    result = result.slice(0, f.position_start) + f.masked_value + result.slice(f.position_end);
  }
  return result;
}

/** Скачать текст как файл. */
export function downloadText(content: string, filename: string) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  URL.revokeObjectURL(url);
  a.remove();
}

/** Заголовок и подпись отчёта-обезличивания. */
export function buildRedactedTextFile(
  originalFilename: string,
  redactedText: string,
  findingsCount: number,
  category: string,
): string {
  const header = [
    "=".repeat(60),
    "ОБЕЗЛИЧЕННАЯ КОПИЯ ДОКУМЕНТА",
    "=".repeat(60),
    `Исходный файл:    ${originalFilename}`,
    `Заменено находок: ${findingsCount}`,
    `Категория:        ${category}`,
    `Сгенерировано:    ${new Date().toLocaleString("ru-RU")}`,
    "Все персональные данные заменены замаскированными значениями.",
    "=".repeat(60),
    "",
    "",
  ].join("\n");
  return header + redactedText;
}

/** Сформировать имя файла обезличенной версии. */
export function redactedFilename(original: string): string {
  const dot = original.lastIndexOf(".");
  const base = dot > 0 ? original.slice(0, dot) : original;
  return `${base}_обезличено.txt`;
}
