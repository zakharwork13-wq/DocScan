import { apiClient } from "./client";
import type { OverviewStats, TimeSeriesPoint } from "@/types";

export async function getOverview(): Promise<OverviewStats> {
  const resp = await apiClient.get<OverviewStats>("/stats/overview");
  return resp.data;
}

export async function getTimeSeries(days = 30): Promise<{
  points: TimeSeriesPoint[];
  period: string;
}> {
  const resp = await apiClient.get("/stats/time-series", { params: { days } });
  return resp.data;
}

export async function getTopFindingTypes(limit = 10): Promise<
  { finding_type: string; count: number }[]
> {
  const resp = await apiClient.get("/stats/top-finding-types", {
    params: { limit },
  });
  return resp.data;
}
