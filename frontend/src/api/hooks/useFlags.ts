import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/api/client";
import type { AnomalyMetrics, FlagDetail, FlagOut } from "@/api/types";

export function useFlags(filters: { status?: string; type?: string; institution_id?: number; severity?: string }) {
  return useQuery({
    queryKey: ["flags", filters],
    queryFn: () => apiGet<{ data: FlagOut[] }>("/api/v1/flags", filters as Record<string, unknown>),
  });
}

export function useFlag(id: number | undefined) {
  return useQuery({
    queryKey: ["flag", id],
    queryFn: () => apiGet<{ data: FlagDetail }>(`/api/v1/flags/${id}`),
    enabled: id !== undefined,
  });
}

export function useFlagReferrals() {
  return useQuery({
    queryKey: ["flag-referrals"],
    queryFn: () => apiGet<{ data: FlagOut[] }>("/api/v1/flags/referrals"),
  });
}

export function useFlagOutcome() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: number; outcome: string; reason?: string }) =>
      apiPost<{ data: FlagOut }>(`/api/v1/flags/${vars.id}/outcome`, { outcome: vars.outcome, reason: vars.reason }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useAnomalyMetrics() {
  return useQuery({
    queryKey: ["anomaly-metrics"],
    queryFn: () => apiGet<{ data: AnomalyMetrics }>("/api/v1/metrics/anomalies"),
  });
}
