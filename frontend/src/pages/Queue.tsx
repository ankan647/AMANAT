import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/amanat/PageHeader";
import { DataTable } from "@/components/amanat/DataTable";
import { MoneyText } from "@/components/amanat/MoneyText";
import { useVerificationQueue } from "@/api/hooks/useInstruments";
import { useCreateBankRequest } from "@/api/hooks/useBankRequests";
import { ApiError } from "@/api/client";
import type { QueueRow } from "@/api/types";

export function QueuePage() {
  const { data, isLoading } = useVerificationQueue();
  const createBankRequest = useCreateBankRequest();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<QueueRow | null>(null);
  const [branch, setBranch] = useState("");

  async function send() {
    if (!selected) return;
    try {
      await createBankRequest.mutateAsync({ instrument_id: selected.instrument_id, bank_name: "State Bank of India", branch });
      toast.success(`Bank request sent for ${selected.institution_name}.`);
      setSelected(null);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not send request.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Verification Queue" description="Priority-ordered instruments that still need bank confirmation." />
      <Card>
        <CardContent className="pt-4">
          <DataTable
            columns={[
              { header: "Institution", cell: (r) => r.institution_name },
              { header: "Amount", cell: (r) => <MoneyText paise={r.amount_paise} /> },
              { header: "Reason", cell: (r) => <span className="text-sm text-muted-foreground">{r.reason}</span> },
              {
                header: "",
                cell: (r) => (
                  <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); setSelected(r); }}>
                    Send bank request
                  </Button>
                ),
              },
            ]}
            rows={data}
            rowKey={(r) => r.instrument_id}
            isLoading={isLoading}
            emptyTitle="Queue is empty"
            emptyDescription="Every valid instrument is already bank-confirmed."
            onRowClick={(r) => navigate(`/instruments/${r.instrument_id}`)}
          />
        </CardContent>
      </Card>

      <Dialog open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send bank confirmation request</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <Label>Branch</Label>
            <Input value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="Branch name" />
          </div>
          <DialogFooter>
            <Button onClick={send} disabled={createBankRequest.isPending}>
              Send
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
