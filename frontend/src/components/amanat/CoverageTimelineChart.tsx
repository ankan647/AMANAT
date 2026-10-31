import { useState } from "react";
import ReactECharts from "echarts-for-react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { CoverageTimeline } from "@/api/types";
import { formatINR } from "@/lib/formatINR";
import { formatDate } from "@/lib/dates";

export function CoverageTimelineChart({ timeline }: { timeline: CoverageTimeline }) {
  const [asTable, setAsTable] = useState(false);

  const dates = Array.from(new Set([...timeline.required.map((p) => p.date), ...timeline.valid.map((p) => p.date)])).sort();
  const requiredByDate = new Map(timeline.required.map((p) => [p.date, p.paise]));
  const validByDate = new Map(timeline.valid.map((p) => [p.date, p.paise]));

  const option = {
    tooltip: {
      trigger: "axis",
      formatter: (params: { axisValue: string; seriesName: string; value: number }[]) => {
        const lines = params.map((p) => `${p.seriesName}: ${formatINR(p.value)}`);
        return `${formatDate(params[0].axisValue)}<br/>${lines.join("<br/>")}`;
      },
    },
    legend: { data: ["Required", "Valid"] },
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
    xAxis: { type: "category", data: dates, axisLabel: { formatter: (v: string) => formatDate(v) } },
    yAxis: { type: "value", axisLabel: { formatter: (v: number) => formatINR(v) } },
    series: [
      {
        name: "Required",
        type: "line",
        step: "end",
        data: dates.map((d) => requiredByDate.get(d) ?? null),
        lineStyle: { color: "#4338ca", width: 2 },
        itemStyle: { color: "#4338ca" },
        markArea:
          timeline.gaps.length > 0
            ? {
                itemStyle: { color: "rgba(244,63,94,0.12)" },
                label: { show: true, formatter: (p: { name?: string }) => p.name ?? "", color: "#e11d48", fontSize: 10 },
                data: timeline.gaps.map((g) => [
                  { xAxis: g.start, name: `${g.days}-day gap` },
                  { xAxis: g.end },
                ]),
              }
            : undefined,
      },
      {
        name: "Valid",
        type: "line",
        step: "end",
        areaStyle: { color: "rgba(13,148,136,0.15)" },
        data: dates.map((d) => validByDate.get(d) ?? null),
        lineStyle: { color: "#0d9488", width: 2 },
        itemStyle: { color: "#0d9488" },
      },
    ],
  };

  return (
    <div>
      <div className="mb-2 flex justify-end">
        <Button variant="outline" size="sm" onClick={() => setAsTable((v) => !v)}>
          {asTable ? "View as chart" : "View as table"}
        </Button>
      </div>
      {asTable ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Required</TableHead>
              <TableHead>Valid</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {dates.map((d) => (
              <TableRow key={d}>
                <TableCell>{formatDate(d)}</TableCell>
                <TableCell>{formatINR(requiredByDate.get(d) ?? 0)}</TableCell>
                <TableCell>{formatINR(validByDate.get(d) ?? 0)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <ReactECharts option={{ ...option, aria: { enabled: true } }} style={{ height: 320 }} />
      )}
    </div>
  );
}
