import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Search, UserPlus, X } from "lucide-react";
import { useState } from "react";

import * as usersApi from "@/api/users";
import { formatDate } from "@/lib/utils";

const ROLE_LABELS: Record<string, string> = {
  admin: "Администратор",
  analyst: "Аналитик",
  user: "Пользователь",
};

export function UsersPage() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const pageSize = 20;

  const { data, isLoading } = useQuery({
    queryKey: ["users", page, search],
    queryFn: () =>
      usersApi.listUsers({
        page,
        page_size: pageSize,
        search: search || undefined,
      }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: any }) =>
      usersApi.updateUser(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => usersApi.deactivateUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Пользователи</h1>
          <p className="text-slate-500 text-sm mt-1">
            {data ? `Всего: ${data.total}` : "Загрузка..."}
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          <UserPlus className="w-4 h-4" />
          Добавить пользователя
        </button>
      </div>

      <div className="card !p-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
            placeholder="Поиск по логину, email, ФИО..."
            className="input pl-9"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="card text-center text-slate-500">Загрузка...</div>
      ) : !data || data.items.length === 0 ? (
        <div className="card text-center py-8 text-slate-500">
          Пользователи не найдены
        </div>
      ) : (
        <div className="card !p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-slate-600">
                <th className="px-4 py-3 font-medium">Логин</th>
                <th className="px-4 py-3 font-medium">ФИО</th>
                <th className="px-4 py-3 font-medium">Роль</th>
                <th className="px-4 py-3 font-medium">Статус</th>
                <th className="px-4 py-3 font-medium">Последний вход</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{u.login}</div>
                    <div className="text-xs text-slate-500">{u.email}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{u.full_name}</td>
                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      onChange={(e) =>
                        updateMutation.mutate({
                          id: u.id,
                          body: { role: e.target.value },
                        })
                      }
                      className="text-sm bg-transparent border border-slate-200 rounded px-2 py-1"
                    >
                      {Object.entries(ROLE_LABELS).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    {u.is_blocked ? (
                      <span className="badge bg-red-100 text-red-700">Заблокирован</span>
                    ) : u.is_active ? (
                      <span className="badge bg-green-100 text-green-700">Активен</span>
                    ) : (
                      <span className="badge bg-slate-100 text-slate-600">Неактивен</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatDate(u.last_login_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {u.is_active && (
                      <button
                        onClick={() => {
                          if (confirm(`Деактивировать пользователя ${u.login}?`)) {
                            deactivateMutation.mutate(u.id);
                          }
                        }}
                        className="text-xs text-red-600 hover:underline"
                      >
                        Деактивировать
                      </button>
                    )}
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

      {showCreate && (
        <CreateUserModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            qc.invalidateQueries({ queryKey: ["users"] });
          }}
        />
      )}
    </div>
  );
}

function CreateUserModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    login: "",
    email: "",
    password: "",
    full_name: "",
    role: "user",
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => usersApi.registerUser(form),
    onSuccess: onCreated,
    onError: (e: any) => {
      setError(e?.response?.data?.detail ?? "Не удалось создать пользователя");
    },
  });

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Новый пользователь</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="label">Логин</label>
            <input
              className="input"
              value={form.login}
              onChange={(e) => setForm({ ...form, login: e.target.value })}
              placeholder="ivanov"
            />
          </div>
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              className="input"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="ivanov@example.com"
            />
          </div>
          <div>
            <label className="label">ФИО</label>
            <input
              className="input"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              placeholder="Иванов Иван Иванович"
            />
          </div>
          <div>
            <label className="label">Роль</label>
            <select
              className="input"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
            >
              <option value="user">Пользователь</option>
              <option value="analyst">Аналитик</option>
              <option value="admin">Администратор</option>
            </select>
          </div>
          <div>
            <label className="label">Пароль</label>
            <input
              type="password"
              className="input"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="Минимум 12 символов, заглавная буква и цифра"
            />
          </div>

          {error && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">
              {error}
            </div>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="btn-primary flex-1"
          >
            <Check className="w-4 h-4" />
            Создать
          </button>
          <button onClick={onClose} className="btn-secondary">
            Отмена
          </button>
        </div>
      </div>
    </div>
  );
}
