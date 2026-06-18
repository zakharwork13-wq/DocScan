/**
 * Обёртка над WASM-сканером.
 *
 * Главный смысл: документ обрабатывается в браузере, не уходит на сервер.
 */

import init, { scanText, version } from "@/wasm/docscan_scanner.js";
import wasmUrl from "@/wasm/docscan_scanner_bg.wasm?url";
import type { FindingType } from "@/types";

export interface WasmFinding {
  finding_type: FindingType;
  masked_value: string;
  position_start: number;
  position_end: number;
  confidence: number;
  context_masked: string | null;
}

export interface WasmScanResult {
  findings: WasmFinding[];
  findings_summary: Record<string, number>;
  document_category: "strict" | "confidential" | "internal" | "public";
}

let initialized = false;
let initPromise: Promise<void> | null = null;

/** Инициализировать WASM-модуль (загрузить .wasm файл). Идемпотентно. */
export async function ensureWasmReady(): Promise<void> {
  if (initialized) return;
  if (initPromise) return initPromise;

  initPromise = (async () => {
    await init({ module_or_path: wasmUrl });
    initialized = true;
    // eslint-disable-next-line no-console
    console.info(`[wasm] DocScan scanner v${version()} loaded`);
  })();
  return initPromise;
}

/** Запустить сканирование текста через WASM. */
export async function scanWithWasm(text: string): Promise<WasmScanResult> {
  await ensureWasmReady();
  const result = scanText(text) as WasmScanResult;

  // Rust regex возвращает позиции в БАЙТАХ UTF-8.
  // JavaScript использует UTF-16 индексы. Для кириллицы это разные значения
  // (русская буква = 2 байта UTF-8 = 1 единица UTF-16), поэтому конвертируем.
  if (result.findings.length > 0) {
    const byteOffsets = new Set<number>();
    for (const f of result.findings) {
      byteOffsets.add(f.position_start);
      byteOffsets.add(f.position_end);
    }
    const byteToChar = buildByteToCharMap(text, byteOffsets);
    for (const f of result.findings) {
      f.position_start = byteToChar.get(f.position_start) ?? f.position_start;
      f.position_end = byteToChar.get(f.position_end) ?? f.position_end;
    }
  }
  return result;
}

/**
 * Построить map: байтовая позиция UTF-8 → UTF-16 индекс строки.
 * Считаем только для нужных позиций, чтобы не аллоцировать массив на всю строку.
 */
function buildByteToCharMap(text: string, byteOffsets: Set<number>): Map<number, number> {
  const result = new Map<number, number>();
  const encoder = new TextEncoder();
  let byteIdx = 0;
  let charIdx = 0;

  if (byteOffsets.has(0)) result.set(0, 0);

  while (charIdx < text.length) {
    // Корректно обрабатываем суррогатные пары (хотя для русского не нужно)
    const code = text.charCodeAt(charIdx);
    const isHighSurrogate = code >= 0xd800 && code <= 0xdbff;
    const chunkLen = isHighSurrogate && charIdx + 1 < text.length ? 2 : 1;
    const chunk = text.substring(charIdx, charIdx + chunkLen);
    byteIdx += encoder.encode(chunk).length;
    charIdx += chunkLen;
    if (byteOffsets.has(byteIdx)) result.set(byteIdx, charIdx);
  }
  return result;
}

/** Версия WASM-движка. */
export async function getWasmVersion(): Promise<string> {
  await ensureWasmReady();
  return version();
}
