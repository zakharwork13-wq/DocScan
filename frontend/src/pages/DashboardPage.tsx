import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  CheckCircle2,
  FileText,
  Loader2,
  TrendingUp,
  Users,
} from "lucide-react";

import * as statsApi from "@/api/stats";
import { findingTypeLabel, statusLabel } from "@/lib/utils";

export function DashboardPage() {
  const { data: overview, isLoading } = useQuery({
    queryKey: ["stats-overview"],
    queryFn: statsApi.getOverview,
  });
  const { data: topTypes } = useQuery({
    queryKey: ["stats-top-types"],
    queryFn: () => statsApi.getTopFindingTypes(8),
  });
  const { data: timeSeries } = useQuery({
    queryKey: ["stats-time-series"],
    queryFn: () => statsApi.getTimeSeries(14),
  });

  if (isLoading || !overview) {
    return (
      <div className="text-center text-slate-500 py-12">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
        Загрузка дашборда...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Дашборд</h1>
        <p className="text-slate-500 text-sm mt-1">
          Сводная статистика по всем сканированиям
        </p>
      </div>

      {/* Карточки KPI */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={FileText}
          title="Всего сканирований"
          value={overview.total_scans}
          color="brand"
        />
        <StatCard
          icon={TrendingUp}
          title="За неделю"
          value={overview.scans_week}
          color="green"
        />
        <StatCard
          icon={CheckCircle2}
          title="Сегодня"
          value={overview.scans_today}
          color="yellow"
        />
        <StatCard
          icon={Users}
          title="Активных пользователей"
          value={overview.active_users_week}
          subtitle={`из ${overview.total_users}`}
          color="purple"
        />
      </div>

      {/* Распределения */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <DistributionCard
          title="По статусам"
          data={overview.by_status}
          labeler={statusLabel}
        />
        <DistributionCard
          title="По категориям"
          data={overview.by_category}
          labeler={(k) =>
            ({
              strict: "Строго конф.",
              confidential: "Конфиденциально",
              internal: "Внутреннее",
              public: "Публичное",
            }[k] ?? k)
          }
        />
        <DistributionCard
          title="По режиму"
          data={overview.by_scan_mode}
          labeler={(k) => (k === "server" ? "Серверный" : "Клиентский")}
        />
      </div>

      {/* Топ типов находок */}
      {topTypes && topTypes.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-brand-600" />
            Топ типов найденных ПДн
          </h2>
          <div className="space-y-2">
            {topTypes.map((t) => {
              const max = Math.max(...topTypes.map((x) => x.count));
              const pct = max ? (t.count / max) * 100 : 0;
              return (
                <div key={t.finding_type} className="flex items-center gap-3">
                  <div className="w-48 text-sm text-slate-700 shrink-0">
                    {findingTypeLabel(t.finding_type)}
                  </div>
                  <div className="flex-1 bg-slate-100 h-6 rounded-md overflow-hidden">
                    <div
                      className="bg-brand-500 h-full flex items-center justify-end pr-2 text-xs font-medium text-white"
                      style={{ width: `${pct}%` }}
                    >
                      {pct > 15 ? t.count : ""}
                    </div>
                  </div>
                  {pct <= 15 && (
                    <div className="text-sm text-slate-600 w-8">{t.count}</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Временной ряд */}
      {timeSeries && timeSeries.points.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-900 mb-4">
            Активность за последние 14 дней
          </h2>
          <TimeSeriesChart points={timeSeries.points} />
        </div>
      )}
    </div>
  );
}

interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  value: number;
  subtitle?: string;
  color: "brand" | "green" | "yellow" | "purple";
}

function StatCard({ icon: Icon, title, value, subtitle, color }: StatCardProps) {
  const colors = {
    brand: "bg-brand-100 text-brand-600",
    green: "bg-green-100 text-green-600",
    yellow: "bg-yellow-100 text-yellow-600",
    purple: "bg-purple-100 text-purple-600",
  };
  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-slate-500 uppercase tracking-wide">
            {title}
          </div>
          <div className="text-3xl font-bold text-slate-900 mt-2">{value}</div>
          {subtitle && (
            <div className="text-xs text-slate-500 mt-1">{subtitle}</div>
          )}
        </div>
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

interface DistributionProps {
  title: string;
  data: Record<string, number>;
  labeler: (k: string) => string;
}

function DistributionCard({ title, data, labeler }: DistributionProps) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);

  return (
    <div className="card">
      <h3 className="font-semibold text-slate-900 mb-3">{title}</h3>
      {total === 0 ? (
        <p className="text-sm text-slate-400">Нет данных</p>
      ) : (
        <div className="space-y-2">
          {Object.entries(data).map(([k, v]) => {
            const pct = total ? Math.round((v / total) * 100) : 0;
            return (
              <div key={k}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-slate-700">{labeler(k)}</span>
                  <span className="text-slate-500">
                    {v} <span className="text-xs">({pct}%)</span>
                  </span>
                </div>
                <div className="bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-brand-500 h-full" style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TimeSeriesChart({
  points,
}: {
  points: { date: string; scans: number; findings: number }[];
}) {
  const maxScans = Math.max(...points.map((p) => p.scans), 1);

  return (
    <div className="space-y-1">
      <div className="flex items-end gap-1 h-32">
        {points.map((p) => {
          const h = (p.scans / maxScans) * 100;
          return (
            <div
              key={p.date}
              className="flex-1 group relative"
              title={`${p.date}: ${p.scans} сканирований, ${p.findings} находок`}
            >
              <div
                className="bg-brand-500 hover:bg-brand-600 rounded-t-sm transition-colors"
                style={{ height: `${Math.max(h, 2)}%` }}
              />
              <div className="hidden group-hover:block absolute -top-10 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                {p.date}: {p.scans} скан., {p.findings} нах.
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex justify-between text-xs text-slate-400 pt-1">
        <span>{points[0]?.date}</span>
        <span>{points[points.length - 1]?.date}</span>
      </div>
    </div>
  );
}
