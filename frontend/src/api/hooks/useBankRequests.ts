import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPostForm } from "@/api/client";
import type { AcceptPreview, AcceptResult, BankRequestOut } from "@/api/types";

export function useBankRequests(filters: { status?: string; overdue?: boolean; institution_id?: number }) {
  return useQuery({
    queryKey: ["bank-requests", filters],
    queryFn: () => apiGet<{ data: BankRequestOut[] }>("/api/v1/bank-requests", filters as Record<string, unknown>),
  });
}

export function useBankRequest(id: number | undefined) {
  return useQuery({
    queryKey: ["bank-request", id],
    queryFn: () => apiGet<{ data: BankRequestOut }>(`/api/v1/bank-requests/${id}`),
    enabled: id !== undefined,
  });
}

export function useCreateBankRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { instrument_id: number; bank_name: string; branch: string }) =>
      apiPost<{ data: BankRequestOut }>("/api/v1/bank-requests", vars),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useRespondBankRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: {
      id: number;
      outcome: "confirmed" | "details_differ" | "cannot_confirm";
      differingValues?: Record<string, string>;
      remarks?: string;
      letter?: File;
    }) => {
      const form = new FormData();
      form.append("outcome", vars.outcome);
      if (vars.differingValues) form.append("differing_values", JSON.stringify(vars.differingValues));
      if (vars.remarks) form.append("remarks", vars.remarks);
      if (vars.letter) form.append("letter", vars.letter);
      return apiPostForm(`/api/v1/bank-requests/${vars.id}/respond`, form);
    },
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useAcceptPreview(id: number | undefined) {
  return useQuery({
    queryKey: ["accept-preview", id],
    queryFn: () => apiGet<{ data: AcceptPreview }>(`/api/v1/bank-requests/${id}/accept-preview`),
    enabled: id !== undefined,
  });
}

export function useAcceptBankResponse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost<{ data: AcceptResult }>(`/api/v1/bank-requests/${id}/accept`),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useRejectBankResponse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: number; reason: string }) =>
      apiPost(`/api/v1/bank-requests/${vars.id}/reject-response`, { reason: vars.reason }),
    onSuccess: () => qc.invalidateQueries(),
  });
}
