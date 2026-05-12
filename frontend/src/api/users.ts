import { apiClient } from "./client";
import type { Paginated, User } from "@/types";

export interface UserDetail extends User {
  is_active: boolean;
  is_blocked: boolean;
  created_at: string;
  last_login_at: string | null;
}

export async function listUsers(
  params: {
    page?: number;
    page_size?: number;
    role?: string;
    active?: boolean;
    search?: string;
  } = {},
): Promise<Paginated<UserDetail>> {
  const resp = await apiClient.get<Paginated<UserDetail>>("/users", { params });
  return resp.data;
}

export async function getUser(id: string): Promise<UserDetail> {
  const resp = await apiClient.get<UserDetail>(`/users/${id}`);
  return resp.data;
}

export async function updateUser(
  id: string,
  body: {
    full_name?: string;
    email?: string;
    role?: string;
    is_active?: boolean;
    is_blocked?: boolean;
  },
): Promise<UserDetail> {
  const resp = await apiClient.patch<UserDetail>(`/users/${id}`, body);
  return resp.data;
}

export async function deactivateUser(id: string): Promise<void> {
  await apiClient.post(`/users/${id}/deactivate`);
}

export async function changeOwnPassword(
  current_password: string,
  new_password: string,
): Promise<void> {
  await apiClient.post("/users/me/password", { current_password, new_password });
}

export async function registerUser(body: {
  login: string;
  email: string;
  password: string;
  full_name: string;
  role: string;
}): Promise<User> {
  const resp = await apiClient.post<User>("/auth/register", body);
  return resp.data;
}
