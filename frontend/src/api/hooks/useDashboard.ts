import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/client";
import type { ActivityEvent, DashboardSummary, PriorityMatrixOut } from "@/api/types";

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => apiGet<{ data: DashboardSummary }>("/api/v1/dashboard/summary"),
  });
}

export function usePriorityMatrix() {
  return useQuery({
    queryKey: ["priority-matrix"],
    queryFn: () => apiGet<{ data: PriorityMatrixOut }>("/api/v1/dashboard/priority-matrix"),
  });
}

export function useActivity(limit = 20) {
  return useQuery({
    queryKey: ["activity", limit],
    queryFn: () => apiGet<ActivityEvent[]>("/api/v1/dashboard/activity", { limit }),
    refetchInterval: 10000,
  });
}
