// Veçoria kryesore: çfarë të bësh, dhe me çfarë klikimi.
//
// Ndarja mes «motori e rishkruan vetë» dhe «mbetet propozim» është vija më e
// rëndësishme e ekranit, dhe nuk është kozmetike: e para ka diff që lexohet dhe
// aplikohet tani; e dyta kërkon gjetjen e çdo reference në projekt, të cilën
// analiza nuk e provon dot. Një listë e vetme do t'i premtonte të dyja njësoj.

import { CheckCircle2, Eye, GitPullRequestArrow, Info, Lock, Wand2 } from "lucide-react";
import type { Condition } from "../types";
import { Card } from "./DashboardLayout";
import type { Severity } from "./Panels";

export interface Suggestion {
  key: string;
  entity: string;
  file: string;
  line: number;
  smell: string;
  reason: string;
  /** Klauzolat e matura; kur mungojnë, rreshti bie te `reason`. */
  conditions: Condition[];
  refactoring: string;
  severity: Severity;
  automated: boolean;
}

const SEVERITY: Record<Severity, { bar: string; ink: string }> = {
  critical: { bar: "bg-high", ink: "text-high-ink" },
  major: { bar: "bg-medium", ink: "text-medium-ink" },
  minor: { bar: "bg-low", ink: "text-low-ink" },
};

export function RefactoringActionList({
  suggestions,
  onOpen,
  applied,
  revert,
  children,
}: {
  suggestions: Suggestion[];
  onOpen: (key: string) => void;
  /** Çfarë ka shkuar te disku në këtë seancë. */
  applied: { file: string; when: string }[];
  revert: string | null;
  /** Veprimet e patch-it dhe të shkrimit, që i mban thirrësi. */
  children?: React.ReactNode;
}) {
  const automated = suggestions.filter((s) => s.automated);
  const advisory = suggestions.filter((s) => !s.automated);

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      {/* `min-w-0` te të dy kolonat: një element rrjeti nuk tkurret nën gjerësinë
          e tekstit të tij më të gjatë pa të. Mbi `apache/ambari` një shteg i
          prerë me `truncate` e shtynte kartën në 718 piksela brenda një ekrani
          375-pikselësh (VD-111). */}
      <div className="min-w-0 space-y-4 xl:col-span-2">
        {automated.length > 0 && (
          <Card title={`Rishkrime të gatshme (${automated.length})`}>
            <ul className="m-0 mt-2 list-none divide-y divide-ink-200 border-t border-ink-200 p-0 dark:divide-ink-800 dark:border-ink-800">
              {automated.slice(0, 6).map((item) => (
                <Row key={item.key} item={item} onOpen={onOpen} />
              ))}
            </ul>
            {automated.length > 6 && <More count={automated.length - 6} />}
          </Card>
        )}

        {advisory.length > 0 && (
          <Card title={`Propozime pa rishkrim (${advisory.length})`}>
            <p className="m-0 flex items-start gap-2 px-4 pt-1 pb-3 text-xs text-ink-500 dark:text-ink-400">
              <Info className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              Këto kërkojnë gjetjen e çdo reference në projekt, të cilën analiza nuk e provon dot.
              Mbeten propozim për autorin.
            </p>
            <ul className="m-0 list-none divide-y divide-ink-200 border-t border-ink-200 p-0 dark:divide-ink-800 dark:border-ink-800">
              {advisory.slice(0, 4).map((item) => (
                <Row key={item.key} item={item} onOpen={onOpen} />
              ))}
            </ul>
            {advisory.length > 4 && <More count={advisory.length - 4} />}
          </Card>
        )}
      </div>

      <div className="min-w-0 space-y-4">
        {children}
        <AppliedTimeline applied={applied} revert={revert} />
      </div>
    </div>
  );
}

