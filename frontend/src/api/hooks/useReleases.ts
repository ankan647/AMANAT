import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/api/client";
import type { HoldOut, PrecheckResult, ReleaseDetail, ReleaseOut } from "@/api/types";

export function useReleases(filters: { status?: string }) {
  return useQuery({
    queryKey: ["releases", filters],
    queryFn: () => apiGet<{ data: ReleaseOut[] }>("/api/v1/releases", filters as Record<string, unknown>),
  });
}

export function useRelease(id: number | undefined) {
  return useQuery({
    queryKey: ["release", id],
    queryFn: () => apiGet<{ data: ReleaseDetail }>(`/api/v1/releases/${id}`),
    enabled: id !== undefined,
  });
}

export function usePrecheck(id: number | undefined) {
  return useQuery({
    queryKey: ["precheck", id],
    queryFn: () => apiGet<{ data: PrecheckResult }>(`/api/v1/releases/${id}/precheck`),
    enabled: id !== undefined,
  });
}

export function useCreateRelease() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { instrument_id: number; reason: string }) =>
      apiPost<{ data: ReleaseOut }>("/api/v1/releases", vars),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["releases"] }),
  });
}

export function useApproveRelease() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: number; remarks: string }) =>
      apiPost(`/api/v1/releases/${vars.id}/approve`, { remarks: vars.remarks }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useRejectRelease() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: number; reason: string }) =>
      apiPost(`/api/v1/releases/${vars.id}/reject`, { reason: vars.reason }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useHolds() {
  return useQuery({
    queryKey: ["holds"],
    queryFn: () => apiGet<{ data: HoldOut[] }>("/api/v1/holds"),
  });
}

export function useCreateHold() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { institution_id?: number; instrument_id?: number; reason: string; source: string }) =>
      apiPost<{ data: HoldOut }>("/api/v1/holds", vars),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holds"] }),
  });
}

export function useLiftHold() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/api/v1/holds/${id}/lift`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holds"] }),
  });
}
