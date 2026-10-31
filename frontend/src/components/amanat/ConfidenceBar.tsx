import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

export function ConfidenceBar({ pct, className }: { pct: number | null; className?: string }) {
  const reduce = useReducedMotion();
  if (pct === null) {
    return <span className="text-xs text-muted-foreground">Exempt</span>;
  }
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="h-2 w-24 overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full rounded-full"
          style={{
            background: "linear-gradient(90deg, #f43f5e 0%, #fbbf24 50%, #10b981 100%)",
          }}
          initial={{ width: reduce ? `${pct}%` : 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: reduce ? 0 : 0.6, ease: "easeOut" }}
        />
      </div>
      <span className="w-9 text-right text-xs font-medium tabular-nums">{pct}%</span>
    </div>
  );
}
