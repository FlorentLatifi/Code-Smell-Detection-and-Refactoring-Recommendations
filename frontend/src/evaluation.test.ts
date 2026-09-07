// A çdo gjë që të dhënat mund të shfaqin ka një etiketë shqip?
//
// Fjalorët këtu janë kopje me dorë e çelësave që prodhon backend-i, dhe të dyja
// anët ndryshojnë veç e veç. Kur ndahen, pamja nuk prishet — `Distribution` bie
// te vetë çelësi — ndaj defekti nuk duket si defekt: thjesht një identifikues
// anglisht mes etiketash shqip, në panelin që tregohet në mbrojtje. Pikërisht
// kështu verdikti `parses` qëndroi i papërkthyer.
//
// Kontrollohet vetëm një drejtim. Një etiketë për diçka që korpusi nuk e nxori
// është e saktë dhe e pritshme: motori mund ta prodhojë atë verdikt ose atë
// arsye refuzimi, thjesht nuk e prodhoi këtu.

import { describe, expect, it } from "vitest";

import {
  COMMITS,
  MODEL_SQ,
  REFUSAL_SQ,
  SMELL_SQ,
  VERDICT_SQ,
  ml,
  dataset,
  refactoring,
  rules,
  sweep,
} from "./evaluation";

describe("etiketat mbulojnë të dhënat", () => {
  it("çdo verdikt i matur ka përkthim", () => {
    const measured = Object.keys(refactoring.verdicts);
    expect(measured.length).toBeGreaterThan(0);
    expect(measured.filter((key) => !(key in VERDICT_SQ))).toEqual([]);
  });

  it("çdo arsye refuzimi e matur ka përkthim", () => {
    const measured = Object.keys(refactoring.refused_by_reason);
    expect(measured.length).toBeGreaterThan(0);
    expect(measured.filter((key) => !(key in REFUSAL_SQ))).toEqual([]);
  });

  it("çdo erë e vlerësuar ka emër", () => {
    const measured = Object.keys(rules.per_smell);
    expect(measured.length).toBeGreaterThan(0);
    expect(measured.filter((key) => !(key in SMELL_SQ))).toEqual([]);
  });

  it("çdo model i vlerësuar ka emër", () => {
    const measured = new Set<string>();
    for (const smell of Object.values(ml.per_smell)) {
      for (const name of Object.keys(smell.models)) measured.add(name);
    }
    expect(measured.size).toBeGreaterThan(0);
    expect([...measured].filter((key) => !(key in MODEL_SQ))).toEqual([]);
  });
});

describe("prejardhja", () => {
  it("mbledh çdo commit që qëndron pas panelit, pa përsëritje", () => {
    const sources = [rules, ml, refactoring, dataset, sweep];
    const expected = [...new Set(sources.map((s) => s.environment.commit.slice(0, 10)))].sort();

    expect(COMMITS).toEqual(expected);
    expect(COMMITS.length).toBeGreaterThan(0);
  });

  it("nuk pretendon një commit të vetëm kur skedarët mbajnë disa", () => {
    // Fusnota shtypte commit-in e `rules_evaluation.json` sikur t'i kishte
    // prodhuar të gjitha shifrat. Nëse skedarët mbajnë më shumë se një, lista
    // duhet t'i mbajë të gjitha — ndryshe defekti është kthyer.
    const distinct = new Set(
      [rules, ml, refactoring, dataset, sweep].map((s) => s.environment.commit),
    );
    expect(COMMITS.length).toBe(distinct.size);
  });
});
