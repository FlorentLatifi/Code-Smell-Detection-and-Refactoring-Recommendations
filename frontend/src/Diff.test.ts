// Tests for the line diff the interface computes itself.
//
// The module explains why it is written here rather than imported: the engine's
// rewrites are local, and a longest-common-subsequence table is exact where a
// heuristic is not. Exact is a property worth checking, so every expectation
// below is worked out by hand from the two inputs, never taken from a run.

import { describe, expect, it } from "vitest";

import { diff, withContext } from "./Diff";
import type { Line } from "./Diff";

/** A compact reading of the result: one letter per line, in order. */
function shape(lines: Line[]): string {
  return lines.map((l) => ({ same: "=", added: "+", removed: "-" })[l.kind]).join("");
}

describe("diff", () => {
  it("reports two identical files as unchanged", () => {
    const text = "a\nb\nc";

    expect(shape(diff(text, text))).toBe("===");
  });

  it("numbers each side independently", () => {
    // "a b c" -> "a c": b is removed, so after that point the two files are on
    // different line numbers, and each side must keep its own.
    const lines = diff("a\nb\nc", "a\nc");

    expect(shape(lines)).toBe("=-=");
    expect(lines[0]).toMatchObject({ before: 1, after: 1 });
    expect(lines[1]).toMatchObject({ kind: "removed", before: 2 });
    // A removed line exists on the left only, so it carries no right-hand
    // number at all -- the gutter renders empty rather than repeating one.
    expect(lines[1].after).toBeUndefined();
    expect(lines[2]).toMatchObject({ before: 3, after: 2 });
  });

  it("finds the insertion rather than rewriting the tail", () => {
    // The point of the LCS: "a c" -> "a b c" is one added line, not one
    // changed line followed by one added one.
    const lines = diff("a\nc", "a\nb\nc");

    expect(shape(lines)).toBe("=+=");
    expect(lines[1]).toMatchObject({ kind: "added", text: "b", after: 2 });
  });

  it("keeps the common lines when a block is replaced", () => {
    // Only the middle differs, and "a" and "d" are the common subsequence.
    const lines = diff("a\nb\nd", "a\nc\nd");

    expect(shape(lines)).toBe("=-+=");
    expect(lines.map((l) => l.text)).toEqual(["a", "b", "c", "d"]);
  });

  it("handles an empty side without losing the other", () => {
    expect(shape(diff("", "a\nb"))).toBe("-++");
    expect(shape(diff("a\nb", ""))).toBe("--+");
  });
});

describe("withContext", () => {
  it("leaves a small file alone", () => {
    // Every line is within three of a change, so nothing is hidden and no gap
    // marker appears.
    const rows = withContext(diff("a\nb\nc", "a\nx\nc"));

    expect(rows.includes("gap")).toBe(false);
    expect(rows).toHaveLength(4);
  });

  it("hides a long unchanged stretch behind one marker", () => {
    // Twelve identical lines with the first changed: lines 2..4 stay as
    // context, and the remaining eight collapse into a single gap.
    const before = ["x", ...Array.from({ length: 11 }, (_, i) => `same${i}`)].join("\n");
    const after = ["y", ...Array.from({ length: 11 }, (_, i) => `same${i}`)].join("\n");

    const rows = withContext(diff(before, after));
    const gaps = rows.filter((r) => r === "gap");
    const kept = rows.filter((r): r is Line => r !== "gap");

    expect(gaps).toHaveLength(1);
    // one removed, one added, then three lines of trailing context
    expect(kept).toHaveLength(5);
    expect(shape(kept)).toBe("-+===");
  });

  it("keeps context on both sides of a change", () => {
    const before = [...Array.from({ length: 10 }, (_, i) => `l${i}`)].join("\n");
    const after = before.split("\n").map((l, i) => (i === 5 ? "changed" : l)).join("\n");

    const kept = withContext(diff(before, after)).filter((r): r is Line => r !== "gap");

    // Three before the change, the removed and added pair, three after.
    expect(shape(kept)).toBe("===-+===");
  });

  it("reports an unchanged file as a single gap", () => {
    const rows = withContext(diff("a\nb\nc", "a\nb\nc"));

    expect(rows).toEqual(["gap"]);
  });
});

