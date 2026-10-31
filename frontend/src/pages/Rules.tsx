import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/amanat/PageHeader";
import { RoleGate } from "@/components/amanat/RoleGate";
import { StatusChip } from "@/components/amanat/StatusChip";
import { MoneyText } from "@/components/amanat/MoneyText";
import {
  useApproveRuleVersion,
  useCreateRuleVersion,
  useImpactPreview,
  useRejectRuleVersion,
  useRules,
  useSubmitRuleVersion,
} from "@/api/hooks/useRules";
import { useAuth } from "@/lib/AuthContext";
import { formatDate } from "@/lib/dates";
import { ApiError } from "@/api/client";
import type { ImpactPreview, RuleVersionOut } from "@/api/types";

const draftSchema = z.object({
  effective_from: z.string().min(1, "Required"),
  note: z.string().min(1, "Required"),
});

export function RulesPage() {
  const { data, isLoading } = useRules();
  const { user } = useAuth();
  const createVersion = useCreateRuleVersion();
  const submitVersion = useSubmitRuleVersion();
  const approveVersion = useApproveRuleVersion();
  const rejectVersion = useRejectRuleVersion();
  const impactPreview = useImpactPreview();
  const [previewFor, setPreviewFor] = useState<ImpactPreview | null>(null);
  const [draftRuleId, setDraftRuleId] = useState<number | null>(null);

  const form = useForm<z.infer<typeof draftSchema>>({
    resolver: zodResolver(draftSchema),
    defaultValues: { effective_from: "", note: "" },
  });

  if (isLoading || !data) return <Skeleton className="h-64 w-full" />;

  async function runPreview(versionId: number) {
    try {
      const res = await impactPreview.mutateAsync(versionId);
      setPreviewFor(res.data);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not compute preview.");
    }
  }

  async function approve(version: RuleVersionOut) {
    try {
      await approveVersion.mutateAsync(version.id);
      toast.success("Rule version approved and now active.");
    } catch (err) {
      if (err instanceof ApiError && err.code === "SOD_VIOLATION") {
        toast.error("You proposed this version, so you cannot approve it yourself.");
      } else {
        toast.error(err instanceof ApiError ? err.message : "Could not approve.");
      }
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Rules" description='Every seed rule is labelled "Seed - pending AICTE legal validation".' />

      {data.data.map((rule) => (
        <Card key={rule.id}>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">{rule.title}</CardTitle>
            <RoleGate allow={["admin"]}>
              <Dialog open={draftRuleId === rule.id} onOpenChange={(open) => setDraftRuleId(open ? rule.id : null)}>
                <DialogTrigger asChild>
                  <Button size="sm" variant="outline">New version</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Draft a new version of {rule.title}</DialogTitle>
                  </DialogHeader>
                  <form
                    className="space-y-3"
                    onSubmit={form.handleSubmit(async (values) => {
                      try {
                        await createVersion.mutateAsync({
                          ruleId: rule.id,
                          effective_from: values.effective_from,
                          applicability: {},
                          parameters: {},
                          note: values.note,
                        });
                        toast.success("Draft created.");
                        setDraftRuleId(null);
                        form.reset();
                      } catch (err) {
                        toast.error(err instanceof ApiError ? err.message : "Could not create draft.");
                      }
                    })}
                  >
                    <div>
                      <Label>Effective from</Label>
                      <Input type="date" {...form.register("effective_from")} />
                      {form.formState.errors.effective_from && (
                        <p className="text-xs text-destructive">{form.formState.errors.effective_from.message}</p>
                      )}
                    </div>
                    <div>
                      <Label>Note</Label>
                      <Textarea {...form.register("note")} placeholder="Seed - pending AICTE legal validation; ..." />
                    </div>
                    <DialogFooter>
                      <Button type="submit" disabled={createVersion.isPending}>Create draft</Button>
                    </DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>
            </RoleGate>
          </CardHeader>
          <CardContent className="space-y-3">
            {rule.versions.map((v) => (
              <div key={v.id} className="rounded-lg border p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium">
                      v{v.version} · {formatDate(v.effective_from)} — {v.effective_to ? formatDate(v.effective_to) : "onward"}
                    </p>
                    <p className="text-xs text-muted-foreground">{v.note}</p>
                  </div>
                  <StatusChip value={v.status} />
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {Object.keys(v.applicability).length === 0 ? (
                    <Badge variant="secondary">Applies to everyone</Badge>
                  ) : (
                    Object.entries(v.applicability).map(([k, val]) => (
                      <Badge key={k} variant="secondary">
                        {k}: {JSON.stringify(val)}
                      </Badge>
                    ))
                  )}
                </div>
                {v.parameters.amounts != null && (
                  <div className="mt-2 flex flex-wrap gap-3 text-xs">
                    {Object.entries(v.parameters.amounts as Record<string, number>).map(([cat, amt]) => (
                      <span key={cat}>
                        {cat}: <MoneyText paise={amt} />
                      </span>
                    ))}
                  </div>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  {v.status === "draft" && (
                    <RoleGate allow={["admin"]}>
                      <>
                        <Button size="sm" variant="outline" onClick={() => runPreview(v.id)}>
                          Impact preview
                        </Button>
                        <Button size="sm" onClick={() => submitVersion.mutate(v.id)}>
                          Submit for approval
                        </Button>
                      </>
                    </RoleGate>
                  )}
                  {v.status === "pending_approval" && (
                    <RoleGate
                      allow={["admin"]}
                      reason={v.proposed_by === user?.id ? "You proposed this version, so you cannot approve it yourself." : undefined}
                    >
                      <>
                        <Button size="sm" disabled={v.proposed_by === user?.id} onClick={() => approve(v)}>
                          Approve
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => rejectVersion.mutate({ versionId: v.id, reason: "Not adopted" })}>
                          Reject
                        </Button>
                      </>
                    </RoleGate>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}

      <Dialog open={!!previewFor} onOpenChange={(open) => !open && setPreviewFor(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Impact preview</DialogTitle>
          </DialogHeader>
          {previewFor && (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">{previewFor.unchanged_count} institution(s) unaffected.</p>
              <div className="max-h-96 space-y-1.5 overflow-y-auto">
                {previewFor.changes.map((c) => (
                  <div key={c.institution_id} className="flex items-center justify-between rounded-lg border p-2 text-sm">
                    <span>{c.name}</span>
                    <div className="flex items-center gap-2 text-xs">
                      <StatusChip value={c.before_status} /> <span>→</span> <StatusChip value={c.after_status} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
