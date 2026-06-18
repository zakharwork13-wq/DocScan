/**
 * Обезличивание документов с сохранением исходного формата.
 *
 * Для DOCX и XLSX мы НЕ генерируем плоский TXT — вместо этого подменяем
 * текст прямо внутри Office Open XML структуры, чтобы пользователь получил
 * нормальный .docx / .xlsx файл с теми же стилями и форматированием.
 */

import { redactText } from "./redaction";
import { scanWithWasm, type WasmFinding } from "./wasmScanner";

export interface RedactedFile {
  blob: Blob;
  filename: string;
  /** Сколько находок было заменено в итоговом файле. */
  replacedCount: number;
}

/**
 * Заменить ПДн в произвольной строке текста через WASM.
 * Возвращает обезличенный текст и количество замен.
 */
async function redactString(text: string): Promise<{ text: string; count: number }> {
  if (!text || text.trim().length === 0) return { text, count: 0 };
  const r = await scanWithWasm(text);
  if (r.findings.length === 0) return { text, count: 0 };
  return { text: redactText(text, r.findings), count: r.findings.length };
}


// ─── DOCX ─────────────────────────────────────────────────────────────────────

/**
 * DOCX — это ZIP с XML. Текст лежит внутри тегов <w:t>...</w:t>.
 * Мы декодируем содержимое каждого такого тега, обезличиваем и кладём обратно.
 */
export async function redactDocx(file: File, originalName: string): Promise<RedactedFile> {
  const JSZip = (await import("jszip")).default;
  const buf = await file.arrayBuffer();
  const zip = await JSZip.loadAsync(buf);

  const targets = [
    "word/document.xml",
    "word/header1.xml",
    "word/header2.xml",
    "word/header3.xml",
    "word/footer1.xml",
    "word/footer2.xml",
    "word/footer3.xml",
  ];

  let totalReplaced = 0;

  for (const path of targets) {
    const entry = zip.file(path);
    if (!entry) continue;
    const xml = await entry.async("string");

    // Меняем содержимое каждого <w:t ...>...</w:t>
    const re = /<w:t(\s[^>]*)?>([\s\S]*?)<\/w:t>/g;
    const newXml = await replaceAsync(xml, re, async (full, attrs, inner) => {
      const decoded = decodeXmlEntities(inner);
      const { text, count } = await redactString(decoded);
      totalReplaced += count;
      // Если что-то заменили — нужно сохранить пробелы (xml:space="preserve")
      const safeAttrs = attrs ?? "";
      const preserveAttr =
        text !== decoded && !safeAttrs.includes("xml:space")
          ? ' xml:space="preserve"'
          : "";
      return `<w:t${safeAttrs}${preserveAttr}>${encodeXmlEntities(text)}</w:t>`;
    });

    zip.file(path, newXml);
  }

  const blob = await zip.generateAsync({
    type: "blob",
    mimeType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    compression: "DEFLATE",
  });

  return {
    blob,
    filename: replaceExtension(originalName, ".docx", "_обезличено.docx"),
    replacedCount: totalReplaced,
  };
}


// ─── XLSX ─────────────────────────────────────────────────────────────────────

/**
 * XLSX — обходим все строковые ячейки на всех листах, обезличиваем
 * и пишем обратно тем же sheetjs.
 */