function More({ count }: { count: number }) {
  return (
    <p className="m-0 border-t border-ink-200 px-4 py-2.5 text-xs text-ink-500 dark:border-ink-800 dark:text-ink-400">
      Edhe {count} të tjera te lista poshtë.
    </p>
  );
}

function Row({ item, onOpen }: { item: Suggestion; onOpen: (key: string) => void }) {
  const severity = SEVERITY[item.severity];
  return (
    <li className="relative py-3.5 pr-4 pl-5 transition hover:bg-ink-50 dark:hover:bg-ink-800/40">
      <span className={`absolute top-3 bottom-3 left-0 w-[3px] rounded-r-sm ${severity.bar}`} aria-hidden="true" />

      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="m-0 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="min-w-0 font-mono text-[13.5px] font-medium [overflow-wrap:anywhere] text-ink-900 dark:text-white">
              {item.entity}
            </span>
            <span className="text-[13px] text-ink-700 dark:text-ink-200">{item.smell}</span>
            <span className={`text-xs font-medium ${severity.ink}`}>{item.severity}</span>
          </p>

          <Clauses item={item} />

          <p className="m-0 mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-500 dark:text-ink-400">
            <span className="min-w-0 truncate font-mono">
              {item.file}:{item.line}
            </span>
            {item.automated ? (
              <span className="flex items-center gap-1 font-medium text-brand-ink">
                <Wand2 className="h-3 w-3" aria-hidden="true" />
                {item.refactoring}
              </span>
            ) : (
              <span className="flex items-center gap-1">
                <Lock className="h-3 w-3" aria-hidden="true" />
                vetëm propozim
              </span>
            )}
          </p>
        </div>

        <button
          onClick={() => onOpen(item.key)}
          className="flex h-8 shrink-0 items-center gap-1.5 rounded-md border border-ink-200 bg-transparent px-2.5 text-xs font-medium text-ink-700 transition hover:bg-white dark:border-ink-700 dark:text-ink-200 dark:hover:bg-ink-800"
        >
          <Eye className="h-3.5 w-3.5" aria-hidden="true" />
          {item.automated ? "Shfaq diff-in" : "Shfaq arsyen"}
        </button>
      </div>
    </li>
  );
}

/**
 * Klauzolat që ndezën, si lexime: metrika, e matura, pragu.
 *
 * Arsyeja vinte si fjali e serverit, «MLOC = 77 (> 35) and CC = 36 (>= 4)», me
 * «and» anglisht brenda një ekrani shqip dhe me katër numra të ngjitur në një
 * varg. Si lexime veç e veç, e matura del e theksuar dhe pragu pranë saj (VD-119).
 */
function Clauses({ item }: { item: Suggestion }) {
  if (item.conditions.length === 0) {
    return <p className="m-0 mt-1.5 text-sm text-ink-600 dark:text-ink-300">{item.reason}</p>;
  }
  return (
    <ul className="m-0 mt-2 flex list-none flex-wrap gap-1.5 p-0" aria-label="Klauzolat që ndezën">
      {item.conditions.map((condition) => (
        <li
          key={`${condition.metric}${condition.operator}`}
          className="rounded-sm bg-ink-100 px-1.5 py-0.5 font-mono text-xs text-ink-600 dark:bg-ink-800 dark:text-ink-300"
        >
          {condition.metric}{" "}
          <b className="font-semibold text-ink-900 dark:text-white">{reading(condition.value)}</b>{" "}
          {condition.operator} {reading(condition.threshold)}
        </li>
      ))}
    </ul>
  );
}

/** TCC-ja vjen si 0.0183661; tri shifra pas presjes mjaftojnë për ta krahasuar. */
function reading(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(3)));
}

/**
 * Çfarë është shkruar vërtet te skedarët, në këtë seancë.
 *
 * Ngjitur pas saj rri komanda që e kthen gjithçka: një panel që shkruan mbi
 * kodin e dikujt duhet ta thotë atë para se të pyetet (VD-100).
 */
