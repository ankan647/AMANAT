import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/amanat/PageHeader";
import { DataTable } from "@/components/amanat/DataTable";
import { StatusChip } from "@/components/amanat/StatusChip";
import { usePauseReminder, useReminders, useResumeReminder } from "@/api/hooks/useReminders";
import { formatDate } from "@/lib/dates";
import { ApiError } from "@/api/client";

export function RemindersPage() {
  const [state, setState] = useState<string | undefined>(undefined);
  const { data, isLoading } = useReminders({ state });
  const pause = usePauseReminder();
  const resume = useResumeReminder();
  const [pausingId, setPausingId] = useState<number | null>(null);
  const [reason, setReason] = useState("Waiting for institution");

  async function doPause() {
    if (!pausingId) return;
    try {
      await pause.mutateAsync({ id: pausingId, reason });
      toast.success("Reminder paused.");
      setPausingId(null);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not pause.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Reminders" description="T-90 / T-60 / T-30 / T-7 and overdue reminders, driven by the simulated clock." />

      <Tabs value={state ?? "all"} onValueChange={(v) => setState(v === "all" ? undefined : v)}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="pending">Pending</TabsTrigger>
          <TabsTrigger value="sent">Sent</TabsTrigger>
          <TabsTrigger value="paused">Paused</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardContent className="pt-4">
          <DataTable
            columns={[
              { header: "Instrument", cell: (r) => `#${r.instrument_id}` },
              { header: "Kind", cell: (r) => r.kind.replace(/_/g, "-").toUpperCase() },
              { header: "Due", cell: (r) => formatDate(r.due_on) },
              { header: "Escalation", cell: (r) => (r.escalation_level > 0 ? <StatusChip value="high" label={`Level ${r.escalation_level}`} /> : "—") },
              {
                header: "Status",
                cell: (r) => (r.paused ? <StatusChip value="returned" label="Paused" /> : r.fired_on ? <StatusChip value="cleared" label="Fired" /> : <StatusChip value="pending" />),
              },
              {
                header: "",
                cell: (r) =>
                  r.paused ? (
                    <Button size="sm" variant="outline" onClick={() => resume.mutate(r.id)}>
                      Resume
                    </Button>
                  ) : !r.fired_on ? (
                    <Button size="sm" variant="outline" onClick={() => setPausingId(r.id)}>
                      Pause
                    </Button>
                  ) : null,
              },
            ]}
            rows={data?.data}
            rowKey={(r) => r.id}
            isLoading={isLoading}
            emptyTitle="No reminders"
          />
        </CardContent>
      </Card>

      <Dialog open={pausingId !== null} onOpenChange={(open) => !open && setPausingId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Pause reminder</DialogTitle>
          </DialogHeader>
          <Textarea value={reason} onChange={(e) => setReason(e.target.value)} />
          <DialogFooter>
            <Button onClick={doPause} disabled={!reason.trim() || pause.isPending}>
              Pause
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
