import { useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { AlertTriangle, CheckCircle2, Download, QrCode, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/amanat/PageHeader";
import { MoneyText } from "@/components/amanat/MoneyText";
import { RoleGate } from "@/components/amanat/RoleGate";
import { StatusChip } from "@/components/amanat/StatusChip";
import { useApproveRelease, useRejectRelease, useRelease } from "@/api/hooks/useReleases";
import { ApiError, apiGetBlob } from "@/api/client";
import { cn } from "@/lib/utils";

const STEPS = ["Scrutiny", "Approver 1", "Approver 2"];

export function ReleaseDetailPage() {
  const { id } = useParams();
  const releaseId = id ? Number(id) : undefined;
  const { data, isLoading, refetch } = useRelease(releaseId);
  const approve = useApproveRelease();
  const reject = useRejectRelease();
  const [remarks, setRemarks] = useState("");
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  if (isLoading || !data) return <Skeleton className="h-64 w-full" />;

  const { release, instrument, approvals, precheck, order, sod } = data.data;
  const precheckChecks = "checks" in precheck ? precheck.checks : [];
  const penalties = "penalties" in precheck ? precheck.penalties : [];
  const holds = "holds" in precheck ? precheck.holds : [];

  const activeStep = release.status === "ready" ? 0 : release.status === "approver1_done" ? 1 : 2;

  async function doApprove() {
    if (!releaseId) return;
    try {
      await approve.mutateAsync({ id: releaseId, remarks });
      toast.success("Release approved.");
      refetch();
    } catch (err) {
      if (err instanceof ApiError && err.code === "SOD_VIOLATION") {
        toast.error(err.message);
      } else {
        toast.error(err instanceof ApiError ? err.message : "Could not approve.");
      }
    }
  }

  async function downloadOrderPdf() {
    if (!order) return;
    try {
      const blob = await apiGetBlob(`/api/v1/orders/${order.id}/pdf`);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
    } catch {
      toast.error("Could not download the order PDF.");
    }
  }

  async function doReject() {
    if (!releaseId) return;
    try {
      await reject.mutateAsync({ id: releaseId, reason: rejectReason });
      toast.success("Release rejected.");
      setRejectOpen(false);
      refetch();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not reject.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Release #${release.id}`}
        description={instrument ? `${instrument.fdr_number}` : undefined}
        actions={instrument ? <MoneyText paise={instrument.amount_paise} className="text-lg" /> : undefined}
      />

      {sod.blocked_for_current_user && sod.reason && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {sod.reason}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Approval stepper</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            {STEPS.map((step, i) => (
              <div key={step} className="flex flex-1 items-center gap-2">
                <div
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
                    i <= activeStep ? "bg-indigo-600 text-white" : "bg-muted text-muted-foreground",
                  )}
                >
                  {i + 1}
                </div>
                <span className="text-sm">{step}</span>
                {i < STEPS.length - 1 && <div className={cn("h-0.5 flex-1", i < activeStep ? "bg-indigo-600" : "bg-muted")} />}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pre-check: {precheck.verdict && <StatusChip value={precheck.verdict} className="ml-1" />}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {precheckChecks.map((check) => (
            <div key={check.key} className="flex items-start justify-between rounded-lg border p-2">
              <div className="flex items-start gap-2">
                {check.passed ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                ) : (
                  <XCircle className={cn("mt-0.5 h-4 w-4 shrink-0", check.severity === "block" ? "text-rose-600" : "text-amber-500")} />
                )}
                <div>
                  <p className="text-sm font-medium">{check.label}</p>
                  <p className="text-xs text-muted-foreground">{check.detail}</p>
                </div>
              </div>
              <StatusChip value={check.severity === "block" ? "high" : check.severity === "condition" ? "medium" : "low"} label={check.severity} />
            </div>
          ))}
          {penalties.map((p, i) => (
            <div key={i} className="rounded-lg border border-amber-200 bg-amber-50 p-2 text-sm dark:border-amber-900 dark:bg-amber-950/40">
              Penalty: {p.percent}% = <MoneyText paise={p.amount_paise} />
            </div>
          ))}
          {holds.map((h) => (
            <div key={h.id} className="rounded-lg border border-rose-200 bg-rose-50 p-2 text-sm dark:border-rose-900 dark:bg-rose-950/40">
              Hold: {h.reason} ({h.source})
            </div>
          ))}
        </CardContent>
      </Card>

      {release.status !== "approved" && release.status !== "rejected" && (
        <RoleGate allow={["senior_approver", "competent_authority"]} reason={sod.reason ?? undefined}>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Approve or reject</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea placeholder="Remarks" value={remarks} onChange={(e) => setRemarks(e.target.value)} />
              <div className="flex gap-2">
                <Button onClick={doApprove} disabled={approve.isPending || sod.blocked_for_current_user}>
                  Approve
                </Button>
                <Button variant="outline" onClick={() => setRejectOpen(true)}>
                  Reject
                </Button>
              </div>
            </CardContent>
          </Card>
        </RoleGate>
      )}

      {approvals.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Approvals so far</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {approvals.map((a, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg border p-2 text-sm">
                <span>Level {a.level} · Officer #{a.approver_id}</span>
                <StatusChip value={a.decision === "approved" ? "confirmed" : "open"} label={a.decision} />
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {order && (
        <Card className="border-gradient">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <QrCode className="h-4 w-4" />
              Signed order {order.order_no}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between">
            <StatusChip value={order.status} />
            <Button variant="outline" size="sm" className="gap-1.5" onClick={downloadOrderPdf}>
              <Download className="h-3.5 w-3.5" />
              Download PDF
            </Button>
          </CardContent>
        </Card>
      )}

      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject release</DialogTitle>
          </DialogHeader>
          <Textarea value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} placeholder="Reason" />
          <DialogFooter>
            <Button variant="destructive" onClick={doReject} disabled={!rejectReason.trim()}>
              Confirm rejection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
