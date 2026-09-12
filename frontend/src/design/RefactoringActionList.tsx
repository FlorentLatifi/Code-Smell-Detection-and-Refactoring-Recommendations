// Veçoria kryesore: çfarë të bësh, dhe me çfarë klikimi.
//
// Ndarja mes «motori e rishkruan vetë» dhe «mbetet propozim» është vija më e
// rëndësishme e tërë ekranit, dhe nuk është kozmetike: e para ka diff që mund të
// lexohet dhe të aplikohet tani; e dyta kërkon gjetjen e çdo reference në
// projekt, të cilën analiza nuk e provon dot. Një listë e vetme do t'i premtonte
// të dyja njësoj.

import { useState } from "react";
import {
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Eye,
  GitPullRequestArrow,
  Info,
  Lock,
  Wand2,
} from "lucide-react";
import { Card } from "./DashboardLayout";
import type { Finding, Severity } from "./mock";
import { applied, findings } from "./mock";

const SEVERITY: Record<Severity, { label: string; chip: string; bar: string }> = {
  high: { label: "E rëndë", chip: "bg-high/10 text-high ring-high/20", bar: "bg-high" },
  medium: { label: "E mesme", chip: "bg-medium/10 text-medium ring-medium/20", bar: "bg-medium" },
  low: { label: "E lehtë", chip: "bg-low/10 text-low ring-low/20", bar: "bg-low" },
};

export function RefactoringActionList() {
  const automated = findings.filter((f) => f.automated);
  const advisory = findings.filter((f) => !f.automated);

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <div className="space-y-4 xl:col-span-2">
        <Card
          title="Rishkrime të gatshme"
          action={
            <button className="flex h-8 items-center gap-1.5 rounded-lg bg-brand-600 px-3 text-xs font-semibold text-white transition hover:bg-brand-500">
              <GitPullRequestArrow className="h-3.5 w-3.5" />
              Apliko të gjitha ({automated.length})
            </button>
          }
        >
          <ul className="divide-y divide-ink-200 dark:divide-ink-800">
            {automated.map((finding) => (
              <Suggestion key={finding.id} finding={finding} />
            ))}
          </ul>
        </Card>

        <Card title="Propozime pa rishkrim">
          <p className="flex items-start gap-2 border-b border-ink-200 px-4 py-3 text-xs text-ink-500 dark:border-ink-800 dark:text-ink-400">
            <Info className="mt-px h-3.5 w-3.5 shrink-0" />
            Këto kërkojnë gjetjen e çdo reference në projekt, të cilën analiza nuk e provon dot.
            Mbeten propozim për autorin.
          </p>
          <ul className="divide-y divide-ink-200 dark:divide-ink-800">
            {advisory.map((finding) => (
              <Suggestion key={finding.id} finding={finding} />
            ))}
          </ul>
        </Card>
      </div>

      <AppliedTimeline />
    </div>
  );
}

