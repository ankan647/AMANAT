import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPostForm } from "@/api/client";
import type { InstrumentDetail, QueueRow } from "@/api/types";

export function useInstrument(id: number | undefined) {
  return useQuery({
    queryKey: ["instrument", id],
    queryFn: () => apiGet<{ data: InstrumentDetail }>(`/api/v1/instruments/${id}`),
    enabled: id !== undefined,
  });
}

export function useVerificationQueue() {
  return useQuery({
    queryKey: ["verification-queue"],
    queryFn: () => apiGet<QueueRow[]>("/api/v1/verification-queue"),
  });
}

export interface LodgeFdrInput {
  institution_id: number;
  fdr_number: string;
  bank_name: string;
  branch: string;
  ifsc: string;
  amount_paise: number;
  issue_date: string;
  maturity_date: string;
  beneficiary: string;
  lien_text: string;
}

export function useLodgeInstrument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ fdr, documents }: { fdr: LodgeFdrInput; documents: File[] }) => {
      const form = new FormData();
      form.append("fdr", JSON.stringify(fdr));
      documents.forEach((doc) => form.append("documents", doc));
      return apiPostForm<{ data: unknown }>("/api/v1/instruments", form);
    },
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useLinkRenewal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ instrumentId, previousInstrumentId }: { instrumentId: number; previousInstrumentId: number }) =>
      apiPost(`/api/v1/instruments/${instrumentId}/link-renewal`, { previous_instrument_id: previousInstrumentId }),
    onSuccess: () => qc.invalidateQueries(),
  });
}
