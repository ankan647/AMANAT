import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/amanat/PageHeader";
import { RoleGate } from "@/components/amanat/RoleGate";
import { useDemoScenarios, useResetDemo } from "@/api/hooks/useMetricsDemo";
import { apiGet, ApiError } from "@/api/client";
import type { InstitutionListResponse } from "@/api/types";

export function DemoPage() {
  const { data: scenarios, isLoading } = useDemoScenarios();
  const resetDemo = useResetDemo();
  const navigate = useNavigate();

  async function openScenario(code: string) {
    try {
      const resp = await apiGet<InstitutionListResponse>("/api/v1/institutions", { q: code });
      const row = resp.data[0];
      if (row) navigate(`/institutions/${row.id}`);
      else toast.error("Scenario institution not found — try resetting demo data.");
    } catch {
      toast.error("Could not open scenario.");
    }
  }

  async function doReset() {
    try {
      await resetDemo.mutateAsync();
      toast.success("Demo data reseeded.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not reset demo data.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Demo Scenarios"
        description="Each card is a named fixture (spec section 7.1) you can jump straight into."
        actions={
          <RoleGate allow={["admin"]}>
            <Button variant="outline" size="sm" className="gap-1.5" onClick={doReset} disabled={resetDemo.isPending}>
              <RotateCcw className="h-3.5 w-3.5" />
              Reset demo data
            </Button>
          </RoleGate>
        }
      />

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {scenarios?.map((s) => (
          <Card key={s.key}>
            <CardHeader>
              <CardTitle className="text-base">
                {s.key}. {s.title}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">{s.story}</p>
              <Button size="sm" variant="outline" onClick={() => openScenario(s.institution_code)}>
                Open {s.institution_code}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
