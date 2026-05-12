import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Clock,
  FileText,
  Hash,
  Loader2,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import * as scansApi from "@/api/scans";
import {
  categoryColor,
  categoryLabel,
  findingTypeLabel,
  formatBytes,
  formatDate,
  statusColor,
  statusLabel,
} from "@/lib/utils";

export function ScanDetailsPage() {
  const { id } = useParams<{ id: string }>();

  const { data: scan, isLoading, error } = useQuery({
    queryKey: ["scan", id],
    queryFn: () => scansApi.getScan(id!),
    enabled: !!id,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "queued" || status === "processing" ? 2000 : false;
    },
  });

  if (isLoading) {
    return (
      <div className="text-center text-slate-500 py-12">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
        Загрузка...
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className="card text-center py-12">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-3" />
        <p className="text-slate-600">Сканирование не найдено или недоступно</p>
        <Link to="/scans" className="btn-secondary mt-4 inline-flex">
          <ArrowLeft className="w-4 h-4" /> К списку
        </Link>
      </div>
    );
  }

  const totalFindings = scan.findings?.length ?? 0;
  const isProcessing = scan.status === "queued" || scan.status === "processing";

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <Link to="/scans" className="text-sm text-brand-600 hover:underline inline-flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" />
          Назад к списку
        </Link>
      </div>

      <div className="card">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3 min-w-0">
            <div className="w-12 h-12 rounded-lg bg-brand-100 flex items-center justify-center shrink-0">
              <FileText className="w-6 h-6 text-brand-600" />
            </div>
            <div className="min-w-0">
              <h1 className="text-xl font-bold text-slate-900 break-all">
                {scan.original_filename}
              </h1>
              <div className="text-sm text-slate-500 mt-1 flex items-center gap-3 flex-wrap">
                <span>{formatBytes(scan.file_size_bytes)}</span>
                <span>·</span>
                <span>{scan.mime_type}</span>
                <span>·</span>
                <span className="inline-flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatDate(scan.created_at)}
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-col items-end gap-2 shrink-0">
            <span className={`badge ${statusColor(scan.status)}`}>
              {isProcessing && <Loader2 className="w-3 h-3 animate-spin mr-1" />}
              {statusLabel(scan.status)}
            </span>
            {scan.document_category && (
              <span className={`badge ${categoryColor(scan.document_category)}`}>
                {categoryLabel(scan.document_category)}
              </span>
            )}
          </div>
        </div>

        {scan.error_message && (
          <div className="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3">
            <strong>Ошибка:</strong> {scan.error_message}
          </div>
        )}

        <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-100 text-sm">
          <div>
            <dt className="text-slate-500">Режим</dt>
            <dd className="font-medium text-slate-900 mt-0.5">
              {scan.scan_mode === "server" ? "Серверный" : "Клиентский"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Длительность</dt>
            <dd className="font-medium text-slate-900 mt-0.5">
              {scan.processing_duration_ms != null
                ? `${(scan.processing_duration_ms / 1000).toFixed(1)} с`
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Находок</dt>
            <dd className="font-medium text-slate-900 mt-0.5">{totalFindings}</dd>
          </div>
          <div className="min-w-0">
            <dt className="text-slate-500 inline-flex items-center gap-1">
              <Hash className="w-3 h-3" /> SHA-256
            </dt>
            <dd
              className="font-mono text-xs text-slate-700 mt-0.5 truncate"
              title={scan.file_hash}
            >
              {scan.file_hash.substring(0, 16)}…
            </dd>
          </div>
        </dl>
      </div>

      {scan.findings_summary && Object.keys(scan.findings_summary).length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-900 mb-4">Сводка по типам</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(scan.findings_summary).map(([type, count]) => (
              <div
                key={type}
                className="border border-slate-200 rounded-md p-3 bg-slate-50"
              >
                <div className="text-xs text-slate-500">{findingTypeLabel(type)}</div>
                <div className="text-2xl font-bold text-slate-900 mt-1">{count}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {scan.findings && scan.findings.length > 0 && (
        <div className="card !p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200">
            <h2 className="font-semibold text-slate-900">
              Найденные данные ({scan.findings.length})
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Значения замаскированы; полный текст остаётся только в исходном файле.
            </p>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-slate-600">
                <th className="px-4 py-2 font-medium">Тип</th>
                <th className="px-4 py-2 font-medium">Значение</th>
                <th className="px-4 py-2 font-medium">Контекст</th>
                <th className="px-4 py-2 font-medium">Уверенность</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {scan.findings.map((f) => (
                <tr key={f.id}>
                  <td className="px-4 py-2">
                    <span className="badge bg-slate-100 text-slate-700">
                      {findingTypeLabel(f.finding_type)}
                    </span>
                  </td>
                  <td className="px-4 py-2 font-mono text-slate-900">
                    {f.masked_value}
                  </td>
                  <td className="px-4 py-2 text-slate-600 text-xs max-w-xs truncate">
                    {f.context_masked ?? "—"}
                  </td>
                  <td className="px-4 py-2">
                    <ConfidenceBar value={f.confidence} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {scan.status === "completed" && totalFindings === 0 && (
        <div className="card text-center py-8">
          <p className="text-slate-600">Персональные данные не обнаружены.</p>
        </div>
      )}
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    value >= 0.85 ? "bg-green-500" : value >= 0.6 ? "bg-yellow-500" : "bg-orange-500";
  return (
    <div className="flex items-center gap-2 min-w-[100px]">
      <div className="flex-1 bg-slate-100 h-1.5 rounded-full overflow-hidden">
        <div className={`${color} h-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-600 w-8 text-right">{pct}%</span>
    </div>
  );
}