// Prerja e prefiksit dhe e prapashtesës u shtua sepse `/refactor/preview` e kthen
// tërë skedarin, dhe tabela LCS mbi të është kuadratike. Testet më poshtë e
// mbajnë atë prerje të ndershme: rezultati duhet të mbetet i njëjti, dhe numrat e
// rreshtave duhet të mbeten ata të skedarit të plotë e jo të segmentit.
describe("prerja para tabelës", () => {
  it("jep të njëjtin rezultat si diff-i mbi tërë skedarin", () => {
    // Njëqind rreshta të njëjtë, një i ndryshuar në mes, njëqind të njëjtë.
    const head = Array.from({ length: 100 }, (_, i) => `head${i}`);
    const tail = Array.from({ length: 100 }, (_, i) => `tail${i}`);
    const before = [...head, "old", ...tail].join("\n");
    const after = [...head, "new", ...tail].join("\n");

    const lines = diff(before, after);
    const changed = lines.filter((l) => l.kind !== "same");

    expect(changed.map((l) => l.text)).toEqual(["old", "new"]);
    expect(lines.filter((l) => l.kind === "same")).toHaveLength(200);
  });

  it("mban numrat e rreshtave të skedarit, jo të segmentit", () => {
    // Rreshti i ndryshuar është i 101-ti në të dyja anët. Po të numëroheshin
    // brenda segmentit të prerë, ai do të dilte 1 — dhe lexuesi do ta kërkonte
    // te rreshti i gabuar i burimit të vet.
    const head = Array.from({ length: 100 }, (_, i) => `head${i}`);
    const before = [...head, "old", "z"].join("\n");
    const after = [...head, "new", "z"].join("\n");

    const lines = diff(before, after);
    const removed = lines.find((l) => l.kind === "removed");
    const added = lines.find((l) => l.kind === "added");

    expect(removed?.before).toBe(101);
    expect(added?.after).toBe(101);
  });

  it("numëron saktë kur njëra anë shtohet vetëm në fund", () => {
    // Extract Method e bën pikërisht këtë: blloku zëvendësohet dhe metoda e re
    // shtohet në fund, ndaj prapashtesa e përbashkët është bosh.
    const lines = diff("a\nb", "a\nb\nc\nd");

    expect(shape(lines)).toBe("==++");
    expect(lines[2].after).toBe(3);
    expect(lines[3].after).toBe(4);
  });

  it("nuk ngec kur skedari është i madh dhe ndryshimi i vogël", () => {
    // Pa prerje, kjo do të ishte një tabelë me 36 milionë qeliza. Me prerje, ajo
    // që hyn te tabela është një rresht kundrejt një rreshti.
    const filler = Array.from({ length: 6000 }, (_, i) => `line ${i}`);
    const before = [...filler, "old"].join("\n");
    const after = [...filler, "new"].join("\n");

    const started = Date.now();
    const lines = diff(before, after);

    expect(Date.now() - started).toBeLessThan(500);
    expect(lines.filter((l) => l.kind !== "same")).toHaveLength(2);
  });

  it("kthen bllok-hequr dhe bllok-shtuar kur edhe pas prerjes është tepër i madh", () => {
    // Asnjë rresht i përbashkët, ndaj prerja nuk heq gjë dhe tabela do të kalonte
    // kufirin. Dalja mbetet e saktë dhe e plotë; thjesht më pak e hollë.
    const before = Array.from({ length: 1600 }, (_, i) => `L${i}`).join("\n");
    const after = Array.from({ length: 1600 }, (_, i) => `R${i}`).join("\n");

    const lines = diff(before, after);

    expect(lines.filter((l) => l.kind === "removed")).toHaveLength(1600);
    expect(lines.filter((l) => l.kind === "added")).toHaveLength(1600);
    expect(lines.filter((l) => l.kind === "same")).toHaveLength(0);
  });
});
