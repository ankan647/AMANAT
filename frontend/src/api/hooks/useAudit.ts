import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/api/client";
import type { AuditAnchorOut, AuditEntry, AuditVerifyResult } from "@/api/types";

export function useAuditLog(filters: { entity_type?: string; actor_id?: number }) {
  return useQuery({
    queryKey: ["audit-log", filters],
    queryFn: () => apiGet<{ data: AuditEntry[] }>("/api/v1/audit", filters as Record<string, unknown>),
  });
}

export function useVerifyAudit() {
  return useMutation({
    mutationFn: () => apiPost<{ data: AuditVerifyResult }>("/api/v1/audit/verify"),
  });
}

export function useAnchorNow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost("/api/v1/audit/anchor"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["anchors"] }),
  });
}

export function useAnchors() {
  return useQuery({
    queryKey: ["anchors"],
    queryFn: () => apiGet<{ data: AuditAnchorOut[] }>("/api/v1/audit/anchors"),
  });
}

export function useDevTamper() {
  return useMutation({
    mutationFn: (vars: { seq: number; new_details: Record<string, unknown> }) =>
      apiPost("/api/v1/audit/dev/tamper", vars),
  });
}

export function useDevRestore() {
  return useMutation({
    mutationFn: (vars: { seq: number; original_details: Record<string, unknown> }) =>
      apiPost("/api/v1/audit/dev/restore", vars),
  });
}
