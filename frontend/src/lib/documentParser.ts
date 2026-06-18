/**
 * Парсеры документов в браузере — извлечение текста для последующего
 * клиентского сканирования через WASM.
 *
 * Поддерживаются: TXT, DOCX, XLSX, PDF (с текстовым слоем).
 * Картинки и PDF-сканы здесь не обрабатываются — для них нужен серверный режим с OCR.
 */

export type SupportedMime =
  | "text/plain"
  | "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  | "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  | "application/vnd.ms-excel"
  | "application/pdf"
  | "text/rtf"
  | "application/rtf";

export async function extractText(file: File): Promise<string> {
  const mime = file.type || guessMimeByExtension(file.name);

  if (mime === "text/plain" || mime.startsWith("text/")) {
    return await extractTxt(file);
  }

  if (mime === "application/vnd.openxmlformats-officedocument.wordprocessingml.document") {
    return await extractDocx(file);
  }

  if (
    mime === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
    mime === "application/vnd.ms-excel"
  ) {
    return await extractXlsx(file);
  }

  if (mime === "application/pdf") {
    return await extractPdf(file);
  }

  if (mime === "application/rtf" || mime === "text/rtf") {
    return await extractRtf(file);
  }

  throw new Error(`Тип файла не поддерживается на клиенте: ${mime}`);
}

function guessMimeByExtension(name: string): string {
  const lower = name.toLowerCase();
  if (lower.endsWith(".docx")) return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  if (lower.endsWith(".xlsx")) return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  if (lower.endsWith(".xls")) return "application/vnd.ms-excel";
  if (lower.endsWith(".pdf")) return "application/pdf";
  if (lower.endsWith(".txt")) return "text/plain";
  if (lower.endsWith(".rtf")) return "application/rtf";
  return "application/octet-stream";
}

async function extractTxt(file: File): Promise<string> {
  // Пробуем UTF-8, потом Windows-1251
  const buf = await file.arrayBuffer();
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(buf);
  } catch {
    return new TextDecoder("windows-1251").decode(buf);
  }
}

async function extractRtf(file: File): Promise<string> {
  // Простой стрип RTF-разметки: убираем контрольные слова и скобки
  const raw = await extractTxt(file);
  return raw
    .replace(/\\[a-zA-Z]+-?\d*\s?/g, "")
    .replace(/[{}]/g, "")
    .replace(/\\'([0-9a-fA-F]{2})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)))
    .replace(/\s+/g, " ");
}

async function extractDocx(file: File): Promise<string> {
  const mammoth = await import("mammoth/mammoth.browser");
  const buf = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ arrayBuffer: buf });
  return result.value;
}

async function extractXlsx(file: File): Promise<string> {
  const XLSX = await import("xlsx");
  const buf = await file.arrayBuffer();
  const wb = XLSX.read(buf, { type: "array" });
  const parts: string[] = [];
  for (const sheetName of wb.SheetNames) {
    const sheet = wb.Sheets[sheetName];
    parts.push(`--- ${sheetName} ---`);
    parts.push(XLSX.utils.sheet_to_csv(sheet, { FS: " | " }));
  }
  return parts.join("\n");
}

async function extractPdf(file: File): Promise<string> {
  // pdfjs-dist подключается через динамический импорт
  const pdfjs: any = await import("pdfjs-dist");
  const workerSrc = (await import("pdfjs-dist/build/pdf.worker.min.mjs?url")).default;
  pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;

  const buf = await file.arrayBuffer();
  const doc = await pdfjs.getDocument({ data: buf }).promise;
  const parts: string[] = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const page = await doc.getPage(i);
    const content = await page.getTextContent();
    const text = content.items.map((it: any) => ("str" in it ? it.str : "")).join(" ");
    parts.push(text);
  }
  return parts.join("\n");
}

/** SHA-256 хеш файла через WebCrypto. */
export async function computeFileHash(file: File): Promise<string> {
  const buf = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
