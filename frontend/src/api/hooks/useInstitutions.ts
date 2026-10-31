import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/client";
import type {
  CoverageTimeline,
  InstitutionDetail,
  InstitutionListResponse,
  WhyRule,
} from "@/api/types";

export interface InstitutionFilters {
  status?: string;
  state?: string;
  category?: string;
  matrix_cell?: string;
  confidence_lt?: number;
  q?: string;
  page?: number;
  page_size?: number;
}

export function useInstitutions(filters: InstitutionFilters) {
  return useQuery({
    queryKey: ["institutions", filters],
    queryFn: () => apiGet<InstitutionListResponse>("/api/v1/institutions", filters as Record<string, unknown>),
  });
}

export function useInstitution(id: number | undefined) {
  return useQuery({
    queryKey: ["institution", id],
    queryFn: () => apiGet<{ data: InstitutionDetail }>(`/api/v1/institutions/${id}`),
    enabled: id !== undefined,
  });
}

export function useCoverageTimeline(id: number | undefined) {
  return useQuery({
    queryKey: ["coverage-timeline", id],
    queryFn: () => apiGet<{ data: CoverageTimeline }>(`/api/v1/institutions/${id}/coverage-timeline`),
    enabled: id !== undefined,
  });
}

export function useWhyRule(id: number | undefined) {
  return useQuery({
    queryKey: ["why-rule", id],
    queryFn: () => apiGet<{ data: WhyRule }>(`/api/v1/institutions/${id}/why-rule`),
    enabled: id !== undefined,
  });
}
