import { useParams, Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/amanat/PageHeader";
import { CoverageBadge } from "@/components/amanat/CoverageBadge";
import { ConfidenceBar } from "@/components/amanat/ConfidenceBar";
import { MoneyText } from "@/components/amanat/MoneyText";
import { CoverageTimelineChart } from "@/components/amanat/CoverageTimelineChart";
import { ExplainDrawer } from "@/components/amanat/ExplainDrawer";
import { DataTable } from "@/components/amanat/DataTable";
import { StatusChip } from "@/components/amanat/StatusChip";
import { EmptyState } from "@/components/amanat/EmptyState";
import { useCoverageTimeline, useInstitution, useWhyRule } from "@/api/hooks/useInstitutions";
import { formatDate } from "@/lib/dates";

export function InstitutionDetailPage() {
  const { id } = useParams();
  const institutionId = id ? Number(id) : undefined;
  const { data, isLoading } = useInstitution(institutionId);
  const { data: timeline } = useCoverageTimeline(institutionId);
  const { data: whyRule } = useWhyRule(institutionId);

  if (isLoading || !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const inst = data.data.institution;

  return (
    <div className="space-y-6">
      <PageHeader
        title={inst.name}
        description={`${inst.code} · ${inst.state} · ${inst.category}`}
        actions={
          <div className="flex items-center gap-2">
            <CoverageBadge status={inst.coverage.status} />
            {data.data.rule_applied && (
              <ExplainDrawer
                title="Why this rule?"
                trigger={<Badge variant="outline" className="cursor-pointer">{data.data.rule_applied.title ?? "Rule applied"}</Badge>}
                steps={whyRule?.data.steps ?? []}
              />
            )}
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Required</p>
            <MoneyText paise={inst.coverage.required_paise} className="text-lg" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Valid today</p>
            <MoneyText paise={inst.coverage.valid_paise} className="text-lg" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Confidence</p>
            <ConfidenceBar pct={inst.confidence_pct} />
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview">
        <TabsList className="flex-wrap">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="instruments">Instruments</TabsTrigger>
          <TabsTrigger value="bank">Bank requests</TabsTrigger>
          <TabsTrigger value="flags">Flags</TabsTrigger>
          <TabsTrigger value="reminders">Reminders</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="pt-4">
          {inst.coverage.exempt_reason && (
            <p className="mb-3 rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-700 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-300">
              {inst.coverage.exempt_reason}
            </p>
          )}
          {timeline?.data ? (
            <CoverageTimelineChart timeline={timeline.data} />
          ) : (
            <Skeleton className="h-64 w-full" />
          )}
        </TabsContent>

        <TabsContent value="instruments" className="pt-4">
          <DataTable
            columns={[
              { header: "FDR", cell: (r) => <Link to={`/instruments/${r.id}`} className="text-indigo-600 hover:underline dark:text-indigo-400">{r.fdr_number}</Link> },
              { header: "Bank", cell: (r) => r.bank_name },
              { header: "Amount", cell: (r) => <MoneyText paise={r.amount_paise} /> },
              { header: "Issue", cell: (r) => formatDate(r.issue_date) },
              { header: "Maturity", cell: (r) => formatDate(r.maturity_date) },
              { header: "Status", cell: (r) => <StatusChip value={r.status} /> },
            ]}
            rows={data.data.instruments}
            rowKey={(r) => r.id}
            emptyTitle="No instruments lodged yet"
          />
        </TabsContent>

        <TabsContent value="bank" className="pt-4">
          <DataTable
            columns={[
              { header: "Request", cell: (r) => r.request_code },
              { header: "Due", cell: (r) => formatDate(r.due_date) },
              { header: "Outcome", cell: (r) => <StatusChip value={r.outcome} /> },
            ]}
            rows={data.data.bank_requests}
            rowKey={(r) => r.id}
            emptyTitle="No bank requests yet"
          />
        </TabsContent>

        <TabsContent value="flags" className="pt-4">
          {data.data.open_flags.length === 0 ? (
            <EmptyState title="No open anomalies" description="Nothing needs review right now." />
          ) : (
            <DataTable
              columns={[
                { header: "Title", cell: (r) => <Link to={`/flags/${r.id}`} className="text-indigo-600 hover:underline dark:text-indigo-400">{r.title}</Link> },
                { header: "Severity", cell: (r) => <StatusChip value={r.severity} /> },
              ]}
              rows={data.data.open_flags}
              rowKey={(r) => r.id}
            />
          )}
        </TabsContent>

        <TabsContent value="reminders" className="pt-4">
          <DataTable
            columns={[
              { header: "Kind", cell: (r) => r.kind.replace(/_/g, " ").toUpperCase() },
              { header: "Due", cell: (r) => formatDate(r.due_on) },
              { header: "Status", cell: (r) => (r.paused ? <StatusChip value="returned" label="Paused" /> : r.fired_on ? <StatusChip value="cleared" label="Fired" /> : <StatusChip value="pending" />) },
            ]}
            rows={data.data.reminders}
            rowKey={(r) => r.id}
            emptyTitle="No reminders"
          />
        </TabsContent>

        <TabsContent value="history" className="pt-4">
          {data.data.holds.length === 0 ? (
            <EmptyState title="No holds on this institution" />
          ) : (
            <DataTable
              columns={[
                { header: "Reason", cell: (r) => r.reason },
                { header: "Source", cell: (r) => r.source },
                { header: "Placed on", cell: (r) => formatDate(r.placed_on) },
              ]}
              rows={data.data.holds}
              rowKey={(r) => r.id}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
