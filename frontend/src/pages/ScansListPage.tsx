import { useQuery } from "@tanstack/react-query";
import { FileText, Upload } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import * as scansApi from "@/api/scans";
import {
  categoryColor,
  categoryLabel,
  formatBytes,
  formatDate,
  statusColor,
  statusLabel,
} from "@/lib/utils";

export function ScansListPage() {
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const { data, isLoading, error } = useQuery({
    queryKey: ["scans", page],
    queryFn: () => scansApi.listScans({ page, page_size: pageSize }),
    refetchInterval: 5000, // обновляем каждые 5 секунд для статусов
  });

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Сканирования</h1>
          <p className="text-slate-500 text-sm mt-1">
            {data ? `Всего: ${data.total}` : "Загрузка..."}
          </p>
        </div>
        <Link to="/upload" className="btn-primary">
          <Upload className="w-4 h-4" />
          Загрузить документ
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-md text-sm">
          Не удалось загрузить список сканирований.
        </div>
      )}

      {isLoading ? (
        <div className="card text-center text-slate-500">Загрузка...</div>
      ) : !data || data.items.length === 0 ? (
        <div className="card text-center py-12">
          <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500">Ещё нет сканирований.</p>
          <Link to="/upload" className="btn-primary mt-4 inline-flex">
            Загрузить первый документ
          </Link>
        </div>
      ) : (
        <div className="card !p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-slate-600">
                <th className="px-4 py-3 font-medium">Файл</th>
                <th className="px-4 py-3 font-medium">Категория</th>
                <th className="px-4 py-3 font-medium">Статус</th>
                <th className="px-4 py-3 font-medium">Размер</th>
                <th className="px-4 py-3 font-medium">Загружен</th>
                <th className="px-4 py-3 font-medium">Находки</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3">
                    <Link
                      to={`/scans/${s.id}`}
                      className="font-medium text-brand-700 hover:underline"
                    >
                      {s.original_filename}
                    </Link>
                    <div className="text-xs text-slate-400 mt-0.5">
                      {s.scan_mode === "server" ? "Серверное" : "Клиентское"}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`badge ${categoryColor(s.document_category)}`}>
                      {categoryLabel(s.document_category)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`badge ${statusColor(s.status)}`}>
                      {statusLabel(s.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatBytes(s.file_size_bytes)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatDate(s.created_at)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {s.findings_summary
                      ? Object.values(s.findings_summary).reduce((a, b) => a + b, 0)
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="border-t border-slate-200 px-4 py-3 flex items-center justify-between">
              <div className="text-sm text-slate-500">
                Страница {page} из {totalPages}
              </div>
              <div className="flex gap-2">
                <button
                  className="btn-secondary !py-1"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Назад
                </button>
                <button
                  className="btn-secondary !py-1"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Вперёд
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
