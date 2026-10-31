import { useState } from "react";
import { toast } from "sonner";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Sheet, SheetContent, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/amanat/PageHeader";
import { DataTable } from "@/components/amanat/DataTable";
import { StatusChip } from "@/components/amanat/StatusChip";
import { GradeBadge } from "@/components/amanat/GradeBadge";
import { useAcceptBankResponse, useAcceptPreview, useBankRequests, useRejectBankResponse } from "@/api/hooks/useBankRequests";
import { formatDate } from "@/lib/dates";
import { ApiError } from "@/api/client";

export function BankRequestsPage() {
  const { data, isLoading } = useBankRequests({});
  const [activeId, setActiveId] = useState<number | null>(null);
  const [reason, setReason] = useState("");
  const { data: preview } = useAcceptPreview(activeId ?? undefined);
  const accept = useAcceptBankResponse();
  const reject = useRejectBankResponse();

  async function doAccept() {
    if (!activeId) return;
    try {
      const res = await accept.mutateAsync(activeId);
      toast.success(`Confidence ${res.data.previous_confidence_pct ?? 0}% to ${res.data.institution_confidence_pct ?? 0}%`);
      setActiveId(null);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not accept.");
    }
  }

  async function doReject() {
    if (!activeId) return;
    try {
      await reject.mutateAsync({ id: activeId, reason });
      toast.success("Response rejected.");
      setActiveId(null);
      setReason("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not reject.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Bank Requests" description="Track verification requests end to end: sent -> due -> responded -> accepted." />
      <Card>
        <CardContent className="pt-4">
          <DataTable
            columns={[
              { header: "Request", cell: (r) => r.request_code },
              { header: "Bank", cell: (r) => r.bank_name },
              { header: "Sent", cell: (r) => formatDate(r.sent_date) },
              { header: "Due", cell: (r) => formatDate(r.due_date) },
              {
                header: "Timeline",
                cell: (r) => (
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <span>Sent</span>
                    <ArrowRight className="h-3 w-3" />
                    <span>Due</span>
                    <ArrowRight className="h-3 w-3" />
                    <span className={r.response_date ? "font-medium text-foreground" : ""}>Responded</span>
                  </div>
                ),
              },
              { header: "Outcome", cell: (r) => <StatusChip value={r.outcome} /> },
              {
                header: "",
                cell: (r) =>
                  r.outcome !== "pending" ? (
                    <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); setActiveId(r.id); }}>
                      Accept / reject
                    </Button>
                  ) : null,
              },
            ]}
            rows={data?.data}
            rowKey={(r) => r.id}
            isLoading={isLoading}
            emptyTitle="No bank requests yet"
          />
        </CardContent>
      </Card>

      <Sheet open={activeId !== null} onOpenChange={(open) => !open && setActiveId(null)}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Accept preview</SheetTitle>
          </SheetHeader>
          {preview && (
            <div className="mt-4 space-y-3">
              <p className="text-sm text-muted-foreground">
                {preview.data.upgraded_fields.length} field(s) will become Bank-confirmed.
              </p>
              <div className="space-y-1.5">
                {preview.data.upgraded_fields.map((f) => (
                  <div key={f.field_name} className="flex items-center justify-between rounded-lg border p-2 text-sm">
                    <span className="capitalize">{f.field_name.replace(/_/g, " ")}</span>
                    <div className="flex items-center gap-2">
                      <GradeBadge grade={f.from_grade} />
                      <ArrowRight className="h-3 w-3" />
                      <GradeBadge grade={f.to_grade} />
                    </div>
                  </div>
                ))}
              </div>
              <div>
                <p className="mb-1 text-xs font-medium text-muted-foreground">Rejection reason (if rejecting)</p>
                <Textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason for rejecting..." />
              </div>
            </div>
          )}
          <SheetFooter className="mt-4 flex-row gap-2">
            <Button variant="outline" className="flex-1" onClick={doReject} disabled={reject.isPending}>
              Reject
            </Button>
            <Button className="flex-1" onClick={doAccept} disabled={accept.isPending}>
              Accept
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}
