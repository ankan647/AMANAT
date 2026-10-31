import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { type LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

function useCountUp(target: number, durationMs = 800) {
  const reduce = useReducedMotion();
  const [value, setValue] = useState(reduce ? target : 0);

  useEffect(() => {
    if (reduce) {
      setValue(target);
      return;
    }
    let start: number | null = null;
    let frame: number;
    const step = (ts: number) => {
      if (start === null) start = ts;
      const progress = Math.min((ts - start) / durationMs, 1);
      setValue(Math.round(target * (1 - Math.pow(1 - progress, 3))));
      if (progress < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, durationMs, reduce]);

  return value;
}

export function StatCard({
  label,
  value,
  icon: Icon,
  suffix,
  format,
  accent,
  index = 0,
}: {
  label: string;
  value: number;
  icon: LucideIcon;
  suffix?: string;
  format?: (n: number) => string;
  accent?: "indigo" | "teal" | "amber" | "rose" | "emerald";
  index?: number;
}) {
  const animated = useCountUp(value);
  const display = format ? format(animated) : `${animated}${suffix ?? ""}`;

  const accentClass: Record<string, string> = {
    indigo: "from-indigo-500/20 via-indigo-500/5 to-transparent text-indigo-600 dark:text-indigo-400",
    teal: "from-teal-500/20 via-teal-500/5 to-transparent text-teal-600 dark:text-teal-400",
    amber: "from-amber-500/20 via-amber-500/5 to-transparent text-amber-600 dark:text-amber-400",
    rose: "from-rose-500/20 via-rose-500/5 to-transparent text-rose-600 dark:text-rose-400",
    emerald: "from-emerald-500/20 via-emerald-500/5 to-transparent text-emerald-600 dark:text-emerald-400",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.05 }}
    >
      <Card className="relative overflow-hidden rounded-xl border shadow-sm">
        <div
          className={cn(
            "pointer-events-none absolute inset-0 bg-gradient-to-br opacity-60",
            accentClass[accent ?? "indigo"],
          )}
        />
        <CardContent className="relative flex items-center justify-between p-4">
          <div>
            <p className="text-xs font-medium text-muted-foreground">{label}</p>
            <p className="mt-1 text-2xl font-semibold tracking-tight tabular-nums">{display}</p>
          </div>
          <Icon className={cn("h-8 w-8 opacity-80", accentClass[accent ?? "indigo"].split(" ").slice(-2).join(" "))} />
        </CardContent>
      </Card>
    </motion.div>
  );
}
