import ReactECharts from "echarts-for-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/amanat/PageHeader";
import { StatCard } from "@/components/amanat/StatCard";
import { Percent, Clock, ShieldCheck, Gavel, Timer } from "lucide-react";
import { useAnomalyMetrics } from "@/api/hooks/useFlags";
import { useKpis } from "@/api/hooks/useMetricsDemo";

export function MetricsPage() {
  const { data: anomalyMetrics, isLoading } = useAnomalyMetrics();
  const { data: kpis } = useKpis();

  const byType = anomalyMetrics?.data.by_type ?? [];
  const option = {
    tooltip: {},
    legend: { data: ["Precision", "Recall"] },
    grid: { left: 110, right: 30, top: 40, bottom: 20 },
    xAxis: { type: "value", min: 0, max: 1 },
    yAxis: { type: "category", data: byType.map((t) => t.type.replace(/_/g, " ")) },
    series: [
      { name: "Precision", type: "bar", data: byType.map((t) => t.precision), itemStyle: { color: "#4338ca" } },
      { name: "Recall", type: "bar", data: byType.map((t) => t.recall ?? 0), itemStyle: { color: "#0d9488" } },
    ],
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Metrics" description="Anomaly detection quality on planted data, and the five pilot KPIs." />

      {kpis && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <StatCard label="Confirmed deposit share" value={kpis.data.confirmed_deposit_share_pct} suffix="%" icon={Percent} accent="teal" index={0} />
          <StatCard label="Avg days to bank confirmation" value={kpis.data.avg_days_to_bank_confirmation} icon={Clock} accent="indigo" index={1} />
          <StatCard label="Flags confirmed share" value={kpis.data.flags_confirmed_share_pct} suffix="%" icon={ShieldCheck} accent="rose" index={2} />
          <StatCard label="Maturities handled before deadline" value={kpis.data.maturities_handled_before_deadline_pct} suffix="%" icon={Timer} accent="emerald" index={3} />
          <StatCard label="Avg days to release decision" value={kpis.data.avg_days_to_release_decision} icon={Gavel} accent="amber" index={4} />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Overall — precision {anomalyMetrics ? (anomalyMetrics.data.overall.precision * 100).toFixed(0) : "—"}%, recall{" "}
            {anomalyMetrics ? (anomalyMetrics.data.overall.recall * 100).toFixed(0) : "—"}%, officer-confirmed share{" "}
            {anomalyMetrics ? (anomalyMetrics.data.overall.officer_confirmed_share * 100).toFixed(0) : "—"}%
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? <Skeleton className="h-80 w-full" /> : <ReactECharts option={option} style={{ height: 420 }} />}
        </CardContent>
      </Card>
    </div>
  );
}
