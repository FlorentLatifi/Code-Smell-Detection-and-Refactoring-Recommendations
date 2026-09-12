// Dy panelet e mbetura: krahasimi i dy qasjeve, dhe skedarët më të ndotur.

import { FileCode2 } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "./DashboardLayout";

const TOOLTIP = {
  borderRadius: 8,
  border: "1px solid #1e293b",
  background: "#0f172a",
  color: "#e2e8f0",
  fontSize: 12,
} as const;

export interface ScoreRow {
  smell: string;
  rules: number | null;
  model: number | null;
}

/**
 * MCC për secilën erë, të dyja qasjet krah për krah.
 *
 * MCC e jo saktësia: mbi një bashkësi ku shumica e etiketave janë «asnjë», një
 * detektor që nuk ndez kurrë merr saktësi të lartë dhe MCC zero. Boshti ndalet
 * te 1 sepse ai është maksimumi, dhe një bosht që rritet me të dhënat i bën 0.27
 * e 0.29 të duken larg njëra-tjetrës.
 */
export function PerformanceCharts({ scores }: { scores: ScoreRow[] }) {
  const label = scores
    .map((row) => `${row.smell}: rregullat ${row.rules ?? "—"}, modeli ${row.model ?? "—"}`)
    .join("; ");
  return (
    <Card title="Rregullat kundrejt modelit (MCC)">
      <div className="h-[280px] p-4" role="img" aria-label={label}>
        {/* Si te unaza: etiketa e mban përmbajtjen, vizatimi fshihet. */}
        <div className="h-full w-full" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={scores} barGap={6} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#64748b33" vertical={false} />
            <XAxis
              dataKey="smell"
              tick={{ fill: "#94a3b8", fontSize: 12 }}
              axisLine={{ stroke: "#64748b33" }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fill: "#94a3b8", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip contentStyle={TOOLTIP} cursor={{ fill: "#64748b18" }} />
            <Legend
              wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
              formatter={(value) => (value === "rules" ? "A — rregullat" : "B — modeli")}
            />
            <Bar dataKey="rules" fill="#64748b" radius={[4, 4, 0, 0]} isAnimationActive={false} />
            <Bar dataKey="model" fill="#6366f1" radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
        </div>
      </div>
    </Card>
  );
}

export type Severity = "critical" | "major" | "minor";

export interface FileRow {
  cls: string;
  path: string;
  file: string;
  smells: number;
  severity: Severity;
}

const PILL: Record<Severity, string> = {
  critical: "bg-high/10 text-high-ink ring-high/20",
  major: "bg-medium/10 text-medium-ink ring-medium/20",
  minor: "bg-low/10 text-low-ink ring-low/20",
};

export function SmellyFilesTable({
  rows,
  onPick,
}: {
  rows: FileRow[];
  onPick: (file: string) => void;
}) {
  if (rows.length === 0) return null;
  return (
    <Card title="Skedarët më të ndotur">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-ink-200 text-left dark:border-ink-800">
              <Th>Klasa</Th>
              <Th>Shtegu</Th>
              <Th align="right">Erëra</Th>
              <Th>Ashpërsia</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-200 dark:divide-ink-800">
            {rows.map((row) => (
              <tr
                key={row.file}
                onClick={() => onPick(row.file)}
                className="cursor-pointer transition hover:bg-ink-50 dark:hover:bg-ink-800/40"
              >
                <td className="px-4 py-2.5">
                  <span className="flex items-center gap-2 font-medium text-ink-900 dark:text-white">
                    <FileCode2 className="h-3.5 w-3.5 shrink-0 text-ink-500" aria-hidden="true" />
                    <span className="truncate">{row.cls}</span>
                  </span>
                </td>
                <td
                  className="max-w-[220px] truncate px-4 py-2.5 font-mono text-xs text-ink-500 dark:text-ink-400"
                  title={row.path}
                >
                  {row.path}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-ink-700 dark:text-ink-200">
                  {row.smells}
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${PILL[row.severity]}`}
                  >
                    {row.severity}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function Th({ children, align = "left" }: { children: React.ReactNode; align?: "left" | "right" }) {
  return (
    <th
      scope="col"
      className={`px-4 py-2.5 text-[11px] font-semibold tracking-wider text-ink-500 uppercase dark:text-ink-400 ${
        align === "right" ? "text-right" : ""
      }`}
    >
      {children}
    </th>
  );
}
