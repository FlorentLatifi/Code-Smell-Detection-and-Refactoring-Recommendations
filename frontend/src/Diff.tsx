// `diff` and `withContext` are exported for their tests rather than for other
// modules: this is the one piece of algorithm the frontend implements itself
// instead of importing, so it is the one piece that has to be checked against
// hand-worked expectations rather than against its own past output.
export interface Line {
  kind: "same" | "added" | "removed";
  text: string;
  before?: number;
  after?: number;
}

/**
 * Sa qeliza tabele LCS-je pranohen para se të hiqet dorë prej saj.
 *
 * Kostoja e tabelës është `n × m`, dhe `/refactor/preview` e kthen **tërë**
 * skedarin, jo vetëm pjesën e prekur. E matur mbi këtë funksion: 500 rreshta
 * 16 ms, 1 500 rreshta 84 ms, 3 000 rreshta 356 ms. Korpusi i këtij projekti mban
 * një skedar prej 15 292 rreshtash, i cili do të kërkonte rreth nëntë sekonda dhe
 * rreth 1.8 GB vargje: skeda ngrin para se të mbarojë.
 *
 * Dy milionë qeliza janë rreth 16 MB dhe rreth 200 ms — kufiri ku një pamje
 * paraprake pushon së qeni e menjëhershme.
 */
const MAX_CELLS = 2_000_000;

/**
 * A line diff, computed here rather than pulled in as a dependency.
 *
 * The engine's rewrites are local: one block replaced and one method appended.
 * A longest-common-subsequence table over the two files is a few lines of code
 * and is exact, which is what matters when the reader is deciding whether to
 * trust a change to their own source.
 */
export function diff(before: string, after: string): Line[] {
  return align(before.split("\n"), after.split("\n"));
}

/**
 * Prit prefiksin dhe prapashtesën e përbashkët para se të llogaritet gjë.
 *
 * Rishkrimet e motorit janë lokale, ndaj pothuajse tërë skedari është i njëjtë në
 * të dyja anët. Ai krahasohet me një kalim të vetëm dhe nuk hyn kurrë te tabela;
 * vetëm ndryshimi që mbetet në mes e paguan koston kuadratike. Numrat e rreshtave
 * mbeten ata të skedarit të plotë, sepse lexuesi i krahason me burimin e vet.
 */
function align(left: string[], right: string[]): Line[] {
  let head = 0;
  while (head < left.length && head < right.length && left[head] === right[head]) head++;

  let tail = 0;
  while (
    tail < left.length - head &&
    tail < right.length - head &&
    left[left.length - 1 - tail] === right[right.length - 1 - tail]
  ) {
    tail++;
  }

  const lines: Line[] = [];
  for (let k = 0; k < head; k++) {
    lines.push({ kind: "same", text: left[k], before: k + 1, after: k + 1 });
  }

  lines.push(...middle(left.slice(head, left.length - tail), right.slice(head, right.length - tail), head));

  for (let k = 0; k < tail; k++) {
    const i = left.length - tail + k;
    const j = right.length - tail + k;
    lines.push({ kind: "same", text: left[i], before: i + 1, after: j + 1 });
  }
  return lines;
}

/**
 * Ndryshimi i vërtetë, ose një ndarje e sinqertë kur ai është tepër i madh.
 *
 * Kur edhe pas prerjes tabela do të dilte mbi kufirin — një skedar i riformatuar
 * tërësisht, për shembull — nuk ka LCS që e shpëton: kthehen blloku i hequr dhe
 * blloku i shtuar. Kjo është më pak e hollë se një diff i vërtetë dhe e saktë; një
 * skedë e ngrirë nuk është asnjëra nga të dyja.
 */
function middle(left: string[], right: string[], base: number): Line[] {
  if (left.length === 0 && right.length === 0) return [];

  if (left.length * right.length > MAX_CELLS) {
    return [
      ...left.map((text, k) => ({ kind: "removed" as const, text, before: base + k + 1 })),
      ...right.map((text, k) => ({ kind: "added" as const, text, after: base + k + 1 })),
    ];
  }

  // lcs[i][j] = length of the longest common subsequence of left[i:] and right[j:]
  const lcs: number[][] = Array.from({ length: left.length + 1 }, () =>
    new Array<number>(right.length + 1).fill(0),
  );
  for (let i = left.length - 1; i >= 0; i--) {
    for (let j = right.length - 1; j >= 0; j--) {
      lcs[i][j] =
        left[i] === right[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }

  const lines: Line[] = [];
  let i = 0;
  let j = 0;
  while (i < left.length && j < right.length) {
    if (left[i] === right[j]) {
      lines.push({ kind: "same", text: left[i], before: base + i + 1, after: base + j + 1 });
      i++;
      j++;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      lines.push({ kind: "removed", text: left[i], before: base + i + 1 });
      i++;
    } else {
      lines.push({ kind: "added", text: right[j], after: base + j + 1 });
      j++;
    }
  }
  while (i < left.length) {
    lines.push({ kind: "removed", text: left[i], before: base + i + 1 });
    i++;
  }
  while (j < right.length) {
    lines.push({ kind: "added", text: right[j], after: base + j + 1 });
    j++;
  }

  return lines;
}

/** Hide long stretches of unchanged code, keeping a few lines for context. */
export function withContext(lines: Line[], context = 3): (Line | "gap")[] {
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
