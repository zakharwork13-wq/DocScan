import { useMutation } from "@tanstack/react-query";
import {
  CheckCircle2,
  Cloud,
  Download,
  FileText,
  Lock,
  Upload as UploadIcon,
} from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import * as scansApi from "@/api/scans";
import { computeFileHash, extractText } from "@/lib/documentParser";
import { downloadText, redactText } from "@/lib/redaction";
import { formatBytes } from "@/lib/utils";
import { scanWithWasm, type WasmScanResult } from "@/lib/wasmScanner";

const ACCEPTED = [
  ".doc", ".docx", ".pdf", ".xls", ".xlsx", ".txt", ".rtf",
  ".png", ".jpg", ".jpeg", ".tiff",
];

const MAX_SIZE = 50 * 1024 * 1024;

type ScanMode = "client" | "server";

export function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<ScanMode>("client");
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [progressLabel, setProgressLabel] = useState<string>("");
  const [scanResult, setScanResult] = useState<{
    scanId: string;
    result: WasmScanResult;
  } | null>(null);

  // Храним извлечённый текст в ref — он не уходит из памяти браузера
  const originalTextRef = useRef<string>("");

  const mutation = useMutation({
    mutationFn: async (f: File) => {
      if (mode === "server") {
        const submitted = await scansApi.uploadScan(f);
        return { submitted, result: null as WasmScanResult | null };
      }
      // Клиентский режим — всё в браузере
      setProgressLabel("Извлекаем текст...");
      const text = await extractText(f);
      originalTextRef.current = text;

      setProgressLabel("Хешируем файл...");
      const hash = await computeFileHash(f);

      setProgressLabel("Сканируем через WASM...");
      const result = await scanWithWasm(text);

      setProgressLabel("Отправляем результат на сервер...");
      const submitted = await scansApi.submitClientResult({
        original_filename: f.name,
        file_size_bytes: f.size,
        file_hash: hash,
        mime_type: f.type || "application/octet-stream",
        document_category: result.document_category,
        findings_summary: result.findings_summary,
      });
      return { submitted, result };
    },
    onSuccess: ({ submitted, result }) => {
      if (mode === "client" && result) {
        // Не уходим со страницы — показываем кнопку скачать обезличенную версию
        setScanResult({ scanId: submitted.id, result });
        setProgressLabel("");
      } else {
        navigate(`/scans/${submitted.id}`);
      }
    },
    onError: (e: any) => {
      const msg =
        e?.response?.data?.detail ??
        e?.message ??
        "Не удалось обработать файл";
      setError(typeof msg === "string" ? msg : "Ошибка обработки");
      setProgressLabel("");
    },
  });

  const handleFile = useCallback((f: File) => {
    setError(null);
    setScanResult(null);
    if (f.size > MAX_SIZE) {
      setError(`Файл превышает 50 МБ (${formatBytes(f.size)})`);
      return;
    }
    setFile(f);
  }, []);

  const handleDownloadRedacted = async () => {
    if (!scanResult || !file) return;
    try {
      const { redactFileToSameFormat, downloadBlob } = await import("@/lib/redactionFormats");

      // Для DOCX/XLSX редактируем сам файл, для остальных — TXT с заголовком
      const redactedText = redactText(originalTextRef.current, scanResult.result.findings);
      const result = await redactFileToSameFormat(
        file,
        redactedText,
        scanResult.result.findings.length,
        scanResult.result.document_category,
      );
      downloadBlob(result.blob, result.filename);
    } catch (e) {
      console.error(e);
      setError("Не удалось сгенерировать обезличенную копию");
    }
  };

  const handleDownloadOriginalText = () => {
    if (!scanResult || !file) return;
    downloadText(originalTextRef.current, `${file.name}_извлечённый_текст.txt`);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Загрузка документа</h1>
        <p className="text-slate-500 text-sm mt-1">
          Выберите режим сканирования — в браузере или на сервере.
        </p>
      </div>

      {/* Переключатель режима */}
      <div className="card !p-3">
        <div className="grid grid-cols-2 gap-2">
          <ModeOption
            active={mode === "client"}
            onClick={() => setMode("client")}
            icon={Lock}
            title="В браузере"
            subtitle="Файл не покидает устройство. WASM-движок (Rust) ищет ПДн прямо в браузере."
            badge="Приватность"
            badgeColor="bg-green-100 text-green-700"
          />
          <ModeOption
            active={mode === "server"}
            onClick={() => setMode("server")}
            icon={Cloud}
            title="На сервере"
            subtitle="Файл шифруется, загружается на сервер, обрабатывается там и удаляется."
            badge="OCR доступен"
            badgeColor="bg-blue-100 text-blue-700"
          />
        </div>
      </div>

      <div
        className={`card border-2 border-dashed transition-colors ${
          dragActive ? "border-brand-500 bg-brand-50/40" : "border-slate-300"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
      >
        {!file ? (
          <div className="text-center py-8">
            <UploadIcon className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-700 font-medium mb-1">
              Перетащите файл сюда или
            </p>
            <label className="btn-primary cursor-pointer inline-flex">
              Выберите файл
              <input
                type="file"
                accept={ACCEPTED.join(",")}
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFile(f);
                }}
              />
            </label>
            <p className="text-xs text-slate-400 mt-4">
              DOC, DOCX, PDF, XLS, XLSX, TXT, RTF
              {mode === "server" && ", изображения"}
              . Макс. 50 МБ
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-3 bg-slate-50 p-3 rounded-md">
              <FileText className="w-8 h-8 text-brand-600" />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-slate-900 truncate">
                  {file.name}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  {formatBytes(file.size)} · {file.type || "неизвестный тип"}
                </div>
              </div>
              <CheckCircle2 className="w-5 h-5 text-green-600 shrink-0" />
            </div>

            {mutation.isPending && progressLabel && (
              <div className="text-sm text-brand-700 bg-brand-50 border border-brand-200 rounded p-2 flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-brand-600 animate-pulse" />
                {progressLabel}
              </div>
            )}

            <div className="flex gap-3">
              <button
                className="btn-primary flex-1"
                disabled={mutation.isPending}
                onClick={() => {
                  setError(null);
                  mutation.mutate(file);
                }}
              >
                {mutation.isPending
                  ? "Обрабатываем..."
                  : mode === "client"
                    ? "Сканировать в браузере"
                    : "Загрузить на сервер"}
              </button>
              <button
                className="btn-secondary"
                disabled={mutation.isPending}
                onClick={() => {
                  setFile(null);
                  setError(null);
                  setProgressLabel("");
                }}
              >
                Отменить
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3">
            {error}
          </div>
        )}
      </div>

      {scanResult && mode === "client" && (
        <div className="card !border-brand-200 bg-brand-50/40">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h2 className="font-semibold text-slate-900 text-lg">
                Сканирование завершено
              </h2>
              <p className="text-sm text-slate-600 mt-1">
                Найдено <strong>{scanResult.result.findings.length}</strong> ПДн •
                категория:{" "}
                <strong>
                  {{
                    strict: "Строго конфиденциально",
                    confidential: "Конфиденциально",
                    internal: "Для внутреннего использования",
                    public: "Публичный",
                  }[scanResult.result.document_category] ??
                    scanResult.result.document_category}
                </strong>
              </p>
            </div>
            <button
              onClick={() => navigate(`/scans/${scanResult.scanId}`)}
              className="btn-secondary !py-1 text-xs"
            >
              Открыть детали →
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              onClick={handleDownloadRedacted}
              className="btn-primary"
              disabled={scanResult.result.findings.length === 0}
            >
              <Download className="w-4 h-4" />
              Скачать обезличенную копию
            </button>
            <button
              onClick={handleDownloadOriginalText}
              className="btn-secondary"
            >
              <Download className="w-4 h-4" />
              Скачать извлечённый текст
            </button>
          </div>

          {scanResult.result.findings.length > 0 && (
            <p className="text-xs text-slate-500 mt-3">
              В обезличенной версии все паспорта, СНИЛС, ИНН, карты, телефоны и
              email будут заменены замаскированными значениями
              (например: <code className="font-mono">+7 (9**) ***-**-67</code>).
            </p>
          )}
        </div>
      )}

      {mode === "client" ? (
        <div className="card bg-green-50 !border-green-200">
          <h3 className="font-semibold text-green-900 mb-2 flex items-center gap-2">
            <Lock className="w-4 h-4" /> Что происходит в клиентском режиме
          </h3>
          <ol className="text-sm text-green-900/80 space-y-1 list-decimal list-inside">
            <li>Файл выбирается в браузере — никуда не загружается</li>
            <li>JavaScript извлекает текст (DOCX, PDF, XLSX, TXT, RTF)</li>
            <li>Запускается Rust-движок, скомпилированный в WebAssembly</li>
            <li>На сервер уходит только: имя файла, хеш, типы найденных ПДн и категория</li>
            <li>Сам текст и значения никогда не покидают ваше устройство</li>
          </ol>
        </div>
      ) : (
        <div className="card bg-slate-50 !border-slate-200">
          <h3 className="font-semibold text-slate-900 mb-2 flex items-center gap-2">
            <Cloud className="w-4 h-4" /> Что происходит в серверном режиме
          </h3>
          <ul className="text-sm text-slate-600 space-y-1 list-disc list-inside">
            <li>Файл шифруется AES-256-GCM и отправляется на сервер</li>
            <li>Сервер расшифровывает и парсит документ (включая OCR картинок)</li>
            <li>Применяет правила детекции и сохраняет результат</li>
            <li>Файл удаляется с сервера после обработки</li>
          </ul>
        </div>
      )}
    </div>
  );
}

interface ModeOptionProps {
  active: boolean;
  onClick: () => void;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle: string;
  badge: string;
  badgeColor: string;
}

function ModeOption({
  active,
  onClick,
  icon: Icon,
  title,
  subtitle,
  badge,
  badgeColor,
}: ModeOptionProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-left p-4 rounded-lg border-2 transition-colors ${
        active
          ? "border-brand-600 bg-brand-50/30"
          : "border-slate-200 hover:border-slate-300 bg-white"
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-5 h-5 ${active ? "text-brand-600" : "text-slate-500"}`} />
        <span className={`font-semibold ${active ? "text-brand-700" : "text-slate-900"}`}>
          {title}
        </span>
        <span className={`badge ml-auto ${badgeColor}`}>{badge}</span>
      </div>
      <p className="text-xs text-slate-600">{subtitle}</p>
    </button>
  );
}
