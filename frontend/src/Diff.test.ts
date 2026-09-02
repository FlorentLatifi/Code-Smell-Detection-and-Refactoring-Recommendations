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
