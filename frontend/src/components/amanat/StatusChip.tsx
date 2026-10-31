import { cn } from "@/lib/utils";

const PALETTE: Record<string, string> = {
  high: "text-rose-600 bg-rose-50 border-rose-200 dark:bg-rose-950/40 dark:border-rose-900",
  medium: "text-amber-600 bg-amber-50 border-amber-200 dark:bg-amber-950/40 dark:border-amber-900",
  low: "text-slate-600 bg-slate-100 border-slate-200 dark:bg-slate-900 dark:border-slate-700",
  open: "text-rose-600 bg-rose-50 border-rose-200 dark:bg-rose-950/40 dark:border-rose-900",
  cleared: "text-emerald-600 bg-emerald-50 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-900",
  returned: "text-amber-600 bg-amber-50 border-amber-200 dark:bg-amber-950/40 dark:border-amber-900",
  referred: "text-purple-600 bg-purple-50 border-purple-200 dark:bg-purple-950/40 dark:border-purple-900",
  pending: "text-amber-600 bg-amber-50 border-amber-200 dark:bg-amber-950/40 dark:border-amber-900",
  confirmed: "text-emerald-600 bg-emerald-50 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-900",
  details_differ: "text-rose-600 bg-rose-50 border-rose-200 dark:bg-rose-950/40 dark:border-rose-900",
  cannot_confirm: "text-slate-600 bg-slate-100 border-slate-200 dark:bg-slate-900 dark:border-slate-700",
  valid: "text-emerald-600 bg-emerald-50 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-900",
  revoked: "text-rose-600 bg-rose-50 border-rose-200 dark:bg-rose-950/40 dark:border-rose-900",
  superseded: "text-slate-600 bg-slate-100 border-slate-200 dark:bg-slate-900 dark:border-slate-700",
  eligible: "text-emerald-600 bg-emerald-50 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-900",
  eligible_with_conditions: "text-amber-600 bg-amber-50 border-amber-200 dark:bg-amber-950/40 dark:border-amber-900",
  blocked: "text-rose-600 bg-rose-50 border-rose-200 dark:bg-rose-950/40 dark:border-rose-900",
};

export function StatusChip({ value, label, className }: { value: string; label?: string; className?: string }) {
  const style = PALETTE[value] ?? "text-slate-600 bg-slate-100 border-slate-200 dark:bg-slate-900 dark:border-slate-700";
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize", style, className)}>
      {(label ?? value).replace(/_/g, " ")}
    </span>
  );
}
