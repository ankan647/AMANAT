import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/api/client";
import type { ImpactPreview, RuleOut, RuleVersionOut } from "@/api/types";

export function useRules() {
  return useQuery({
    queryKey: ["rules"],
    queryFn: () => apiGet<{ data: RuleOut[] }>("/api/v1/rules"),
  });
}

export function useCreateRuleVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      ruleId: number;
      effective_from: string;
      effective_to?: string;
      applicability: Record<string, unknown>;
      parameters: Record<string, unknown>;
      note: string;
    }) =>
      apiPost<{ data: RuleVersionOut }>(`/api/v1/rules/${vars.ruleId}/versions`, {
        effective_from: vars.effective_from,
        effective_to: vars.effective_to,
        applicability: vars.applicability,
        parameters: vars.parameters,
        note: vars.note,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useImpactPreview() {
  return useMutation({
    mutationFn: (versionId: number) =>
      apiPost<{ data: ImpactPreview }>(`/api/v1/rule-versions/${versionId}/impact-preview`),
  });
}

export function useSubmitRuleVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (versionId: number) => apiPost(`/api/v1/rule-versions/${versionId}/submit`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useApproveRuleVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (versionId: number) => apiPost(`/api/v1/rule-versions/${versionId}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useRejectRuleVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { versionId: number; reason: string }) =>
      apiPost(`/api/v1/rule-versions/${vars.versionId}/reject`, { reason: vars.reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}
