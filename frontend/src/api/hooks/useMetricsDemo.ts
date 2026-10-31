import { useMutation, useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/api/client";
import type { DemoScenario, KpiOut } from "@/api/types";

export function useKpis() {
  return useQuery({
    queryKey: ["kpis"],
    queryFn: () => apiGet<{ data: KpiOut }>("/api/v1/metrics/kpis"),
  });
}

export function useDemoScenarios() {
  return useQuery({
    queryKey: ["demo-scenarios"],
    queryFn: () => apiGet<DemoScenario[]>("/api/v1/demo/scenarios"),
  });
}

export function useResetDemo() {
  return useMutation({
    mutationFn: () => apiPost("/api/v1/demo/reset"),
  });
}
