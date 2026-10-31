import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";
import { AlertCircle, CheckCircle2, HelpCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/amanat/PageHeader";
import { EmptyState } from "@/components/amanat/EmptyState";
import { useBankRequests, useRespondBankRequest } from "@/api/hooks/useBankRequests";
import { formatDate } from "@/lib/dates";
import { ApiError } from "@/api/client";
import type { BankRequestOut } from "@/api/types";

const FIELDS = ["fdr_number", "bank", "amount", "issue_date", "maturity", "beneficiary", "lien"];

export function BankPortalPage() {
  const { data, isLoading, refetch } = useBankRequests({ status: "pending" });
  const respond = useRespondBankRequest();
  const [active, setActive] = useState<BankRequestOut | null>(null);
  const [mode, setMode] = useState<"confirmed" | "details_differ" | "cannot_confirm" | null>(null);
  const [diffs, setDiffs] = useState<Record<string, string>>({});
  const [success, setSuccess] = useState(false);

  const pending = data?.data ?? [];

  function openMode(request: BankRequestOut, m: typeof mode) {
    setActive(request);
    setMode(m);
    setDiffs({});
  }

  async function submit() {
    if (!active || !mode) return;
    try {
      await respond.mutateAsync({
        id: active.id,
        outcome: mode,
        differingValues: mode === "details_differ" ? diffs : undefined,
      });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 1600);
      setActive(null);
      setMode(null);
      refetch();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not submit response.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Bank Verification Requests" description="Respond to AICTE's deposit verification requests for your bank." />

      {isLoading && <Skeleton className="h-40 w-full" />}
      {!isLoading && pending.length === 0 && (
        <EmptyState title="No pending requests" description="You're all caught up." icon={CheckCircle2} />
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {pending.map((r) => (
          <Card key={r.id} className="border-2">
            <CardHeader>
              <CardTitle className="text-base">{r.request_code}</CardTitle>
              <p className="text-xs text-muted-foreground">Due {formatDate(r.due_date)} · {r.branch}</p>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button className="w-full gap-2 bg-emerald-600 hover:bg-emerald-700" onClick={() => openMode(r, "confirmed")}>
                <CheckCircle2 className="h-4 w-4" />
                Confirm
              </Button>
              <Button variant="outline" className="w-full gap-2" onClick={() => openMode(r, "details_differ")}>
                <AlertCircle className="h-4 w-4" />
                Details differ
              </Button>
              <Button variant="ghost" className="w-full gap-2" onClick={() => openMode(r, "cannot_confirm")}>
                <HelpCircle className="h-4 w-4" />
                Cannot confirm
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={!!active} onOpenChange={(open) => !open && setActive(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {mode === "confirmed" && "Confirm deposit details"}
              {mode === "details_differ" && "Report differing details"}
              {mode === "cannot_confirm" && "Cannot confirm"}
            </DialogTitle>
          </DialogHeader>
          {mode === "details_differ" && (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Enter only the fields that differ from what was claimed.</p>
              {FIELDS.map((field) => (
                <div key={field}>
                  <Label className="capitalize">{field.replace(/_/g, " ")}</Label>
                  <Input
                    value={diffs[field] ?? ""}
                    onChange={(e) => setDiffs((d) => ({ ...d, [field]: e.target.value }))}
                  />
                </div>
              ))}
            </div>
          )}
          <DialogFooter>
            <Button onClick={submit} disabled={respond.isPending}>
              Submit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AnimatePresence>
        {success && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/20"
          >
            <div className="rounded-full bg-emerald-500 p-6 text-white shadow-xl">
              <CheckCircle2 className="h-16 w-16" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
