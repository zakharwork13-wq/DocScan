import { apiClient } from "./client";

export interface Rule {
  id: string;
  code: string;
  name: string;
  description: string | null;
  finding_type: string;
  pattern: string;
  validator: string | null;
  base_confidence: number;
  positive_keywords: string[] | null;
  negative_keywords: string[] | null;
  is_active: boolean;
  is_builtin: boolean;
  version: number;
  created_at: string;
  updated_at: string | null;
}

export interface RuleVersion {
  id: number;
  rule_id: string;
  version: number;
  snapshot: Record<string, unknown>;
  changed_by: string | null;
  changed_at: string;
}

export interface RuleTestResponse {
  matches: { value: string; start: number; end: number; valid: boolean }[];
  error: string | null;
}

export async function listRules(params: {
  active?: boolean;
  finding_type?: string;
} = {}): Promise<{ items: Rule[]; total: number }> {
  const resp = await apiClient.get("/rules", { params });
  return resp.data;
}

export async function createRule(body: {
  code: string;
  name: string;
  description?: string;
  finding_type: string;
  pattern: string;
  validator?: string;
  base_confidence: number;
  positive_keywords?: string[];
  negative_keywords?: string[];
  is_active: boolean;
}): Promise<Rule> {
  const resp = await apiClient.post<Rule>("/rules", body);
  return resp.data;
}

export async function updateRule(id: string, body: Partial<Rule>): Promise<Rule> {
  const resp = await apiClient.patch<Rule>(`/rules/${id}`, body);
  return resp.data;
}

export async function deleteRule(id: string): Promise<void> {
  await apiClient.delete(`/rules/${id}`);
}

export async function listRuleVersions(id: string): Promise<RuleVersion[]> {
  const resp = await apiClient.get<RuleVersion[]>(`/rules/${id}/versions`);
  return resp.data;
}

export async function testRule(
  pattern: string,
  text: string,
  validator?: string,
): Promise<RuleTestResponse> {
  const resp = await apiClient.post<RuleTestResponse>("/rules/test", {
    pattern,
    text,
    validator: validator || undefined,
  });
  return resp.data;
}
