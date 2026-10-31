import { Outlet, useNavigate } from "react-router-dom";
import { AlertTriangle, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SimulatedBadge } from "@/components/amanat/SimulatedBadge";
import { useAuth } from "@/lib/AuthContext";

export function BankShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-slate-100 via-slate-50 to-blue-50 dark:from-slate-950 dark:via-slate-900 dark:to-blue-950/30">
      <div className="flex items-center justify-center gap-2 bg-amber-400 px-3 py-1.5 text-center text-xs font-semibold text-amber-950">
        <AlertTriangle className="h-3.5 w-3.5" />
        SIMULATED BANK SCREEN — no real bank system is connected
      </div>
      <header className="flex items-center justify-between border-b bg-slate-800 px-4 py-3 text-white">
        <div>
          <p className="font-semibold tracking-tight">{user?.bank_name ?? "Bank Portal"}</p>
          <p className="text-xs text-slate-300">Verification requests from AICTE</p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="gap-2 text-white hover:bg-slate-700 hover:text-white"
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          <LogOut className="h-4 w-4" />
          Log out
        </Button>
      </header>
      <main className="flex-1 p-4 md:p-8">
        <Outlet />
      </main>
      <SimulatedBadge />
    </div>
  );
}
