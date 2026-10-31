import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { CalendarClock, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useDemoAccounts, useLogin } from "@/api/hooks/useAuthApi";
import { ApiError } from "@/api/client";
import { useAuth } from "@/lib/AuthContext";
import { homeRouteFor, roleLabel, type Role } from "@/lib/roles";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("Demo@123");
  const login = useLogin();
  const { data: demoAccounts, isLoading: loadingAccounts } = useDemoAccounts();
  const { login: setSession } = useAuth();
  const navigate = useNavigate();

  async function doLogin(loginEmail: string, loginPassword: string) {
    try {
      const resp = await login.mutateAsync({ email: loginEmail, password: loginPassword });
      setSession(resp.data.access_token, resp.data.user);
      toast.success(`Welcome, ${resp.data.user.name}`);
      navigate(homeRouteFor(resp.data.user.role as Role, resp.data.user.institution_id));
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Login failed.";
      toast.error(message);
    }
  }

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      <div className="brand-gradient flex flex-col justify-center gap-6 p-10 text-white">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <div className="mb-6 flex items-center gap-2">
            <CalendarClock className="h-8 w-8" />
            <span className="text-2xl font-semibold tracking-tight">Amanat</span>
          </div>
          <h1 className="max-w-md text-3xl font-semibold leading-tight tracking-tight">
            Every deposit covered, every claim checked, every date watched.
          </h1>
          <p className="mt-4 max-w-md text-indigo-100">
            A prototype for AICTE's security-deposit FDR lifecycle: lodge, check, bank-confirm,
            track, renew, release — with a plain-language reason behind every status.
          </p>
          <div className="mt-8 flex items-center gap-2 text-sm text-indigo-100">
            <ShieldCheck className="h-4 w-4" />
            Synthetic data, simulated bank screen, demo signing key.
          </div>
        </motion.div>
      </div>

      <div className="flex flex-col justify-center gap-6 p-6 md:p-10">
        <Card className="w-full max-w-md self-center">
          <CardContent className="p-6">
            <h2 className="mb-4 text-lg font-semibold">Sign in</h2>
            <form
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                doLogin(email, password);
              }}
            >
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="scrutiny1@aicte.demo" />
              </div>
              <div>
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
              </div>
              <Button type="submit" className="w-full" disabled={login.isPending}>
                {login.isPending ? "Signing in..." : "Sign in"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="w-full max-w-md self-center">
          <p className="mb-2 text-sm font-medium text-muted-foreground">Demo accounts (one click, DEMO_MODE)</p>
          <div className="grid max-h-80 grid-cols-1 gap-2 overflow-y-auto sm:grid-cols-2">
            {loadingAccounts &&
              Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}
            {demoAccounts?.map((account) => (
              <button
                key={account.email}
                onClick={() => doLogin(account.email, "Demo@123")}
                className="rounded-lg border p-3 text-left text-sm transition-colors hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/30"
              >
                <p className="font-medium">{account.name}</p>
                <p className="text-xs text-muted-foreground">{roleLabel(account.role as Role)}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
