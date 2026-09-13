// Veçoria kryesore: çfarë të bësh, dhe me çfarë klikimi.
//
// Ndarja mes «motori e rishkruan vetë» dhe «mbetet propozim» është vija më e
// rëndësishme e ekranit, dhe nuk është kozmetike: e para ka diff që lexohet dhe
// aplikohet tani; e dyta kërkon gjetjen e çdo reference në projekt, të cilën
// analiza nuk e provon dot. Një listë e vetme do t'i premtonte të dyja njësoj.

import { CheckCircle2, Eye, GitPullRequestArrow, Info, Lock, Wand2 } from "lucide-react";
import { Card } from "./DashboardLayout";
import type { Severity } from "./Panels";

export interface Suggestion {
  key: string;
  entity: string;
  file: string;
  line: number;
  smell: string;
  reason: string;
  refactoring: string;
  severity: Severity;
  automated: boolean;
}

const SEVERITY: Record<Severity, { chip: string; bar: string }> = {
  critical: { chip: "bg-high/10 text-high-ink ring-high/20", bar: "bg-high" },
  major: { chip: "bg-medium/10 text-medium-ink ring-medium/20", bar: "bg-medium" },
  minor: { chip: "bg-low/10 text-low-ink ring-low/20", bar: "bg-low" },
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
      <div className="space-y-4 xl:col-span-2">
        {automated.length > 0 && (
          <Card title={`Rishkrime të gatshme (${automated.length})`}>
            <ul className="m-0 list-none divide-y divide-ink-200 p-0 dark:divide-ink-800">
              {automated.slice(0, 6).map((item) => (
                <Row key={item.key} item={item} onOpen={onOpen} />
              ))}
            </ul>
            {automated.length > 6 && <More count={automated.length - 6} />}
          </Card>
        )}

        {advisory.length > 0 && (
          <Card title={`Propozime pa rishkrim (${advisory.length})`}>
            <p className="flex items-start gap-2 border-b border-ink-200 px-4 py-3 text-xs text-ink-500 dark:border-ink-800 dark:text-ink-400">
              <Info className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              Këto kërkojnë gjetjen e çdo reference në projekt, të cilën analiza nuk e provon dot.
              Mbeten propozim për autorin.
            </p>
            <ul className="m-0 list-none divide-y divide-ink-200 p-0 dark:divide-ink-800">
              {advisory.slice(0, 4).map((item) => (
                <Row key={item.key} item={item} onOpen={onOpen} />
              ))}
            </ul>
            {advisory.length > 4 && <More count={advisory.length - 4} />}
          </Card>
        )}
      </div>

      <div className="space-y-4">
        {children}
        <AppliedTimeline applied={applied} revert={revert} />
      </div>
    </div>
  );
}

function More({ count }: { count: number }) {
  return (
    <p className="border-t border-ink-200 px-4 py-2.5 text-xs text-ink-500 dark:border-ink-800 dark:text-ink-400">
      Edhe {count} të tjera te lista poshtë.
    </p>
  );
}

function Row({ item, onOpen }: { item: Suggestion; onOpen: (key: string) => void }) {
  const severity = SEVERITY[item.severity];
  return (
    <li className="relative px-4 py-3.5 transition hover:bg-ink-50 dark:hover:bg-ink-800/40">
      <span className={`absolute inset-y-0 left-0 w-0.5 ${severity.bar}`} aria-hidden="true" />

      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-medium text-ink-900 dark:text-white">
              {item.entity}
            </span>
            <span
              className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${severity.chip}`}
            >
              {item.smell}
            </span>
            {item.automated ? (
              <span className="flex items-center gap-1 rounded-full bg-brand-500/10 px-2 py-0.5 text-[11px] font-medium text-brand-ink">
                <Wand2 className="h-3 w-3" aria-hidden="true" />
                {item.refactoring}
              </span>
            ) : (
              <span className="flex items-center gap-1 rounded-full bg-ink-100 px-2 py-0.5 text-[11px] font-medium text-ink-600 dark:bg-ink-800 dark:text-ink-300">
                <Lock className="h-3 w-3" aria-hidden="true" />
                vetëm propozim
              </span>
            )}
          </div>

          <p className="mt-1 text-sm text-ink-600 dark:text-ink-300">{item.reason}</p>
          <p className="mt-1 truncate font-mono text-xs text-ink-500 dark:text-ink-400">
            {item.file}:{item.line}
          </p>
        </div>

        <button
          onClick={() => onOpen(item.key)}
          className="flex h-8 shrink-0 items-center gap-1.5 rounded-lg border border-ink-200 bg-transparent px-2.5 text-xs font-medium text-ink-600 transition hover:bg-white dark:border-ink-700 dark:text-ink-300 dark:hover:bg-ink-800"
        >
          <Eye className="h-3.5 w-3.5" aria-hidden="true" />
          {item.automated ? "Shfaq diff-in" : "Shfaq arsyen"}
        </button>
      </div>
    </li>
  );
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
        <p className="px-4 py-4 text-xs text-ink-500 dark:text-ink-400">
          Asgjë nuk është shkruar ende. Motori nuk e prek kodin pa u kërkuar.
        </p>
      ) : (
        <>
          <ol className="m-0 list-none space-y-0 p-4 pt-3">
            {applied.map((entry, index) => (
              <li key={entry.file} className="relative flex gap-3 pb-4 last:pb-0">
                {index < applied.length - 1 && (
                  <span
                    className="absolute top-6 left-[9px] h-full w-px bg-ink-200 dark:bg-ink-800"
                    aria-hidden="true"
                  />
                )}
                <span className="relative z-10 mt-0.5 grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full bg-low/15 text-low-ink">
                  <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <p className="truncate font-mono text-xs text-ink-800 dark:text-ink-100">
                    {entry.file}
                  </p>
                  <p className="mt-0.5 text-[11px] text-ink-500 dark:text-ink-400">{entry.when}</p>
                </div>
              </li>
            ))}
          </ol>
          {revert && (
            <div className="border-t border-ink-200 p-4 dark:border-ink-800">
              <p className="text-xs text-ink-500 dark:text-ink-400">
                Për t'i kthyer të gjitha:{" "}
                <code className="rounded bg-ink-100 px-1.5 py-0.5 font-mono text-ink-700 dark:bg-ink-800 dark:text-ink-200">
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
      <div className="space-y-3 p-4">
        <button
          onClick={onPrepare}
          disabled={busy || ready === 0}
          className="flex h-9 w-full items-center justify-center gap-2 rounded-lg border-0 bg-brand-600 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
        >
          <GitPullRequestArrow className="h-4 w-4" aria-hidden="true" />
          {busy ? "Duke përgatitur…" : "Përgatit patch-in"}
        </button>

        <p className="text-xs text-ink-500 dark:text-ink-400">
          <b className="text-ink-700 dark:text-ink-200">
            {ready} nga {total}
          </b>{" "}
          vende kanë një rishkrim që motori e provon.
        </p>

        {busy && progress && (
          <div role="status">
            <div className="h-1.5 overflow-hidden rounded-full bg-ink-100 dark:bg-ink-800">
              <div
                className="h-full rounded-full bg-brand-500 transition-[width]"
                style={{
                  width: `${progress.files_total ? (progress.files_done / progress.files_total) * 100 : 0}%`,
                }}
              />
            </div>
            <p className="mt-1.5 text-xs text-ink-500 dark:text-ink-400">
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
