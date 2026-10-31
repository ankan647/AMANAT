import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/api/client";
import type { ClockAdvanceResult, ClockOut } from "@/api/types";

export function useClock() {
  return useQuery({
    queryKey: ["clock"],
    queryFn: () => apiGet<{ data: ClockOut }>("/api/v1/clock"),
    refetchInterval: 15000,
  });
}

export function useAdvanceClock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (days: number) => apiPost<{ data: ClockAdvanceResult }>("/api/v1/clock/advance", { days }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useSetClock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (date: string) => apiPost<{ data: ClockAdvanceResult }>("/api/v1/clock/set", { date }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useResetClock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost<{ data: ClockAdvanceResult }>("/api/v1/clock/reset"),
    onSuccess: () => qc.invalidateQueries(),
  });
}