export async function redactXlsx(file: File, originalName: string): Promise<RedactedFile> {
  const XLSX = await import("xlsx");
  const buf = await file.arrayBuffer();
  const wb = XLSX.read(buf, { type: "array" });

  let totalReplaced = 0;

  for (const sheetName of wb.SheetNames) {
    const sheet = wb.Sheets[sheetName];
    if (!sheet["!ref"]) continue;
    const range = XLSX.utils.decode_range(sheet["!ref"]);

    for (let r = range.s.r; r <= range.e.r; r++) {
      for (let c = range.s.c; c <= range.e.c; c++) {
        const addr = XLSX.utils.encode_cell({ r, c });
        const cell = sheet[addr];
        if (!cell) continue;

        // Обрабатываем строковые ячейки и форматированный результат чисел/дат
        const candidates: { key: "v" | "w"; value: string }[] = [];
        if (typeof cell.v === "string") candidates.push({ key: "v", value: cell.v });
        if (typeof cell.w === "string" && cell.w !== cell.v)
          candidates.push({ key: "w", value: cell.w });

        for (const cand of candidates) {
          const { text, count } = await redactString(cand.value);
          if (count > 0) {
            cell[cand.key] = text;
            if (cand.key === "v") cell.t = "s"; // переводим в строку
            totalReplaced += count;
          }
        }
      }
    }
  }

  const out = XLSX.write(wb, { bookType: "xlsx", type: "array" });
  const blob = new Blob([out], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });

  return {
    blob,
    filename: replaceExtension(originalName, ".xlsx", "_обезличено.xlsx"),
    replacedCount: totalReplaced,
  };
}


// ─── TXT (fallback для остальных форматов) ──────────────────────────────────

export async function redactTxt(
  originalName: string,
  redactedText: string,
  findingsCount: number,
  category: string,
): Promise<RedactedFile> {
  const header = [
    "=".repeat(60),
    "ОБЕЗЛИЧЕННАЯ КОПИЯ ДОКУМЕНТА",
    "=".repeat(60),
    `Исходный файл:    ${originalName}`,
    `Заменено находок: ${findingsCount}`,
    `Категория:        ${category}`,
    `Сгенерировано:    ${new Date().toLocaleString("ru-RU")}`,
    "Все персональные данные заменены замаскированными значениями.",
    "=".repeat(60),
    "",
    "",
  ].join("\n");

  const blob = new Blob([header + redactedText], { type: "text/plain;charset=utf-8" });
  return {
    blob,
    filename: replaceExtensionAny(originalName, "_обезличено.txt"),
    replacedCount: findingsCount,
  };
}


// ─── Главная диспетчер-функция ───────────────────────────────────────────────

/**
 * Универсальный вход: автоматически выбирает стратегию по типу файла.
 * Для DOCX/XLSX возвращает файл того же формата, для остальных — TXT.
 */
export async function redactFileToSameFormat(
  file: File,
  fallbackRedactedText: string,
  fallbackFindingsCount: number,
  fallbackCategory: string,
): Promise<RedactedFile> {
  const lower = file.name.toLowerCase();
  if (lower.endsWith(".docx")) {
    return redactDocx(file, file.name);
  }
  if (lower.endsWith(".xlsx")) {
    return redactXlsx(file, file.name);
  }
  return redactTxt(
    file.name,
    fallbackRedactedText,
    fallbackFindingsCount,
    fallbackCategory,
  );
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  URL.revokeObjectURL(url);
  a.remove();
}


// ─── Утилиты ─────────────────────────────────────────────────────────────────

function replaceExtension(name: string, oldExt: string, newSuffix: string): string {
  if (name.toLowerCase().endsWith(oldExt)) {
    return name.slice(0, -oldExt.length) + newSuffix;
  }
  return name + newSuffix;
}

function replaceExtensionAny(name: string, newSuffix: string): string {
  const dot = name.lastIndexOf(".");
  const base = dot > 0 ? name.slice(0, dot) : name;
  return base + newSuffix;
}

function decodeXmlEntities(s: string): string {
  return s
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, "&");
}

function encodeXmlEntities(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/** Асинхронная версия String.replace с async-replacer. */
async function replaceAsync(
  str: string,
  re: RegExp,
  fn: (match: string, ...args: any[]) => Promise<string>,
): Promise<string> {
  const promises: Promise<string>[] = [];
  str.replace(re, (match, ...args) => {
    promises.push(fn(match, ...args));
    return match;
  });
  const results = await Promise.all(promises);
  return str.replace(re, () => results.shift() ?? "");
}

// Помечаем что WasmFinding всё ещё нужен (через redaction.ts).
// eslint-disable-next-line @typescript-eslint/no-unused-vars
type _Unused = WasmFinding;
