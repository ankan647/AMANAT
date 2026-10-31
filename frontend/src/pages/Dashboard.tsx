import { useMemo, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { AlertTriangle, Banknote, CheckCircle2, Gavel, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/amanat/PageHeader";
import { StatCard } from "@/components/amanat/StatCard";
import { PriorityMatrix } from "@/components/amanat/PriorityMatrix";
import { ActivityFeed } from "@/components/amanat/ActivityFeed";
import { DataTable } from "@/components/amanat/DataTable";
import { CoverageBadge } from "@/components/amanat/CoverageBadge";
import { ConfidenceBar } from "@/components/amanat/ConfidenceBar";
import { MoneyText } from "@/components/amanat/MoneyText";
import { useDashboardSummary, usePriorityMatrix } from "@/api/hooks/useDashboard";
import { useInstitutions } from "@/api/hooks/useInstitutions";
import { useDemoScenarios } from "@/api/hooks/useMetricsDemo";
import { formatINR } from "@/lib/formatINR";

export function DashboardPage() {
  const { data: summary, isLoading: loadingSummary } = useDashboardSummary();
  const { data: matrix } = usePriorityMatrix();
  const { data: scenarios } = useDemoScenarios();
  const [searchParams] = useSearchParams();
  const [q, setQ] = useState("");
  const navigate = useNavigate();

  const matrixCell = searchParams.get("matrix_cell") ?? undefined;
  const { data: institutions, isLoading: loadingInstitutions } = useInstitutions({ matrix_cell: matrixCell, q: q || undefined });

  const stats = useMemo(() => {
    const s = summary?.data;
    if (!s) return [];
    return [
      { label: "Institutions", value: s.institutions_total, icon: ShieldCheck, accent: "indigo" as const },
      { label: "Required deposit", value: s.required_paise, icon: Banknote, accent: "teal" as const, format: formatINR },
      { label: "Valid deposit", value: s.valid_paise, icon: CheckCircle2, accent: "emerald" as const, format: formatINR },
      { label: "Confirmed %", value: s.confirmed_pct, icon: ShieldCheck, accent: "teal" as const, suffix: "%" },
      { label: "Open flags", value: s.open_flags, icon: AlertTriangle, accent: "rose" as const },
      { label: "Releases pending", value: s.releases_pending, icon: Gavel, accent: "amber" as const },
    ];
  }, [summary]);

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="brand-gradient rounded-2xl p-6 text-white shadow-lg"
      >
        <h1 className="text-xl font-semibold tracking-tight">Welcome back</h1>
        <p className="mt-1 max-w-2xl text-sm text-indigo-100">
          Two indicators drive every decision here: <strong>Coverage Health</strong> — is enough
          valid deposit held, today and on every future date — and <strong>Verification
          Confidence</strong> — how much of that deposit the bank has actually confirmed.
        </p>
      </motion.div>

      {loadingSummary ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          {stats.map((s, i) => (
            <StatCard key={s.label} {...s} index={i} />
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="border-gradient lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Priority matrix</CardTitle>
          </CardHeader>
          <CardContent>
            <PriorityMatrix matrix={matrix?.data} />
          </CardContent>
        </Card>
        <ActivityFeed />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">Institutions</CardTitle>
          <Input placeholder="Search name or code..." value={q} onChange={(e) => setQ(e.target.value)} className="w-64" />
        </CardHeader>
        <CardContent>
          <DataTable
            columns={[
              { header: "Code", cell: (r) => r.code },
              { header: "Name", cell: (r) => r.name },
              { header: "Coverage", cell: (r) => <CoverageBadge status={r.coverage.status} /> },
              { header: "Confidence", cell: (r) => <ConfidenceBar pct={r.confidence_pct} /> },
              { header: "Required", cell: (r) => <MoneyText paise={r.coverage.required_paise} /> },
              { header: "Next action", cell: (r) => <span className="text-sm">{r.next_action.label}</span> },
            ]}
            rows={institutions?.data}
            rowKey={(r) => r.id}
            isLoading={loadingInstitutions}
            onRowClick={(r) => navigate(`/institutions/${r.id}`)}
            emptyTitle="No institutions match"
          />
        </CardContent>
      </Card>

      {scenarios && scenarios.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Demo scenarios</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3 overflow-x-auto pb-2">
              {scenarios.map((s) => (
                <button
                  key={s.key}
                  onClick={() => navigate("/demo")}
                  className="min-w-[220px] rounded-lg border p-3 text-left text-sm hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/30"
                >
                  <p className="font-medium">
                    {s.key}. {s.title}
                  </p>
                  <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{s.story}</p>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
