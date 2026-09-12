// Rreshti i parë: sa janë, sa rëndë, dhe si ndahen.
//
// Tri kutiza ashpërsie dhe një unazë. Numri i madh mban ngjyrën e vet dhe jo
// vetëm etiketën: një rresht me tri numra gri kërkon lexim, ndërsa tre numra të
// ngjyrosur lexohen me një shikim, dhe kjo është e vetmja gjë që ky rresht duhet
// të bëjë.

import { AlertTriangle, CheckCircle2, ShieldAlert, Sparkles, TrendingDown } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Card } from "./DashboardLayout";
import { byType, totals } from "./mock";

export function OverviewMetrics() {
  return (
    <div className="grid gap-4 lg:grid-cols-4">
      <Metric
        icon={ShieldAlert}
        label="Erëra gjithsej"
        value={totals.smells}
        note="mbi 312 skedarë"
        tone="brand"
      />
      <Metric
        icon={AlertTriangle}
        label="E rëndë"
        value={totals.high}
        note="kërkon vëmendje tani"
        tone="high"
      />
      <Metric
        icon={TrendingDown}
        label="E mesme"
        value={totals.medium}
        note="planifikoje"
        tone="medium"
      />
      <Metric icon={CheckCircle2} label="E lehtë" value={totals.low} note="kur të kesh kohë" tone="low" />

      <Card title="Sipas llojit" className="lg:col-span-2">
        <TypeDonut />
      </Card>

      <Card title="Sa mund të ndreqet vetë" className="lg:col-span-2">
        <AutomationPanel />
      </Card>
    </div>
  );
}

const TONES = {
  brand: {
    ring: "ring-brand-500/20",
    chip: "bg-brand-500/10 text-brand-500",
    value: "text-ink-900 dark:text-white",
  },
  high: {
    ring: "ring-high/20",
    chip: "bg-high/10 text-high",
    value: "text-high",
  },
  medium: {
    ring: "ring-medium/20",
    chip: "bg-medium/10 text-medium",
    value: "text-medium",
  },
  low: {
    ring: "ring-low/20",
    chip: "bg-low/10 text-low",
    value: "text-low",
  },
} as const;

function Metric({
  icon: Icon,
  label,
  value,
  note,
  tone,
}: {
  icon: typeof ShieldAlert;
  label: string;
  value: number;
  note: string;
  tone: keyof typeof TONES;
}) {
  const style = TONES[tone];
  return (
    <div
      className={`min-w-0 rounded-xl border border-ink-200 bg-white p-4 shadow-sm ring-1 ${style.ring} dark:border-ink-800 dark:bg-ink-900`}
    >
      <div className="flex items-start justify-between">
        <span className="text-[11px] font-semibold tracking-wider text-ink-500 uppercase dark:text-ink-400">
          {label}
        </span>
        <span className={`grid h-7 w-7 place-items-center rounded-lg ${style.chip}`}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className={`mt-3 text-3xl font-semibold tabular-nums ${style.value}`}>{value}</p>
      <p className="mt-1 text-xs text-ink-500 dark:text-ink-400">{note}</p>
    </div>
  );
}

function TypeDonut() {
  const total = byType.reduce((sum, slice) => sum + slice.value, 0);
  return (
    <div className="flex flex-wrap items-center gap-4 p-4">
      <div className="relative h-[150px] w-[150px] shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={byType}
              dataKey="value"
              nameKey="name"
              innerRadius={48}
              outerRadius={70}
              paddingAngle={2}
              strokeWidth={0}
            >
              {byType.map((slice) => (
                <Cell key={slice.name} fill={slice.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: "1px solid #1e293b",
                background: "#0f172a",
                color: "#e2e8f0",
                fontSize: 12,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        {/* Totali te vrima: numri që lexohet i pari, pa një etiketë të vetën. */}
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <div className="text-center">
            <p className="text-2xl font-semibold tabular-nums text-ink-900 dark:text-white">
              {total}
            </p>
            <p className="text-[10px] tracking-wider text-ink-500 uppercase dark:text-ink-400">
              erëra
            </p>
          </div>
        </div>
      </div>

      <ul className="min-w-0 flex-1 space-y-1.5">
        {byType.map((slice) => (
          <li key={slice.name} className="flex items-center gap-2 text-sm">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-sm"
              style={{ background: slice.color }}
              aria-hidden="true"
            />
            <span className="min-w-0 flex-1 truncate text-ink-600 dark:text-ink-300">
              {slice.name}
            </span>
            <span className="tabular-nums text-ink-500 dark:text-ink-400">{slice.value}</span>
            <span className="w-10 text-right text-xs tabular-nums text-ink-400 dark:text-ink-500">
              {Math.round((slice.value / total) * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Sa nga gjetjet i rishkruan motori vetë.
 *
 * Ndarë nga numri i përgjithshëm sepse është pyetje tjetër: «sa ka» dhe «sa mund
 * të hiqen sot pa u marrë vetë me to» nuk janë e njëjta gjë, dhe e dyta është ajo
 * që vendos se çfarë bëhet pas këtij ekrani.
 */
function AutomationPanel() {
  const share = Math.round((totals.automated / totals.smells) * 100);
  return (
    <div className="p-4">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-3xl font-semibold tabular-nums text-ink-900 dark:text-white">
            {totals.automated}
          </p>
          <p className="mt-1 text-xs text-ink-500 dark:text-ink-400">
            vende me rishkrim të verifikuar
          </p>
        </div>
        <span className="flex items-center gap-1.5 rounded-full bg-low/10 px-2.5 py-1 text-xs font-semibold text-low">
          <Sparkles className="h-3.5 w-3.5" />
          {share}% e tërësisë
        </span>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-ink-100 dark:bg-ink-800">
        <div className="h-full rounded-full bg-brand-500" style={{ width: `${share}%` }} />
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-lg bg-ink-50 p-3 dark:bg-ink-800/50">
          <dt className="text-xs text-ink-500 dark:text-ink-400">Aplikuar</dt>
          <dd className="mt-0.5 text-lg font-semibold tabular-nums text-low">{totals.applied}</dd>
        </div>
        <div className="rounded-lg bg-ink-50 p-3 dark:bg-ink-800/50">
          <dt className="text-xs text-ink-500 dark:text-ink-400">Në pritje</dt>
          <dd className="mt-0.5 text-lg font-semibold tabular-nums text-ink-700 dark:text-ink-200">
            {totals.automated - totals.applied}
          </dd>
        </div>
      </dl>
    </div>
  );
}
