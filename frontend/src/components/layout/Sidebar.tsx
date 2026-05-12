import { BarChart3, FileText, ShieldCheck, Upload } from "lucide-react";
import { NavLink } from "react-router-dom";

import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/utils";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: string[];
}

const navItems: NavItem[] = [
  { to: "/scans", label: "Сканирования", icon: FileText },
  { to: "/upload", label: "Загрузить", icon: Upload },
  { to: "/dashboard", label: "Дашборд", icon: BarChart3, roles: ["admin", "analyst"] },
];

export function Sidebar() {
  const user = useAuthStore((s) => s.user);

  return (
    <aside className="w-60 bg-slate-900 text-slate-100 flex flex-col">
      <div className="px-6 py-5 border-b border-slate-800 flex items-center gap-3">
        <ShieldCheck className="w-7 h-7 text-brand-500" />
        <div>
          <div className="font-bold text-lg leading-none">DocScan</div>
          <div className="text-xs text-slate-400 mt-1">v1.0</div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          if (item.roles && !item.roles.includes(user?.role ?? "")) {
            return null;
          }
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-600 text-white"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white",
                )
              }
            >
              <Icon className="w-4 h-4" />
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      <div className="px-4 py-3 border-t border-slate-800 text-xs text-slate-500">
        Защищено и работает на устройстве
      </div>
    </aside>
  );
}
