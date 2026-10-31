import { useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { CheckCircle2, Link2, ShieldAlert, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/amanat/PageHeader";
import { DataTable } from "@/components/amanat/DataTable";
import { useAnchorNow, useAnchors, useAuditLog, useDevRestore, useDevTamper, useVerifyAudit } from "@/api/hooks/useAudit";
import { formatDateTime } from "@/lib/dates";
import type { AuditVerifyResult } from "@/api/types";

export function AuditPage() {
  const { data, isLoading } = useAuditLog({});
  const { data: anchors } = useAnchors();
  const verify = useVerifyAudit();
  const anchorNow = useAnchorNow();
  const tamper = useDevTamper();
  const restore = useDevRestore();
  const [result, setResult] = useState<AuditVerifyResult | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [capturedOriginal, setCapturedOriginal] = useState<Record<string, unknown> | null>(null);

  async function runVerify() {
    setVerifying(true);
    setResult(null);
    const res = await verify.mutateAsync();
    setTimeout(() => {
      setResult(res.data);
      setVerifying(false);
    }, 800);
  }

  async function doTamper() {
    const rows = data?.data ?? [];
    if (rows.length === 0) return;
    const target = rows[0];
    setCapturedOriginal(target.details);
    await tamper.mutateAsync({ seq: target.seq, new_details: { tampered: true } });
    toast.warning(`Tampered seq ${target.seq}. Run Verify now to see it detected.`);
  }

  async function doRestore() {
    const rows = data?.data ?? [];
    if (rows.length === 0 || !capturedOriginal) return;
    const target = rows[0];
    await restore.mutateAsync({ seq: target.seq, original_details: capturedOriginal });
    toast.success(`Restored seq ${target.seq}.`);
    setCapturedOriginal(null);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit"
        description="Append-only, hash-chained log. Every state-changing action is recorded here."
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => anchorNow.mutate()} className="gap-1.5">
              <Link2 className="h-3.5 w-3.5" />
              Anchor now
            </Button>
            <Button size="sm" onClick={runVerify} disabled={verifying}>
              Verify now
            </Button>
          </div>
        }
      />

      {verifying && <Progress value={66} className="animate-pulse" />}

      {result && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className={`flex items-center gap-2 rounded-lg border p-3 text-sm ${
            result.ok
              ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
              : "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300"
          }`}
        >
          {result.ok ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
          {result.ok
            ? `Chain verified OK. ${result.entries_checked} entries, ${result.anchors_checked} anchors checked.`
            : `Chain broken at seq ${result.first_broken_seq}.`}
        </motion.div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldAlert className="h-4 w-4" />
            DEMO_MODE: tamper / restore
          </CardTitle>
        </CardHeader>
        <CardContent className="flex gap-2">
          <Button variant="outline" size="sm" onClick={doTamper}>
            Tamper seq 1
          </Button>
          <Button variant="outline" size="sm" onClick={doRestore} disabled={!capturedOriginal}>
            Restore
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Chain</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <DataTable
              columns={[
                { header: "Seq", cell: (r) => r.seq },
                { header: "Action", cell: (r) => r.action },
                { header: "Entity", cell: (r) => `${r.entity_type}${r.entity_id ? ` #${r.entity_id}` : ""}` },
                { header: "Hash", cell: (r) => <code className="text-xs">{r.hash.slice(0, 10)}…</code> },
                { header: "When", cell: (r) => formatDateTime(r.ts) },
              ]}
              rows={(data?.data ?? []).slice(-50).reverse()}
              rowKey={(r) => r.seq}
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Anchors</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={[
              { header: "Anchored at", cell: (r) => formatDateTime(r.anchored_at) },
              { header: "Up to seq", cell: (r) => r.seq_upto },
              { header: "Head hash", cell: (r) => <code className="text-xs">{r.head_hash.slice(0, 10)}…</code> },
            ]}
            rows={anchors?.data}
            rowKey={(r) => r.id}
            emptyTitle="No anchors yet"
          />
        </CardContent>
      </Card>
    </div>
  );
}
