import { apiClient } from "./client";

export interface AuditLog {
  id: number;
  user_id: string | null;
  action: string;
  object_type: string | null;
  object_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  request_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface PaginatedAudit {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export async function listAuditLogs(
  params: {
    page?: number;
    page_size?: number;
    user_id?: string;
    action?: string;
    object_type?: string;
    date_from?: string;
    date_to?: string;
  } = {},
): Promise<PaginatedAudit> {
  const resp = await apiClient.get<PaginatedAudit>("/audit", { params });
  return resp.data;
}

export function exportAuditUrl(params: {
  date_from?: string;
  date_to?: string;
}): string {
  const qs = new URLSearchParams();
  if (params.date_from) qs.set("date_from", params.date_from);
  if (params.date_to) qs.set("date_to", params.date_to);
  return `/api/v1/audit/export?${qs.toString()}`;
}
