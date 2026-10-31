import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { CheckCircle2, Gavel, Undo2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/amanat/PageHeader";
import { StatusChip } from "@/components/amanat/StatusChip";
import { RoleGate } from "@/components/amanat/RoleGate";
import { useFlag, useFlagOutcome } from "@/api/hooks/useFlags";
import { ApiError } from "@/api/client";

export function FlagDetailPage() {
  const { id } = useParams();
  const flagId = id ? Number(id) : undefined;
  const { data, isLoading } = useFlag(flagId);
  const outcome = useFlagOutcome();
  const navigate = useNavigate();
  const [pendingOutcome, setPendingOutcome] = useState<string | null>(null);
  const [reason, setReason] = useState("");

  if (isLoading || !data) {
    return <Skeleton className="h-64 w-full" />;
  }

  const flag = data.data.flag;

  async function submit(selected: string, selectedReason: string) {
    if (!flagId) return;
    try {
      await outcome.mutateAsync({ id: flagId, outcome: selected, reason: selectedReason || undefined });
      toast.success("Outcome recorded.", {
        action: { label: "Undo", onClick: () => toast.info("Undo isn't available for recorded outcomes in this demo.") },
      });
      setPendingOutcome(null);
      setReason("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not record outcome.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={flag.title}
        description="Anomaly: needs review — not a finding of fraud, just something that needs a second look."
        actions={<StatusChip value={flag.status} />}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Reasons</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {data.data.reasons.map((r, i) => (
              <p key={i}>{r.text}</p>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Evidence</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="overflow-x-auto rounded-lg bg-muted p-3 text-xs">{JSON.stringify(data.data.evidence, null, 2)}</pre>
          </CardContent>
        </Card>
      </div>

      {data.data.related_instruments.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Related instruments</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {data.data.related_instruments.map((r) => (
              <Button key={r.id} variant="outline" size="sm" onClick={() => navigate(`/instruments/${r.id}`)}>
                {r.fdr_number}
              </Button>
            ))}
          </CardContent>
        </Card>
      )}

      {flag.status === "open" && (
        <RoleGate allow={["scrutiny", "senior_approver", "competent_authority"]}>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" className="gap-2" onClick={() => setPendingOutcome("cleared")}>
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              Cleared
            </Button>
            <Button variant="outline" className="gap-2" onClick={() => submit("return_for_correction", "")}>
              <Undo2 className="h-4 w-4 text-amber-600" />
              Return for correction
            </Button>
            <Button variant="outline" className="gap-2" onClick={() => submit("refer_for_investigation", "")}>
              <Gavel className="h-4 w-4 text-purple-600" />
              Refer for investigation
            </Button>
          </div>
        </RoleGate>
      )}

      <Dialog open={pendingOutcome === "cleared"} onOpenChange={(open) => !open && setPendingOutcome(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clear this anomaly</DialogTitle>
          </DialogHeader>
          <Textarea placeholder="Reason (required)" value={reason} onChange={(e) => setReason(e.target.value)} />
          <DialogFooter>
            <Button disabled={!reason.trim()} onClick={() => submit("cleared", reason)}>
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
