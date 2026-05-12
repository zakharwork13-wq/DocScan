import { useMutation } from "@tanstack/react-query";
import { Lock, Save, User as UserIcon } from "lucide-react";
import { useState } from "react";

import * as usersApi from "@/api/users";
import { useAuthStore } from "@/store/auth";
import { toast } from "@/store/notifications";

const ROLE_LABELS: Record<string, string> = {
  admin: "Администратор",
  analyst: "Аналитик",
  user: "Пользователь",
};

export function ProfilePage() {
  const user = useAuthStore((s) => s.user);

  const [pw, setPw] = useState({ current: "", new1: "", new2: "" });
  const [pwError, setPwError] = useState<string | null>(null);

  const pwMutation = useMutation({
    mutationFn: () => usersApi.changeOwnPassword(pw.current, pw.new1),
    onSuccess: () => {
      toast({ type: "success", title: "Пароль изменён" });
      setPw({ current: "", new1: "", new2: "" });
      setPwError(null);
    },
    onError: (e: any) => {
      setPwError(e?.response?.data?.detail ?? "Не удалось сменить пароль");
    },
  });

  const handleChangePassword = () => {
    setPwError(null);
    if (pw.new1.length < 12) {
      setPwError("Пароль должен содержать минимум 12 символов");
      return;
    }
    if (!/[A-Z]/.test(pw.new1)) {
      setPwError("Пароль должен содержать заглавную букву");
      return;
    }
    if (!/[0-9]/.test(pw.new1)) {
      setPwError("Пароль должен содержать цифру");
      return;
    }
    if (pw.new1 !== pw.new2) {
      setPwError("Пароли не совпадают");
      return;
    }
    pwMutation.mutate();
  };

  if (!user) {
    return <div className="card text-center text-slate-500">Загрузка...</div>;
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Мой профиль</h1>
        <p className="text-slate-500 text-sm mt-1">
          Данные учётной записи и смена пароля
        </p>
      </div>

      <div className="card">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 rounded-full bg-brand-100 text-brand-600 flex items-center justify-center">
            <UserIcon className="w-7 h-7" />
          </div>
          <div>
            <div className="font-semibold text-lg">{user.full_name}</div>
            <div className="text-sm text-slate-500">{user.email}</div>
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-4 text-sm border-t border-slate-100 pt-4">
          <div>
            <dt className="text-slate-500">Логин</dt>
            <dd className="font-medium text-slate-900 mt-0.5">{user.login}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Роль</dt>
            <dd className="font-medium text-slate-900 mt-0.5">
              {ROLE_LABELS[user.role] ?? user.role}
            </dd>
          </div>
        </dl>
      </div>

      <div className="card">
        <h2 className="font-semibold text-slate-900 flex items-center gap-2 mb-4">
          <Lock className="w-5 h-5 text-brand-600" />
          Сменить пароль
        </h2>

        <div className="space-y-3">
          <div>
            <label className="label">Текущий пароль</label>
            <input
              type="password"
              className="input"
              value={pw.current}
              onChange={(e) => setPw({ ...pw, current: e.target.value })}
              autoComplete="current-password"
            />
          </div>
          <div>
            <label className="label">Новый пароль</label>
            <input
              type="password"
              className="input"
              value={pw.new1}
              onChange={(e) => setPw({ ...pw, new1: e.target.value })}
              autoComplete="new-password"
              placeholder="Минимум 12 символов, заглавная буква и цифра"
            />
          </div>
          <div>
            <label className="label">Повторите новый пароль</label>
            <input
              type="password"
              className="input"
              value={pw.new2}
              onChange={(e) => setPw({ ...pw, new2: e.target.value })}
              autoComplete="new-password"
            />
          </div>

          {pwError && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">
              {pwError}
            </div>
          )}

          <button
            onClick={handleChangePassword}
            disabled={pwMutation.isPending || !pw.current || !pw.new1 || !pw.new2}
            className="btn-primary"
          >
            <Save className="w-4 h-4" />
            {pwMutation.isPending ? "Сохраняем..." : "Сменить пароль"}
          </button>
        </div>
      </div>
    </div>
  );
}