function AppliedTimeline({
  applied,
  revert,
}: {
  applied: { file: string; when: string }[];
  revert: string | null;
}) {
  return (
    <Card title="Aplikuar në këtë seancë">
      {applied.length === 0 ? (
        <p className="m-0 px-4 pt-1 pb-4 text-xs text-ink-500 dark:text-ink-400">
          Asgjë nuk është shkruar ende. Motori nuk e prek kodin pa u kërkuar.
        </p>
      ) : (
        <>
          <ol className="m-0 list-none space-y-0 p-4 pt-2">
            {applied.map((entry, index) => (
              <li key={entry.file} className="relative flex gap-3 pb-4 last:pb-0">
                {index < applied.length - 1 && (
                  <span
                    className="absolute top-6 left-[9px] h-full w-px bg-ink-200 dark:bg-ink-800"
                    aria-hidden="true"
                  />
                )}
                <span className="relative z-10 mt-0.5 grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full bg-ok/15 text-ok-ink">
                  <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <p className="m-0 truncate font-mono text-xs text-ink-800 dark:text-ink-100">
                    {entry.file}
                  </p>
                  <p className="m-0 mt-0.5 text-[11px] text-ink-500 dark:text-ink-400">{entry.when}</p>
                </div>
              </li>
            ))}
          </ol>
          {revert && (
            <div className="border-t border-ink-200 p-4 dark:border-ink-800">
              <p className="m-0 text-xs text-ink-500 dark:text-ink-400">
                Për t'i kthyer të gjitha:{" "}
                <code className="rounded-sm bg-ink-100 px-1.5 py-0.5 font-mono text-ink-700 dark:bg-ink-800 dark:text-ink-200">
                  {revert}
                </code>
              </p>
            </div>
          )}
        </>
      )}
    </Card>
  );
}

/** Butoni i patch-it dhe i shkrimit, si kartë te kolona e djathtë. */
export function PatchActions({
  ready,
  total,
  busy,
  progress,
  onPrepare,
  children,
}: {
  ready: number;
  total: number;
  busy: boolean;
  progress: { files_done: number; files_total: number; changes: number } | null;
  onPrepare: () => void;
  children?: React.ReactNode;
}) {
  return (
    <Card title="Veprimet">
      <div className="space-y-3 px-4 pt-2 pb-4">
        <button
          onClick={onPrepare}
          disabled={busy || ready === 0}
          className="flex h-9 w-full items-center justify-center gap-2 rounded-md border-0 bg-brand-600 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
        >
          <GitPullRequestArrow className="h-4 w-4" aria-hidden="true" />
          {busy ? "Duke përgatitur…" : "Përgatit patch-in"}
        </button>

        <p className="m-0 text-xs text-ink-500 dark:text-ink-400">
          <b className="text-ink-800 dark:text-ink-100">
            {ready} nga {total}
          </b>{" "}
          vende kanë një rishkrim që motori e provon.
        </p>

        {busy && progress && (
          <div role="status">
            <div className="h-1.5 overflow-hidden rounded-sm bg-ink-100 dark:bg-ink-800">
              <div
                className="h-full bg-brand-500 transition-[width]"
                style={{
                  width: `${progress.files_total ? (progress.files_done / progress.files_total) * 100 : 0}%`,
                }}
              />
            </div>
            <p className="m-0 mt-1.5 text-xs text-ink-500 dark:text-ink-400">
              {progress.files_done} nga {progress.files_total} skedarë (
              {progress.files_total
                ? Math.round((progress.files_done / progress.files_total) * 100)
                : 0}
              %),{" "}
              {progress.changes === 0
                ? "ende asnjë ndryshim"
                : `${progress.changes} ${progress.changes === 1 ? "ndryshim" : "ndryshime"} deri tani`}
              .
            </p>
          </div>
        )}

        {children}
      </div>
    </Card>
  );
}