function Suggestion({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(false);
  const severity = SEVERITY[finding.severity];

  return (
    <li className="group relative px-4 py-3.5 transition hover:bg-ink-50 dark:hover:bg-ink-800/40">
      <span className={`absolute inset-y-0 left-0 w-0.5 ${severity.bar}`} aria-hidden="true" />

      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-medium text-ink-900 dark:text-white">
              {finding.entity}
            </span>
            <span
              className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${severity.chip}`}
            >
              {finding.smell}
            </span>
            {finding.automated ? (
              <span className="flex items-center gap-1 rounded-full bg-brand-500/10 px-2 py-0.5 text-[11px] font-medium text-brand-500">
                <Wand2 className="h-3 w-3" />
                automatik
              </span>
            ) : (
              <span className="flex items-center gap-1 rounded-full bg-ink-100 px-2 py-0.5 text-[11px] font-medium text-ink-500 dark:bg-ink-800 dark:text-ink-400">
                <Lock className="h-3 w-3" />
                vetëm propozim
              </span>
            )}
          </div>

          <p className="mt-1 text-sm text-ink-600 dark:text-ink-300">{finding.reason}</p>

          <p className="mt-1 flex items-center gap-2 font-mono text-xs text-ink-400 dark:text-ink-500">
            {finding.file}
            {finding.automated && (
              <>
                <span className="text-ink-300 dark:text-ink-700">·</span>
                <span className="text-low">+{finding.added}</span>
                <span className="text-high">−{finding.removed}</span>
              </>
            )}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            onClick={() => setOpen((was) => !was)}
            className="flex h-8 items-center gap-1.5 rounded-lg border border-ink-200 px-2.5 text-xs font-medium text-ink-600 transition hover:bg-white dark:border-ink-700 dark:text-ink-300 dark:hover:bg-ink-800"
          >
            <Eye className="h-3.5 w-3.5" />
            Shfaq diff-in
            <ChevronRight
              className={`h-3.5 w-3.5 transition ${open ? "rotate-90" : ""}`}
              aria-hidden="true"
            />
          </button>
          {finding.automated && (
            <button className="flex h-8 items-center gap-1.5 rounded-lg bg-brand-600 px-2.5 text-xs font-semibold text-white transition hover:bg-brand-500">
              <GitPullRequestArrow className="h-3.5 w-3.5" />
              Apliko
            </button>
          )}
        </div>
      </div>

      {open && <DiffPreview />}
    </li>
  );
}

/** Diff i rremë, sa për formën e bllokut. */
function DiffPreview() {
  const lines = [
    { kind: " ", text: "public double processPayment(Order order) {" },
    { kind: "-", text: "    if (order.getTotal() > 0) {" },
    { kind: "-", text: "        validate(order);" },
    { kind: "-", text: "        log.info(\"paid\");" },
    { kind: "-", text: "    }" },
    { kind: "+", text: "    validateAndLog(order);" },
    { kind: " ", text: "    return order.getTotal();" },
    { kind: " ", text: "}" },
  ];
  return (
    <pre className="mt-3 overflow-x-auto rounded-lg border border-ink-200 bg-ink-50 p-3 font-mono text-xs leading-relaxed dark:border-ink-800 dark:bg-ink-950">
      {lines.map((line, index) => (
        <div
          key={index}
          className={
            line.kind === "+"
              ? "bg-low/10 text-low"
              : line.kind === "-"
                ? "bg-high/10 text-high"
                : "text-ink-500 dark:text-ink-400"
          }
        >
          <span className="mr-2 select-none opacity-60">{line.kind}</span>
          {line.text}
        </div>
      ))}
    </pre>
  );
}

/**
 * Çfarë është shkruar vërtet te skedarët.
 *
 * Ndarë nga lista e propozimeve sepse është gjendje e kaluar e jo punë e mbetur.
 * Ngjitur pas saj rri komanda që e kthen gjithçka: një panel që shkruan mbi kodin
 * e dikujt duhet ta thotë atë para se të pyetet.
 */
function AppliedTimeline() {
  return (
    <Card title="Aplikuar në këtë seancë">
      <ol className="space-y-0 p-4 pt-3">
        {applied.map((entry, index) => (
          <li key={entry.id} className="relative flex gap-3 pb-4 last:pb-0">
            {index < applied.length - 1 && (
              <span
                className="absolute top-6 left-[9px] h-full w-px bg-ink-200 dark:bg-ink-800"
                aria-hidden="true"
              />
            )}
            <span className="relative z-10 mt-0.5 grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full bg-low/15 text-low">
              <CheckCircle2 className="h-3 w-3" />
            </span>
            <div className="min-w-0">
              <p className="truncate font-mono text-xs text-ink-800 dark:text-ink-100">
                {entry.entity}
              </p>
              <p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-ink-500 dark:text-ink-400">
                <span>{entry.smell}</span>
                <span className="text-ink-300 dark:text-ink-700">·</span>
                <Clock3 className="h-3 w-3" />
                {entry.when}
              </p>
            </div>
          </li>
        ))}
      </ol>

      <div className="border-t border-ink-200 p-4 dark:border-ink-800">
        <p className="text-xs text-ink-500 dark:text-ink-400">
          Për t'i kthyer të gjitha:{" "}
          <code className="rounded bg-ink-100 px-1.5 py-0.5 font-mono text-ink-700 dark:bg-ink-800 dark:text-ink-200">
            git restore .
          </code>
        </p>
        <button className="mt-3 flex h-8 w-full items-center justify-center gap-1.5 rounded-lg border border-ink-200 text-xs font-medium text-ink-600 transition hover:bg-ink-50 dark:border-ink-700 dark:text-ink-300 dark:hover:bg-ink-800">
          Hap historikun e plotë
          <ArrowUpRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </Card>
  );
}
