import { AlertTriangle, CheckCircle2, Clock, ShieldCheck, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CoverageStatus } from "@/api/types";

const CONFIG: Record<CoverageStatus, { label: string; icon: typeof CheckCircle2; className: string }> = {
  covered: { label: "Covered", icon: CheckCircle2, className: "text-emerald-600 bg-emerald-50 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-900" },
  expiring_soon: { label: "Expiring soon", icon: Clock, className: "text-amber-500 bg-amber-50 border-amber-200 dark:bg-amber-950/40 dark:border-amber-900" },
  shortfall: { label: "Shortfall", icon: AlertTriangle, className: "text-rose-600 bg-rose-50 border-rose-200 dark:bg-rose-950/40 dark:border-rose-900" },
  not_covered: { label: "Not covered", icon: XCircle, className: "text-slate-700 bg-slate-100 border-slate-200 dark:bg-slate-900 dark:border-slate-700 dark:text-slate-300" },
  exempt: { label: "Exempt", icon: ShieldCheck, className: "text-sky-600 bg-sky-50 border-sky-200 dark:bg-sky-950/40 dark:border-sky-900" },
};

export function CoverageBadge({ status, className }: { status: CoverageStatus; className?: string }) {
  const cfg = CONFIG[status];
  const Icon = cfg.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        cfg.className,
        className,
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {cfg.label}
    </span>
  );
}
