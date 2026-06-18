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

export interface ClientScanResultPayload {
  original_filename: string;
  file_size_bytes: number;
  file_hash: string;
  mime_type: string;
  document_category: string;
  findings_summary: Record<string, number>;
}

/**
 * Отправить результат клиентского сканирования.
 * Файл НЕ передаётся — только метаданные и агрегированная статистика.
 */
export async function submitClientResult(
  payload: ClientScanResultPayload,
): Promise<{ id: string; status: string }> {
  const resp = await apiClient.post<{ id: string; status: string }>(
    "/scans/client-result",
    payload,
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

export async function downloadReport(id: string, filename: string): Promise<void> {
  const resp = await apiClient.get(`/scans/${id}/report`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([resp.data]));
  const a = document.createElement("a");
  a.href = url;
  a.download = `docscan_report_${filename}.pdf`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  a.remove();
}

export async function downloadRedacted(id: string, originalFilename: string): Promise<void> {
  const resp = await apiClient.get(`/scans/${id}/redacted`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([resp.data]));
  const dot = originalFilename.lastIndexOf(".");
  const base = dot > 0 ? originalFilename.slice(0, dot) : originalFilename;
  const a = document.createElement("a");
  a.href = url;
  a.download = `${base}_обезличено.txt`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  a.remove();
}
