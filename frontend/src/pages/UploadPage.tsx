import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, FileText, Upload as UploadIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";

import * as scansApi from "@/api/scans";
import { formatBytes } from "@/lib/utils";

const ACCEPTED = [
  ".doc", ".docx", ".pdf", ".xls", ".xlsx", ".txt", ".rtf",
  ".png", ".jpg", ".jpeg", ".tiff",
];

const MAX_SIZE = 50 * 1024 * 1024;

export function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const mutation = useMutation({
    mutationFn: (f: File) => scansApi.uploadScan(f),
    onSuccess: (data) => {
      navigate(`/scans/${data.id}`);
    },
    onError: (e: any) => {
      const msg =
        e?.response?.data?.detail ??
        "Не удалось загрузить файл";
      setError(typeof msg === "string" ? msg : "Ошибка загрузки");
    },
  });

  const handleFile = useCallback((f: File) => {
    setError(null);
    if (f.size > MAX_SIZE) {
      setError(`Файл превышает 50 МБ (${formatBytes(f.size)})`);
      return;
    }
    setFile(f);
  }, []);

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
          Файл будет зашифрован, обработан и удалён с сервера после анализа.
        </p>
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
              Поддерживаются: DOC, DOCX, PDF, XLS, XLSX, TXT, RTF, изображения. Макс. 50 МБ
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

            <div className="flex gap-3">
              <button
                className="btn-primary flex-1"
                disabled={mutation.isPending}
                onClick={() => mutation.mutate(file)}
              >
                {mutation.isPending ? "Загружаем..." : "Начать сканирование"}
              </button>
              <button
                className="btn-secondary"
                disabled={mutation.isPending}
                onClick={() => setFile(null)}
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

      <div className="card bg-slate-50 !border-slate-200">
        <h3 className="font-semibold text-slate-900 mb-2">Что делает система</h3>
        <ul className="text-sm text-slate-600 space-y-1 list-disc list-inside">
          <li>Извлекает текст из документа (DOCX, PDF, XLSX, TXT, RTF, изображений)</li>
          <li>Ищет ПДн граждан РФ: паспорт, СНИЛС, ИНН, банковские карты, телефоны и др.</li>
          <li>Классифицирует документ по уровню конфиденциальности</li>
          <li>Шифрует файл AES-256, удаляет его после анализа</li>
        </ul>
      </div>
    </div>
  );
}
