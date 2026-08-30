interface Line {
  kind: "same" | "added" | "removed";
  text: string;
  before?: number;
  after?: number;
}

/**
 * A line diff, computed here rather than pulled in as a dependency.
 *
 * The engine's rewrites are local: one block replaced and one method appended.
 * A longest-common-subsequence table over the two files is a few lines of code
 * and is exact, which is what matters when the reader is deciding whether to
 * trust a change to their own source.
 */
function diff(before: string, after: string): Line[] {
  const left = before.split("\n");
  const right = after.split("\n");

  // lcs[i][j] = length of the longest common subsequence of left[i:] and right[j:]
  const lcs: number[][] = Array.from({ length: left.length + 1 }, () =>
    new Array<number>(right.length + 1).fill(0),
  );
  for (let i = left.length - 1; i >= 0; i--) {
    for (let j = right.length - 1; j >= 0; j--) {
      lcs[i][j] = left[i] === right[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }

  const lines: Line[] = [];
  let i = 0;
  let j = 0;
  while (i < left.length && j < right.length) {
    if (left[i] === right[j]) {
      lines.push({ kind: "same", text: left[i], before: i + 1, after: j + 1 });
      i++;
      j++;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      lines.push({ kind: "removed", text: left[i], before: i + 1 });
      i++;
    } else {
      lines.push({ kind: "added", text: right[j], after: j + 1 });
      j++;
    }
  }
  while (i < left.length) lines.push({ kind: "removed", text: left[i], before: ++i });
  while (j < right.length) lines.push({ kind: "added", text: right[j], after: ++j });

  return lines;
}

/** Hide long stretches of unchanged code, keeping a few lines for context. */
function withContext(lines: Line[], context = 3): (Line | "gap")[] {
  const keep = new Set<number>();
  lines.forEach((line, index) => {
    if (line.kind === "same") return;
    for (let k = index - context; k <= index + context; k++) {
      if (k >= 0 && k < lines.length) keep.add(k);
    }
  });

  const out: (Line | "gap")[] = [];
  let skipping = false;
  lines.forEach((line, index) => {
    if (keep.has(index)) {
      out.push(line);
      skipping = false;
    } else if (!skipping) {
      out.push("gap");
      skipping = true;
    }
  });
  return out;
}

export function Diff({ before, after }: { before: string; after: string }) {
  const rows = withContext(diff(before, after));
  const added = rows.filter((r) => r !== "gap" && r.kind === "added").length;
  const removed = rows.filter((r) => r !== "gap" && r.kind === "removed").length;

  return (
    <div className="diff">
      <h3>
        Ndryshimi i propozuar <span className="plus">+{added}</span>{" "}
        <span className="minus">−{removed}</span>
      </h3>
      <p className="note">
        Kjo është vetëm pamje paraprake. Asnjë skedar nuk është prekur.
      </p>
      <pre>
        {rows.map((row, index) =>
          row === "gap" ? (
            <span key={index} className="gap">
              ⋯
            </span>
          ) : (
            <span key={index} className={`line ${row.kind}`}>
              <span className="gutter">{row.before ?? ""}</span>
              <span className="gutter">{row.after ?? ""}</span>
              <span className="mark">
                {row.kind === "added" ? "+" : row.kind === "removed" ? "−" : " "}
              </span>
              {row.text}
            </span>
          ),
        )}
      </pre>
    </div>
  );
}
