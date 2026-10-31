import { formatINR } from "@/lib/formatINR";
import { cn } from "@/lib/utils";

export function MoneyText({ paise, className }: { paise: number; className?: string }) {
  return <span className={cn("tabular-nums font-semibold", className)}>{formatINR(paise)}</span>;
}
