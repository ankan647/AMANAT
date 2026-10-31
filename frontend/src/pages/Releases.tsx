import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/amanat/PageHeader";
import { DataTable } from "@/components/amanat/DataTable";
import { StatusChip } from "@/components/amanat/StatusChip";
import { useReleases } from "@/api/hooks/useReleases";
import { formatDate } from "@/lib/dates";

export function ReleasesPage() {
  const { data, isLoading } = useReleases({});
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <PageHeader title="Releases" description="Pre-check, approvals, and the signed release order." />
      <Card>
        <CardContent className="pt-4">
          <DataTable
            columns={[
              { header: "Instrument", cell: (r) => `#${r.instrument_id}` },
              { header: "Requested", cell: (r) => formatDate(r.requested_on) },
              { header: "Verdict", cell: (r) => (r.precheck_verdict ? <StatusChip value={r.precheck_verdict} /> : "—") },
              { header: "Status", cell: (r) => <StatusChip value={r.status} /> },
              { header: "Two approvers?", cell: (r) => (r.needs_second_approval ? "Yes" : "No") },
            ]}
            rows={data?.data}
            rowKey={(r) => r.id}
            isLoading={isLoading}
            onRowClick={(r) => navigate(`/releases/${r.id}`)}
            emptyTitle="No release requests yet"
          />
        </CardContent>
      </Card>
    </div>
  );
}
