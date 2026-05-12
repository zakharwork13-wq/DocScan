import { apiClient } from "./client";
import type { TokenResponse, User } from "@/types";

export async function login(
  loginOrEmail: string,
  password: string,
): Promise<TokenResponse> {
  const resp = await apiClient.post<TokenResponse>("/auth/login", {
    login: loginOrEmail,
    password,
  });
  return resp.data;
}

export async function logout(refreshToken: string): Promise<void> {
  await apiClient.post("/auth/logout", { refresh_token: refreshToken });
}

export async function getMe(): Promise<User> {
  const resp = await apiClient.get<User>("/auth/me");
  return resp.data;
}
