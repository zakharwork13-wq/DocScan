import { useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";

import * as authApi from "@/api/auth";
import { useAuthStore } from "@/store/auth";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function Layout() {
  const navigate = useNavigate();
  const { user, accessToken, refreshToken, setUser, logout } = useAuthStore();

  useEffect(() => {
    if (accessToken && !user) {
      authApi.getMe()
        .then(setUser)
        .catch(() => {
          logout();
          navigate("/login", { replace: true });
        });
    }
  }, [accessToken, user, setUser, logout, navigate]);

  const handleLogout = async () => {
    try {
      if (refreshToken) {
        await authApi.logout(refreshToken);
      }
    } catch {
      /* игнорируем */
    } finally {
      logout();
      navigate("/login", { replace: true });
    }
  };

  return (
    <div className="flex h-full">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar user={user} onLogout={handleLogout} />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
