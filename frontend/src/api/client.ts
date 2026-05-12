import axios, { AxiosError, type AxiosRequestConfig } from "axios";

import { useAuthStore } from "@/store/auth";

export const apiClient = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

// Запросы: подставляем access-токен
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Ответы: при 401 пробуем refresh
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = useAuthStore.getState().refreshToken;
  if (!refreshToken) return null;

  try {
    const resp = await axios.post(
      "/api/v1/auth/refresh",
      { refresh_token: refreshToken },
      { headers: { "Content-Type": "application/json" } },
    );
    const newAccess = resp.data.access_token as string;
    useAuthStore.getState().setAccessToken(newAccess);
    return newAccess;
  } catch {
    useAuthStore.getState().logout();
    return null;
  }
}

apiClient.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    const original = error.config as AxiosRequestConfig & { _retry?: boolean };

    if (
      error.response?.status === 401 &&
      !original?._retry &&
      !original?.url?.includes("/auth/")
    ) {
      original._retry = true;

      refreshPromise = refreshPromise ?? refreshAccessToken();
      const newToken = await refreshPromise;
      refreshPromise = null;

      if (newToken) {
        original.headers = original.headers ?? {};
        (original.headers as Record<string, string>).Authorization =
          `Bearer ${newToken}`;
        return apiClient.request(original);
      }
    }

    return Promise.reject(error);
  },
);
