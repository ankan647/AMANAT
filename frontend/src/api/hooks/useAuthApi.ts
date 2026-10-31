import { useMutation, useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/api/client";
import type { AuthUser } from "@/api/auth";
import type { DemoAccount } from "@/api/types";

interface LoginResponse {
  data: { access_token: string; token_type: string; expires_in: number; user: AuthUser };
}

export function useLogin() {
  return useMutation({
    mutationFn: (vars: { email: string; password: string }) =>
      apiPost<LoginResponse>("/api/v1/auth/login", vars),
  });
}

export function useDemoAccounts() {
  return useQuery({
    queryKey: ["demo-accounts"],
    queryFn: () => apiGet<DemoAccount[]>("/api/v1/auth/demo-accounts"),
  });
}

export function useMe(enabled: boolean) {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiGet<{ data: AuthUser }>("/api/v1/auth/me"),
    enabled,
  });
}
