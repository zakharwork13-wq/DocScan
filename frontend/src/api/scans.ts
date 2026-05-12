import { apiClient } from "./client";
import type { Paginated, Scan, ScanBrief } from "@/types";

export async function uploadScan(file: File): Promise<{ id: string; status: string }> {
  const formData = new FormData();
  formData.append("file", file);
  const resp = await apiClient.post<{ id: string; status: string }>(
    "/scans/upload",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return resp.data;
}

export async function listScans(
  params: {
    page?: number;
    page_size?: number;
    status?: string;
    category?: string;
  } = {},
): Promise<Paginated<ScanBrief>> {
  const resp = await apiClient.get<Paginated<ScanBrief>>("/scans", { params });
  return resp.data;
}

export async function getScan(id: string): Promise<Scan> {
  const resp = await apiClient.get<Scan>(`/scans/${id}`);
  return resp.data;
}

export async function getScanStatus(id: string): Promise<{ id: string; status: string }> {
  const resp = await apiClient.get<{ id: string; status: string }>(
    `/scans/${id}/status`,
  );
  return resp.data;
}

export async function deleteScan(id: string): Promise<void> {
  await apiClient.delete(`/scans/${id}`);
}
