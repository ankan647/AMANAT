import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/api/client";
import type { OrderOut, PublicOrder } from "@/api/types";

export function useOrder(id: number | undefined) {
  return useQuery({
    queryKey: ["order", id],
    queryFn: () => apiGet<{ data: OrderOut }>(`/api/v1/orders/${id}`),
    enabled: id !== undefined,
  });
}

export function useRevokeOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: number; reason: string }) => apiPost(`/api/v1/orders/${vars.id}/revoke`, { reason: vars.reason }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function usePublicOrder(orderNo: string | undefined) {
  return useQuery({
    queryKey: ["public-order", orderNo],
    queryFn: () => apiGet<{ data: PublicOrder }>(`/api/v1/public/orders/${orderNo}`),
    enabled: !!orderNo,
    retry: false,
  });
}

export function usePublicSigningKey() {
  return useQuery({
    queryKey: ["public-signing-key"],
    queryFn: () => apiGet<{ data: { algorithm: string; public_key_b64: string; demo_key: boolean } }>("/api/v1/public/signing-key"),
  });
}

export function usePublicVerifyPayload() {
  return useMutation({
    mutationFn: (vars: { payload: Record<string, unknown>; signature_b64: string }) =>
      apiPost<{ data: { signature_valid: boolean } }>("/api/v1/public/orders/verify", vars),
  });
}
