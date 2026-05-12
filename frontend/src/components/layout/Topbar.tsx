import { LogOut } from "lucide-react";

import type { User } from "@/types";

interface Props {
  user: User | null;
  onLogout: () => void;
}

const roleLabels: Record<string, string> = {
  admin: "Администратор",
  analyst: "Аналитик",
  user: "Пользователь",
};

export function Topbar({ user, onLogout }: Props) {
  return (
    <header className="bg-white border-b border-slate-200 px-6 h-14 flex items-center justify-between">
      <div className="text-sm text-slate-500">
        {/* Здесь можно показывать хлебные крошки */}
      </div>

      <div className="flex items-center gap-4">
        {user && (
          <div className="text-right">
            <div className="text-sm font-medium text-slate-900">
              {user.full_name || user.login}
            </div>
            <div className="text-xs text-slate-500">
              {roleLabels[user.role] ?? user.role}
            </div>
          </div>
        )}
        <button
          onClick={onLogout}
          className="btn-secondary !p-2"
          title="Выйти"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
