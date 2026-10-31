import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/api/client";
import type { NotificationOut, ReminderOut } from "@/api/types";

export function useReminders(filters: { state?: string; instrument_id?: number }) {
  return useQuery({
    queryKey: ["reminders", filters],
    queryFn: () => apiGet<{ data: ReminderOut[] }>("/api/v1/reminders", filters as Record<string, unknown>),
  });
}

export function usePauseReminder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: number; reason: string }) =>
      apiPost(`/api/v1/reminders/${vars.id}/pause`, { reason: vars.reason }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reminders"] }),
  });
}

export function useResumeReminder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/api/v1/reminders/${id}/resume`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reminders"] }),
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: () => apiGet<{ data: NotificationOut[] }>("/api/v1/notifications"),
    refetchInterval: 15000,
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiPost(`/api/v1/notifications/${id}/read`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiPost("/api/v1/notifications/read-all"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });
}
