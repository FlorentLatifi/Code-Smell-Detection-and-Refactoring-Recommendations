import { useState } from "react";
import { patch } from "./api";
import type { PatchResult } from "./types";

/**
 * The last step the engine can take on its own: hand the author the change.
 *
 * Deliberately not an "apply" button. Nothing here writes to the tree, and the
 * diff is shown before it can be taken anywhere, because the engine rewrites
 * the author's own source and a change nobody read is a change nobody agreed to
 * (ENGINEERING.md §4, VD-49).
 *
 * The counts beside it matter as much as the diff. A short patch has four
 * different meanings -- nothing was found, nothing was safe, some rewrites
 * collide, or the budget ran out -- and a reader who cannot tell them apart
 * would read "3 changes" as "3 problems".
 */
export function Patch({ path }: { path: string }) {
  const [result, setResult] = useState<PatchResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function ask() {
    setBusy(true);
    setFailure(null);
    setResult(null);
    setCopied(false);
    try {
      setResult(await patch(path));
    } catch (error) {
      setFailure((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      // A blocked clipboard is not worth an error banner: the diff is on screen
      // and can be selected by hand.
      setCopied(false);
    }
  }

  return (
    <section className="patch">
      <div className="patch-bar">
        <button className="primary" onClick={ask} disabled={busy || !path.trim()}>
          {busy ? "Duke përgatitur…" : "Përgatit patch-in"}
        </button>
        <p className="caption">
          Nxjerr një diff të unifikuar për çdo rishkrim që motori e provon të sigurt. Asnjë
          skedar nuk preket; aplikimi mbetet vendimi yt.
        </p>
      </div>

      {failure && (
        <p className="failure" role="alert">
          {failure}
        </p>
      )}

      {result && <Outcome result={result} onCopy={copy} copied={copied} />}
    </section>
  );
}

function Outcome({
  result,
  onCopy,
  copied,
}: {
  result: PatchResult;
  onCopy: (text: string) => void;
  copied: boolean;
}) {
  if (result.changes === 0) {
    return (
      <p className="note">
        Asnjë rishkrim i sigurt nën këtë shteg. <Reasons result={result} />
      </p>
    );
  }

  return (
    <>
      <div className="patch-summary">
        <p>
          <b>{result.changes}</b> {word(result.changes, "ndryshim", "ndryshime")} në{" "}
          <b>{result.files}</b> {word(result.files, "skedar", "skedarë")}.{" "}
          <Reasons result={result} />
        </p>
        <div className="patch-actions">
          <button onClick={() => onCopy(result.diff)}>
            {copied ? "U kopjua" : "Kopjo patch-in"}
          </button>
          <button onClick={() => save(result.diff)}>Shkarko</button>
        </div>
      </div>

      <p className="caption">
        Ruaje si <code>fixes.patch</code> te rrënja e projektit dhe provoje pa e prekur asgjë:{" "}
        <code>git apply --check fixes.patch</code>.
        {!result.verified_with_javac &&
          " javac nuk u gjet, ndaj rishkrimi u verifikua vetëm për sintaksë."}
      </p>

      {result.dropped.length > 0 && (
        <ul className="dropped">
          {result.dropped.map((drop) => (
            <li key={drop.file_path}>
              <b>{drop.file_path}</b> u hoq nga patch-i: {drop.detail || drop.verdict}
            </li>
          ))}
        </ul>
      )}

      <UnifiedDiff text={result.diff} />
    </>
  );
}

/**
 * Hand the diff over as a file.
 *
 * The blob URL is created and revoked around the one click that uses it. Built
 * during render instead, it would leak a fresh URL on every re-render and hold
 * the whole patch in memory behind each one.
 */
function save(diff: string): void {
  const url = URL.createObjectURL(new Blob([diff], { type: "text/x-patch" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "fixes.patch";
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Singular or plural, because these counts are read as sentences.
 *
 * "1 ndryshime në 1 skedarë" is wrong Albanian, and this text is the part of the
 * tool a reader actually reads.
 */
function word(count: number, one: string, many: string): string {
  return count === 1 ? one : many;
}

/** Why the patch is shorter than the finding list, in the engine's own terms. */
function Reasons({ result }: { result: PatchResult }) {
  const parts: string[] = [];
  if (result.declined) {
    parts.push(
      `${result.declined} ${word(result.declined, "vend", "vende")} pa rishkrim të sigurt`,
    );
  }
  if (result.deferred) {
    parts.push(
      `${result.deferred} ${word(result.deferred, "i shtyrë", "të shtyra")} ` +
        "për ekzekutimin pasardhës",
    );
  }
  if (result.unreached) {
    parts.push(
      `${result.unreached} ${word(result.unreached, "skedar", "skedarë")} ` +
        `${word(result.unreached, "s'u arrit", "s'u arritën")} brenda kohës`,
    );
  }
  if (result.dropped.length) {
    const n = result.dropped.length;
    parts.push(`${n} ${word(n, "i hequr", "të hequr")} pas verifikimit`);
  }

  if (parts.length === 0) return null;
  return <span className="quiet">{parts.join("; ")}.</span>;
}

/**
 * The diff as the server wrote it, coloured by the first character of each line.
 *
 * Not re-parsed and not re-rendered from a model of it: what is shown has to be
 * the exact text the copy button puts on the clipboard, or the reader is
 * approving one thing and applying another.
 */
function UnifiedDiff({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <pre className="unified">
      {lines.map((line, index) => (
        <span key={index} className={`line ${classOf(line)}`}>
          {line}
        </span>
      ))}
    </pre>
  );
}

function classOf(line: string): string {
  if (line.startsWith("+++") || line.startsWith("---")) return "file";
  if (line.startsWith("@@")) return "hunk";
  if (line.startsWith("+")) return "added";
  if (line.startsWith("-")) return "removed";
  if (line.startsWith("\\")) return "gap";
  return "same";
}
