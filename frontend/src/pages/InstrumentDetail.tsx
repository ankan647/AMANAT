import { useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { Banknote, Gavel } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { DataTable } from "@/components/amanat/DataTable";
import { GradeBadge } from "@/components/amanat/GradeBadge";
import { MoneyText } from "@/components/amanat/MoneyText";
import { PageHeader } from "@/components/amanat/PageHeader";
import { RoleGate } from "@/components/amanat/RoleGate";
import { StatusChip } from "@/components/amanat/StatusChip";
import { useInstrument } from "@/api/hooks/useInstruments";
import { useCreateBankRequest } from "@/api/hooks/useBankRequests";
import { useCreateRelease } from "@/api/hooks/useReleases";
import { formatDate } from "@/lib/dates";
import { ApiError } from "@/api/client";

export function InstrumentDetailPage() {
  const { id } = useParams();
  const instrumentId = id ? Number(id) : undefined;
  const { data, isLoading, refetch } = useInstrument(instrumentId);
  const createBankRequest = useCreateBankRequest();
  const createRelease = useCreateRelease();
  const [bankDialogOpen, setBankDialogOpen] = useState(false);
  const [branch, setBranch] = useState("");
  const [releaseReason, setReleaseReason] = useState("Term completed");

  if (isLoading || !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const instrument = data.data.instrument;

  async function sendBankRequest() {
    try {
      await createBankRequest.mutateAsync({ instrument_id: instrument.id, bank_name: instrument.bank_name, branch: branch || instrument.branch });
      toast.success("Bank verification requested.");
      setBankDialogOpen(false);
      refetch();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not send request.");
    }
  }

  async function raiseRelease() {
    try {
      await createRelease.mutateAsync({ instrument_id: instrument.id, reason: releaseReason });
      toast.success("Release request created.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not raise release.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={instrument.fdr_number}
        description={`${instrument.bank_name} · ${instrument.branch} · ${instrument.ifsc}`}
        actions={
          <div className="flex gap-2">
            <RoleGate allow={["scrutiny", "senior_approver", "competent_authority"]}>
              <Dialog open={bankDialogOpen} onOpenChange={setBankDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-1.5">
                    <Banknote className="h-3.5 w-3.5" />
                    Request bank confirmation
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Request bank confirmation</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-2">
                    <Label>Branch</Label>
                    <Input value={branch} onChange={(e) => setBranch(e.target.value)} placeholder={instrument.branch} />
                  </div>
                  <DialogFooter>
                    <Button onClick={sendBankRequest} disabled={createBankRequest.isPending}>
                      Send request
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </RoleGate>
            <RoleGate allow={["institution", "scrutiny"]}>
              <Dialog>
                <DialogTrigger asChild>
                  <Button size="sm" className="gap-1.5">
                    <Gavel className="h-3.5 w-3.5" />
                    Raise release
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Raise release request</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-2">
                    <Label>Reason</Label>
                    <Textarea value={releaseReason} onChange={(e) => setReleaseReason(e.target.value)} />
                  </div>
                  <DialogFooter>
                    <Button onClick={raiseRelease} disabled={createRelease.isPending}>
                      Submit
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </RoleGate>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Amount</p>
            <MoneyText paise={instrument.amount_paise} className="text-lg" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Term</p>
            <p className="text-sm">{formatDate(instrument.issue_date)} — {formatDate(instrument.maturity_date)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Instrument grade</p>
            <GradeBadge grade={data.data.confidence.grade} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Field verification</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={[
              { header: "Field", cell: (r) => r.field_name.replace(/_/g, " ") },
              { header: "Value", cell: (r) => <span className="line-clamp-1 max-w-xs">{r.value}</span> },
              { header: "Grade", cell: (r) => <GradeBadge grade={r.grade} /> },
              { header: "Source", cell: (r) => r.source },
            ]}
            rows={data.data.fields}
            rowKey={(r) => r.field_name}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Documents</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={[
              { header: "File", cell: (r) => r.filename },
              { header: "Kind", cell: (r) => r.kind.replace(/_/g, " ") },
              { header: "SHA-256", cell: (r) => <code className="text-xs">{r.sha256.slice(0, 16)}…</code> },
              { header: "Text snippet", cell: (r) => <span className="line-clamp-1 max-w-xs text-xs text-muted-foreground">{r.ocr_text}</span> },
            ]}
            rows={data.data.documents}
            rowKey={(r) => r.id}
            emptyTitle="No documents uploaded"
          />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Assignment history</CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={[
                { header: "Officer", cell: (r) => `#${r.officer_id}` },
                { header: "Role", cell: (r) => r.role },
                { header: "Assigned", cell: (r) => formatDate(r.assigned_at) },
              ]}
              rows={data.data.assignments}
              rowKey={(r) => `${r.officer_id}-${r.role}-${r.assigned_at}`}
              emptyTitle="No assignments yet"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Flags & bank requests</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.data.flags.map((f) => (
              <div key={f.id} className="flex items-center justify-between rounded-lg border p-2 text-sm">
                <span className="line-clamp-1">{f.title}</span>
                <StatusChip value={f.status} />
              </div>
            ))}
            {data.data.bank_requests.map((b) => (
              <div key={b.id} className="flex items-center justify-between rounded-lg border p-2 text-sm">
                <span>{b.request_code}</span>
                <StatusChip value={b.outcome} />
              </div>
            ))}
            {data.data.flags.length === 0 && data.data.bank_requests.length === 0 && (
              <p className="text-sm text-muted-foreground">Nothing yet.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
