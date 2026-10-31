import { Outlet } from "react-router-dom";
import { CalendarClock } from "lucide-react";
import { SimulatedBadge } from "@/components/amanat/SimulatedBadge";

export function PublicShell() {
  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-white via-indigo-50/30 to-teal-50/30 dark:from-slate-950 dark:via-indigo-950/20 dark:to-teal-950/20">
      <header className="brand-gradient flex items-center gap-2 px-6 py-4 text-white">
        <CalendarClock className="h-6 w-6" />
        <span className="font-semibold tracking-tight">Amanat</span>
        <span className="text-xs opacity-80">— AICTE Security Deposit Verification</span>
      </header>
      <main className="flex flex-1 items-center justify-center p-6">
        <Outlet />
      </main>
      <SimulatedBadge />
    </div>
  );
}
