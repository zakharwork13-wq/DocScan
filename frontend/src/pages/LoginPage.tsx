import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { Lock, ShieldCheck, User as UserIcon } from "lucide-react";

import * as authApi from "@/api/auth";
import { useAuthStore } from "@/store/auth";

interface LoginForm {
  login: string;
  password: string;
}

export function LoginPage() {
  const navigate = useNavigate();
  const { setTokens, setUser } = useAuthStore();

  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>();

  const onSubmit = async (data: LoginForm) => {
    setError(null);
    setSubmitting(true);
    try {
      const tokens = await authApi.login(data.login, data.password);
      setTokens(tokens.access_token, tokens.refresh_token);
      const user = await authApi.getMe();
      setUser(user);
      navigate("/scans", { replace: true });
    } catch (e: any) {
      const message =
        e?.response?.data?.detail ??
        e?.response?.data?.message ??
        "Не удалось войти. Проверьте логин и пароль.";
      setError(typeof message === "string" ? message : "Ошибка входа");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 via-white to-slate-100 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand-600 text-white shadow-lg mb-4">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900">DocScan</h1>
          <p className="text-slate-500 mt-2">Поиск персональных данных в документах</p>
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold mb-6 text-slate-900">Вход в систему</h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="label" htmlFor="login">Логин или email</label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                <input
                  id="login"
                  type="text"
                  autoComplete="username"
                  className="input pl-9"
                  placeholder="admin"
                  {...register("login", { required: "Введите логин" })}
                />
              </div>
              {errors.login && (
                <p className="text-xs text-red-600 mt-1">{errors.login.message}</p>
              )}
            </div>

            <div>
              <label className="label" htmlFor="password">Пароль</label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  className="input pl-9"
                  placeholder="••••••••"
                  {...register("password", { required: "Введите пароль" })}
                />
              </div>
              {errors.password && (
                <p className="text-xs text-red-600 mt-1">{errors.password.message}</p>
              )}
            </div>

            {error && (
              <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3">
                {error}
              </div>
            )}

            <button
              type="submit"
              className="btn-primary w-full"
              disabled={submitting}
            >
              {submitting ? "Входим..." : "Войти"}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-400 mt-6">
          © 2026 DocScan. Защищено и работает на устройстве.
        </p>
      </div>
    </div>
  );
}
