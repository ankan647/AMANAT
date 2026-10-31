import { BadgeCheck, CircleDashed, FileCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FieldGrade } from "@/api/types";

const CONFIG: Record<FieldGrade, { label: string; icon: typeof BadgeCheck; className: string }> = {
  claimed: { label: "Claimed", icon: CircleDashed, className: "text-slate-400 bg-slate-50 border-slate-200 dark:bg-slate-900 dark:border-slate-700" },
  document_checked: { label: "Document-checked", icon: FileCheck, className: "text-amber-500 bg-amber-50 border-amber-200 dark:bg-amber-950/40 dark:border-amber-900" },
  bank_confirmed: { label: "Bank-confirmed", icon: BadgeCheck, className: "text-emerald-600 bg-emerald-50 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-900" },
};

export function GradeBadge({ grade, className }: { grade: FieldGrade; className?: string }) {
  const cfg = CONFIG[grade];
  const Icon = cfg.icon;
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium", cfg.className, className)}>
      <Icon className="h-3.5 w-3.5" />
      {cfg.label}
    </span>
  );
}
