import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/amanat/PageHeader";
import { DataTable } from "@/components/amanat/DataTable";
import { StatusChip } from "@/components/amanat/StatusChip";
import { useFlagReferrals, useFlags } from "@/api/hooks/useFlags";
import { formatDateTime } from "@/lib/dates";

export function FlagsPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<string | undefined>("open");
  const { data, isLoading } = useFlags({ status });
  const { data: referrals } = useFlagReferrals();

  return (
    <div className="space-y-6">
      <PageHeader title="Anomalies" description='Wording is always "Anomaly: needs review" — never a stronger word.' />

      <Tabs defaultValue="flags" onValueChange={(v) => setStatus(v === "flags" ? "open" : undefined)}>
        <TabsList>
          <TabsTrigger value="flags">Open flags</TabsTrigger>
          <TabsTrigger value="referrals">Vigilance referrals ({referrals?.data.length ?? 0})</TabsTrigger>
        </TabsList>
        <TabsContent value="flags" className="pt-4">
          <Card>
            <CardContent className="pt-4">
              <DataTable
                columns={[
                  { header: "Title", cell: (r) => r.title },
                  { header: "Type", cell: (r) => <span className="text-xs text-muted-foreground">{r.type.replace(/_/g, " ")}</span> },
                  { header: "Severity", cell: (r) => <StatusChip value={r.severity} /> },
                  { header: "Status", cell: (r) => <StatusChip value={r.status} /> },
                  { header: "Raised", cell: (r) => formatDateTime(r.created_at) },
                ]}
                rows={data?.data}
                rowKey={(r) => r.id}
                isLoading={isLoading}
                onRowClick={(r) => navigate(`/flags/${r.id}`)}
                emptyTitle="No open anomalies"
                emptyDescription="Everything currently raised has been reviewed."
              />
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="referrals" className="pt-4">
          <Card>
            <CardContent className="pt-4">
              <DataTable
                columns={[
                  { header: "Title", cell: (r) => r.title },
                  { header: "Reason", cell: (r) => <span className="text-xs text-muted-foreground">{r.outcome_reason}</span> },
                ]}
                rows={referrals?.data}
                rowKey={(r) => r.id}
                onRowClick={(r) => navigate(`/flags/${r.id}`)}
                emptyTitle="No referrals"
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
