// Dy panelet e mbetura: krahasimi i dy qasjeve, dhe skedarët më të ndotur.

import { FileCode2 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "./DashboardLayout";
import type { Severity } from "./mock";
import { scores, smellyFiles } from "./mock";

const TOOLTIP = {
  borderRadius: 8,
  border: "1px solid #1e293b",
  background: "#0f172a",
  color: "#e2e8f0",
  fontSize: 12,
} as const;

/**
 * MCC për secilën erë, të dyja qasjet krah për krah.
 *
 * MCC e jo saktësia: mbi një bashkësi ku shumica e etiketave janë «asnjë», një
 * detektor që nuk ndez kurrë merr saktësi të lartë dhe MCC zero. Boshti ndalet
 * te 1 sepse ai është maksimumi i mundshëm, dhe një bosht që rritet me të dhënat
 * i bën 0.27 e 0.29 të duken larg njëra-tjetrës.
 */
export function PerformanceCharts() {
  return (
    <Card title="Rregullat kundrejt modelit (MCC)">
      <div className="h-[280px] p-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={scores} barGap={6} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="smell"
              tick={{ fill: "#94a3b8", fontSize: 12 }}
              axisLine={{ stroke: "#1e293b" }}
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
            <Bar dataKey="rules" fill="#64748b" radius={[4, 4, 0, 0]} />
            <Bar dataKey="model" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

const PILL: Record<Severity, string> = {
  high: "bg-high/10 text-high ring-high/20",
  medium: "bg-medium/10 text-medium ring-medium/20",
  low: "bg-low/10 text-low ring-low/20",
};

const PILL_LABEL: Record<Severity, string> = {
  high: "E rëndë",
  medium: "E mesme",
  low: "E lehtë",
};

export function SmellyFilesTable() {
  return (
    <Card title="Skedarët më të ndotur">
      <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-ink-200 text-left dark:border-ink-800">
            <th className="px-4 py-2.5 text-[11px] font-semibold tracking-wider text-ink-500 uppercase dark:text-ink-400">
              Klasa
            </th>
            <th className="px-4 py-2.5 text-[11px] font-semibold tracking-wider text-ink-500 uppercase dark:text-ink-400">
              Shtegu
            </th>
            <th className="px-4 py-2.5 text-right text-[11px] font-semibold tracking-wider text-ink-500 uppercase dark:text-ink-400">
              Erëra
            </th>
            <th className="px-4 py-2.5 text-[11px] font-semibold tracking-wider text-ink-500 uppercase dark:text-ink-400">
              Ashpërsia
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-200 dark:divide-ink-800">
          {smellyFiles.map((row) => (
            <tr
              key={row.cls}
              className="cursor-pointer transition hover:bg-ink-50 dark:hover:bg-ink-800/40"
            >
              <td className="px-4 py-2.5">
                <span className="flex items-center gap-2 font-medium text-ink-900 dark:text-white">
                  <FileCode2 className="h-3.5 w-3.5 text-ink-400" />
                  {row.cls}
                </span>
              </td>
              <td className="px-4 py-2.5 font-mono text-xs text-ink-500 dark:text-ink-400">
                {row.path}
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums text-ink-700 dark:text-ink-200">
                {row.smells}
              </td>
              <td className="px-4 py-2.5">
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${PILL[row.severity]}`}
                >
                  {PILL_LABEL[row.severity]}
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
