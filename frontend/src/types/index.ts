// Типы данных, соответствующие схемам бекенда

export type UserRole = "admin" | "analyst" | "user";

export interface User {
  id: string;
  login: string;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type ScanStatus = "queued" | "processing" | "completed" | "failed";

export type ScanMode = "server" | "client";

export type DocumentCategory =
  | "strict"
  | "confidential"
  | "internal"
  | "public";

export type FindingType =
  | "passport"
  | "snils"
  | "inn_person"
  | "inn_org"
  | "bank_card"
  | "phone"
  | "email"
  | "date_of_birth"
  | "oms_policy"
  | "driver_license"
  | "fio"
  | "address";

export interface ScanFinding {
  id: string;
  finding_type: FindingType;
  masked_value: string;
  position_start: number | null;
  position_end: number | null;
  page_number: number | null;
  confidence: number;
  context_masked: string | null;
}

export interface Scan {
  id: string;
  user_id: string;
  original_filename: string;
  file_size_bytes: number;
  file_hash: string;
  mime_type: string;
  scan_mode: ScanMode;
  status: ScanStatus;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  processing_duration_ms: number | null;
  document_category: DocumentCategory | null;
  findings_summary: Record<string, number> | null;
  error_message: string | null;
  findings: ScanFinding[];
}

export interface ScanBrief {
  id: string;
  original_filename: string;
  file_size_bytes: number;
  scan_mode: ScanMode;
  status: ScanStatus;
  created_at: string;
  finished_at: string | null;
  document_category: DocumentCategory | null;
  findings_summary: Record<string, number> | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface OverviewStats {
  total_scans: number;
  scans_today: number;
  scans_week: number;
  scans_month: number;
  total_users: number;
  active_users_week: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_scan_mode: Record<string, number>;
}

export interface TimeSeriesPoint {
  date: string;
  scans: number;
  findings: number;
}
