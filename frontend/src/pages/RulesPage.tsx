import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle, FlaskConical, Lock, Pencil, Plus, Trash2, X, XCircle } from "lucide-react";
import { useState } from "react";

import * as rulesApi from "@/api/rules";
import { findingTypeLabel } from "@/lib/utils";

export function RulesPage() {
  const qc = useQueryClient();
  const [editingRule, setEditingRule] = useState<rulesApi.Rule | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [testing, setTesting] = useState<rulesApi.Rule | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["rules"],
    queryFn: () => rulesApi.listRules(),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      rulesApi.updateRule(id, { is_active: active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => rulesApi.deleteRule(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Правила детекции</h1>
          <p className="text-slate-500 text-sm mt-1">
            {data ? `Всего: ${data.total}` : "Загрузка..."}
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          <Plus className="w-4 h-4" />
          Создать правило
        </button>
      </div>

      {isLoading ? (
        <div className="card text-center text-slate-500">Загрузка...</div>
      ) : (
        <div className="card !p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-slate-600">
                <th className="px-4 py-3 font-medium">Код</th>
                <th className="px-4 py-3 font-medium">Название</th>
                <th className="px-4 py-3 font-medium">Тип</th>
                <th className="px-4 py-3 font-medium">Уверенность</th>
                <th className="px-4 py-3 font-medium">Активно</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono text-xs">
                    <div className="flex items-center gap-2">
                      {r.code}
                      {r.is_builtin && (
                        <Lock className="w-3 h-3 text-slate-400" />
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-900">{r.name}</td>
                  <td className="px-4 py-3">
                    <span className="badge bg-slate-100 text-slate-700">
                      {findingTypeLabel(r.finding_type)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {(r.base_confidence * 100).toFixed(0)}%
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() =>
                        toggleMutation.mutate({ id: r.id, active: !r.is_active })
                      }
                      className="text-2xl leading-none"
                    >
                      {r.is_active ? (
                        <CheckCircle className="w-5 h-5 text-green-600" />
                      ) : (
                        <XCircle className="w-5 h-5 text-slate-300" />
                      )}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setTesting(r)}
                        className="text-slate-500 hover:text-brand-600"
                        title="Тестировать"
                      >
                        <FlaskConical className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setEditingRule(r)}
                        className="text-slate-500 hover:text-brand-600"
                        title="Редактировать"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      {!r.is_builtin && (
                        <button
                          onClick={() => {
                            if (confirm(`Удалить правило "${r.name}"?`)) {
                              deleteMutation.mutate(r.id);
                            }
                          }}
                          className="text-slate-500 hover:text-red-600"
                          title="Удалить"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(showCreate || editingRule) && (
        <RuleEditorModal
          rule={editingRule}
          onClose={() => {
            setShowCreate(false);
            setEditingRule(null);
          }}
          onSaved={() => {
            setShowCreate(false);
            setEditingRule(null);
            qc.invalidateQueries({ queryKey: ["rules"] });
          }}
        />
      )}

      {testing && (
        <RuleTestModal rule={testing} onClose={() => setTesting(null)} />
      )}
    </div>
  );
}

function RuleEditorModal({
  rule,
  onClose,
  onSaved,
}: {
  rule: rulesApi.Rule | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    code: rule?.code ?? "",
    name: rule?.name ?? "",
    description: rule?.description ?? "",
    finding_type: rule?.finding_type ?? "phone",
    pattern: rule?.pattern ?? "",
    validator: rule?.validator ?? "",
    base_confidence: rule?.base_confidence ?? 0.7,
    positive_keywords: rule?.positive_keywords?.join(", ") ?? "",
    negative_keywords: rule?.negative_keywords?.join(", ") ?? "",
    is_active: rule?.is_active ?? true,
  });
  const [error, setError] = useState<string | null>(null);

  const isNew = !rule;
  const isBuiltin = rule?.is_builtin ?? false;

  const mutation = useMutation({
    mutationFn: async () => {
      const body = {
        ...form,
        positive_keywords: form.positive_keywords
          ? form.positive_keywords.split(",").map((s) => s.trim()).filter(Boolean)
          : undefined,
        negative_keywords: form.negative_keywords
          ? form.negative_keywords.split(",").map((s) => s.trim()).filter(Boolean)
          : undefined,
        validator: form.validator || undefined,
      };

      if (isNew) {
        await rulesApi.createRule(body);
      } else {
        await rulesApi.updateRule(rule!.id, body);
      }
    },
    onSuccess: onSaved,
    onError: (e: any) => {
      setError(e?.response?.data?.detail ?? "Не удалось сохранить");
    },
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-auto">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6 my-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">
            {isNew ? "Новое правило" : `Правило: ${rule!.code}`}
            {isBuiltin && (
              <span className="ml-2 text-xs font-normal text-slate-500">
                (встроенное — паттерн нельзя менять)
              </span>
            )}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Код</label>
            <input
              className="input"
              value={form.code}
              disabled={!isNew}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="passport_rf"
            />
          </div>
          <div>
            <label className="label">Тип находки</label>
            <select
              className="input"
              value={form.finding_type}
              onChange={(e) => setForm({ ...form, finding_type: e.target.value })}
            >
              {["passport", "snils", "inn_person", "inn_org", "bank_card",
                "phone", "email", "date_of_birth", "oms_policy", "driver_license",
                "fio", "address"].map((t) => (
                <option key={t} value={t}>
                  {findingTypeLabel(t)}
                </option>
              ))}
            </select>
          </div>
          <div className="col-span-2">
            <label className="label">Название</label>
            <input
              className="input"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div className="col-span-2">
            <label className="label">Описание</label>
            <input
              className="input"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <div className="col-span-2">
            <label className="label">Регулярное выражение</label>
            <input
              className="input font-mono text-xs"
              value={form.pattern}
              disabled={isBuiltin}
              onChange={(e) => setForm({ ...form, pattern: e.target.value })}
              placeholder="\b\d{4}[\s\-]\d{6}\b"
            />
          </div>
          <div>
            <label className="label">Валидатор</label>
            <select
              className="input"
              value={form.validator}
              onChange={(e) => setForm({ ...form, validator: e.target.value })}
            >
              <option value="">Нет</option>
              <option value="snils">СНИЛС</option>
              <option value="inn_person">ИНН физ. лица</option>
              <option value="inn_org">ИНН организации</option>
              <option value="luhn">Алгоритм Луна</option>
            </select>
          </div>
          <div>
            <label className="label">
              Базовая уверенность: {(form.base_confidence * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={form.base_confidence}
              onChange={(e) =>
                setForm({ ...form, base_confidence: parseFloat(e.target.value) })
              }
              className="w-full"
            />
          </div>
          <div className="col-span-2">
            <label className="label">Позитивные ключевые слова (через запятую)</label>
            <input
              className="input"
              value={form.positive_keywords}
              onChange={(e) =>
                setForm({ ...form, positive_keywords: e.target.value })
              }
              placeholder="паспорт, серия, выдан"
            />
          </div>
          <div className="col-span-2">
            <label className="label">Негативные ключевые слова (через запятую)</label>
            <input
              className="input"
              value={form.negative_keywords}
              onChange={(e) =>
                setForm({ ...form, negative_keywords: e.target.value })
              }
              placeholder="договор, акт, счёт"
            />
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            <label htmlFor="is_active" className="text-sm text-slate-700">
              Правило активно
            </label>
          </div>
        </div>

        {error && (
          <div className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">
            {error}
          </div>
        )}

        <div className="flex gap-3 mt-6">
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="btn-primary flex-1"
          >
            {isNew ? "Создать" : "Сохранить"}
          </button>
          <button onClick={onClose} className="btn-secondary">
            Отмена
          </button>
        </div>
      </div>
    </div>
  );
}

function RuleTestModal({
  rule,
  onClose,
}: {
  rule: rulesApi.Rule;
  onClose: () => void;
}) {
  const [text, setText] = useState(
    "Иванов Иван Иванович, паспорт 4507 123456, телефон +7 (999) 123-45-67",
  );
  const [result, setResult] = useState<rulesApi.RuleTestResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      rulesApi.testRule(rule.pattern, text, rule.validator ?? undefined),
    onSuccess: (r) => setResult(r),
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Тест правила: {rule.name}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="label">Паттерн</label>
            <div className="bg-slate-50 p-2 rounded font-mono text-xs text-slate-700">
              {rule.pattern}
            </div>
          </div>

          <div>
            <label className="label">Тестовый текст</label>
            <textarea
              rows={5}
              className="input font-mono text-sm"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </div>

          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="btn-primary"
          >
            <FlaskConical className="w-4 h-4" />
            Запустить проверку
          </button>

          {result && (
            <div className="border border-slate-200 rounded p-3 bg-slate-50">
              {result.error ? (
                <div className="text-red-700 text-sm">{result.error}</div>
              ) : result.matches.length === 0 ? (
                <div className="text-slate-500 text-sm">Совпадений не найдено</div>
              ) : (
                <div className="space-y-1">
                  <div className="text-sm font-medium text-slate-700 mb-2">
                    Найдено: {result.matches.length}
                  </div>
                  {result.matches.map((m, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 text-sm bg-white border border-slate-200 rounded px-2 py-1"
                    >
                      <span className="font-mono">{m.value}</span>
                      <span className="text-xs text-slate-400">
                        [{m.start}—{m.end}]
                      </span>
                      {m.valid ? (
                        <CheckCircle className="w-4 h-4 text-green-600 ml-auto" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-500 ml-auto" />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
