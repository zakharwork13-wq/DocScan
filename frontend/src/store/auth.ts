import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { User } from "@/types";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;

  setTokens: (access: string, refresh: string) => void;
  setAccessToken: (access: string) => void;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,

      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh }),
      setAccessToken: (access) => set({ accessToken: access }),
      setUser: (user) => set({ user }),
      logout: () =>
        set({ accessToken: null, refreshToken: null, user: null }),
    }),
    { name: "docscan-auth" },
  ),
);

export function isAdmin(role?: string | null): boolean {
  return role === "admin";
}

export function isAnalystOrAdmin(role?: string | null): boolean {
  return role === "admin" || role === "analyst";
}
