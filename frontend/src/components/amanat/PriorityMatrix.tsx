import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import type { PriorityMatrixOut } from "@/api/types";
import { cn } from "@/lib/utils";

const CELL_STYLE: Record<string, string> = {
  routine_monitoring: "bg-gradient-to-br from-emerald-500 to-emerald-700 text-white",
  verify_next: "bg-gradient-to-br from-amber-400 to-yellow-600 text-white",
  send_renewal_notice: "bg-gradient-to-br from-orange-400 to-orange-600 text-white",
  urgent_both: "bg-gradient-to-br from-rose-500 to-red-700 text-white",
};

export function PriorityMatrix({ matrix }: { matrix: PriorityMatrixOut | undefined }) {
  const navigate = useNavigate();
  if (!matrix) return null;

  const order = ["routine_monitoring", "verify_next", "send_renewal_notice", "urgent_both"];
  const cells = order.map((key) => matrix.cells.find((c) => c.key === key)).filter(Boolean);

  return (
    <div className="grid grid-cols-2 gap-3">
      {cells.map((cell, i) => (
        <motion.button
          key={cell!.key}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.05 }}
          onClick={() => navigate(`/?matrix_cell=${cell!.key}`)}
          className={cn(
            "rounded-xl p-4 text-left shadow-sm transition-transform hover:scale-[1.02] focus-visible:outline-2 focus-visible:outline-offset-2",
            CELL_STYLE[cell!.key],
          )}
        >
          <p className="text-3xl font-bold tabular-nums">{cell!.count}</p>
          <p className="mt-1 text-sm font-medium opacity-95">{cell!.label}</p>
        </motion.button>
      ))}
    </div>
  );
}
