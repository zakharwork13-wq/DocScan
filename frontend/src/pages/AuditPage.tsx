import { useQuery } from "@tanstack/react-query";
import { Download, Filter } from "lucide-react";
import { useState } from "react";

import * as auditApi from "@/api/audit";
import { useAuthStore } from "@/store/auth";
import { formatDate } from "@/lib/utils";

const ACTION_LABELS: Record<string, string> = {
  "user.login": "Вход",
  "user.logout": "Выход",
  "user.login_failed": "Неудачная попытка входа",
  "user.created": "Создан пользователь",
  "user.updated": "Изменён пользователь",
  "scan.uploaded": "Загружен документ",
  "scan.completed": "Сканирование завершено",
  "scan.deleted": "Удалено сканирование",
  "rule.created": "Создано правило",
  "rule.updated": "Изменено правило",
  "rule.deleted": "Удалено правило",
};

export function AuditPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    action: "",
    object_type: "",
    date_from: "",
    date_to: "",
  });

  const pageSize = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["audit", page, filters],
    queryFn: () =>
      auditApi.listAuditLogs({
        page,
        page_size: pageSize,
        action: filters.action || undefined,
        object_type: filters.object_type || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
      }),
  });

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1;

  const handleExport = () => {
    const url = auditApi.exportAuditUrl({
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
    });

    // Передаём токен в заголовке через fetch + Blob (нельзя через простой <a> с авторизацией)
    fetch(url, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then((r) => r.blob())
      .then((blob) => {
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `audit_${new Date().toISOString().slice(0, 10)}.csv`;
        link.click();
      });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Журнал аудита</h1>
          <p className="text-slate-500 text-sm mt-1">
            {data ? `Всего записей: ${data.total}` : "Загрузка..."}
          </p>
        </div>
        <button onClick={handleExport} className="btn-secondary">
          <Download className="w-4 h-4" />
          Экспорт в CSV
        </button>
      </div>

      <div className="card !p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-slate-500" />
          <span className="text-sm font-medium text-slate-700">Фильтры</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="label text-xs">Действие</label>
            <input
              type="text"
              className="input"
              value={filters.action}
              onChange={(e) =>
                setFilters({ ...filters, action: e.target.value })
              }
              placeholder="user.login"
            />
          </div>
          <div>
            <label className="label text-xs">Тип объекта</label>
            <select
              className="input"
              value={filters.object_type}
              onChange={(e) =>
                setFilters({ ...filters, object_type: e.target.value })
              }
            >
              <option value="">Все</option>
              <option value="user">Пользователь</option>
              <option value="scan">Сканирование</option>
              <option value="rule">Правило</option>
            </select>
          </div>
          <div>
            <label className="label text-xs">С даты</label>
            <input
              type="datetime-local"
              className="input"
              value={filters.date_from}
              onChange={(e) =>
                setFilters({ ...filters, date_from: e.target.value })
              }
            />
          </div>
          <div>
            <label className="label text-xs">По дату</label>
            <input
              type="datetime-local"
              className="input"
              value={filters.date_to}
              onChange={(e) =>
                setFilters({ ...filters, date_to: e.target.value })
              }
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="card text-center text-slate-500">Загрузка...</div>
      ) : !data || data.items.length === 0 ? (
        <div className="card text-center py-8 text-slate-500">
          Записи не найдены
        </div>
      ) : (
        <div className="card !p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-slate-600">
                <th className="px-4 py-3 font-medium">Время</th>
                <th className="px-4 py-3 font-medium">Действие</th>
                <th className="px-4 py-3 font-medium">Объект</th>
                <th className="px-4 py-3 font-medium">IP</th>
                <th className="px-4 py-3 font-medium">Детали</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2 text-slate-600 whitespace-nowrap">
                    {formatDate(log.created_at)}
                  </td>
                  <td className="px-4 py-2">
                    <span className="font-mono text-xs text-slate-700">
                      {ACTION_LABELS[log.action] ?? log.action}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {log.object_type ? (
                      <span className="text-xs">
                        {log.object_type}
                        {log.object_id && (
                          <span className="text-slate-400 ml-1">
                            #{String(log.object_id).substring(0, 8)}
                          </span>
                        )}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-2 text-xs text-slate-500 font-mono">
                    {log.ip_address ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-xs text-slate-500 max-w-md truncate">
                    {log.details ? JSON.stringify(log.details) : "—"}
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
