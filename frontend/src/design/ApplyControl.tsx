// Shkrimi mbi skedarët, si kontroll i vetëm te kolona e veprimeve.
//
// Dy hapa, sepse është i vetmi veprim që e ndryshon kodin: klikimi i parë thotë
// çfarë do të ndodhë dhe komandën që e kthen, i dyti e kryen. Gjendja e pemës
// pyetet përpara, që «ky shteg nuk është depo git» të thuhet para pritjes e jo
// pas saj (VD-100).

import { useState } from "react";
import { AlertTriangle, HardDriveDownload } from "lucide-react";
import { APPLY_REFUSAL_SQ, applyPatch } from "../api";
import type { ApplyResult, TreeState } from "../types";

export function ApplyControl({
  path,
  tree,
  ready,
  onApplied,
}: {
  path: string;
  tree: TreeState | null;
  /** Patch-i është përgatitur; pa të nuk ka çfarë të shkruhet. */
  ready: boolean;
  onApplied: (result: ApplyResult) => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  if (!ready) return null;

  if (tree && !tree.writable) {
    return (
      <p className="flex items-start gap-2 rounded-lg bg-medium/10 px-3 py-2 text-xs text-medium-ink">
        <AlertTriangle className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        {APPLY_REFUSAL_SQ[tree.reason ?? ""] ?? tree.detail}
      </p>
    );
  }

  async function write() {
    setBusy(true);
    setFailure(null);
    try {
      onApplied(await applyPatch(path));
      setConfirming(false);
    } catch (error) {
      setFailure((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2">
      {failure && (
        <p className="rounded-lg bg-high/10 px-3 py-2 text-xs text-high-ink" role="alert">
          {failure}
        </p>
      )}

      {confirming ? (
        <>
          <p className="rounded-lg bg-ink-50 px-3 py-2 text-xs text-ink-600 dark:bg-ink-800/60 dark:text-ink-300">
            Kjo rishkruan skedarët te disku. Pema është e pastër, ndaj{" "}
            <code className="font-mono">git restore .</code> e kthen gjithçka.
          </p>
          <div className="flex gap-2">
            <button
              onClick={write}
              disabled={busy}
              className="h-8 flex-1 rounded-lg bg-brand-600 text-xs font-semibold text-white transition hover:bg-brand-500 disabled:opacity-50"
            >
              {busy ? "Duke shkruar…" : "Po, shkruaji"}
            </button>
            <button
              onClick={() => setConfirming(false)}
              disabled={busy}
              className="h-8 rounded-lg border border-ink-200 px-3 text-xs font-medium text-ink-600 transition hover:bg-ink-50 dark:border-ink-700 dark:text-ink-300 dark:hover:bg-ink-800"
            >
              Anulo
            </button>
          </div>
        </>
      ) : (
        <button
          onClick={() => setConfirming(true)}
          disabled={tree === null}
          className="flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-ink-200 text-sm font-medium text-ink-700 transition hover:bg-ink-50 disabled:opacity-50 dark:border-ink-700 dark:text-ink-200 dark:hover:bg-ink-800"
        >
          <HardDriveDownload className="h-4 w-4" aria-hidden="true" />
          Apliko te skedarët
        </button>
      )}
    </div>
  );
}
