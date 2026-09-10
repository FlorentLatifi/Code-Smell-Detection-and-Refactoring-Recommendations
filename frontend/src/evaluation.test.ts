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
  PMD_ROW_SQ,
  REFUSAL_SQ,
  SMELL_SQ,
  SOURCES,
  VERDICT_SQ,
  blockingFor,
  ml,
  pmd,
  refactoring,
  rules,
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
    const expected = [...new Set(SOURCES.map((s) => s.environment.commit.slice(0, 10)))].sort();

    expect(COMMITS).toEqual(expected);
    expect(COMMITS.length).toBeGreaterThan(0);
  });

  it("nuk pretendon një commit të vetëm kur skedarët mbajnë disa", () => {
    // Fusnota shtypte commit-in e `rules_evaluation.json` sikur t'i kishte
    // prodhuar të gjitha shifrat. Nëse skedarët mbajnë më shumë se një, lista
    // duhet t'i mbajë të gjitha — ndryshe defekti është kthyer.
    const distinct = new Set(SOURCES.map((s) => s.environment.commit));

    expect(COMMITS.length).toBe(distinct.size);
  });

  it("rritet bashkë me panelin", () => {
    // Kur paneli filloi të shfaqte krahasimin me PMD-në dhe llogarinë e
    // klauzolave, prejardhja e tyre duhej të hynte te fusnota. Ky test e mban
    // atë lidhje: çdo burim i ri që paneli lexon duhet të jetë te SOURCES.
    const commits = new Set(COMMITS);

    for (const source of [pmd, rules, ml, refactoring]) {
      expect(commits.has(source.environment.commit.slice(0, 10))).toBe(true);
    }
  });
});

describe("krahasimi me mjetin e jashtëm", () => {
  it("çdo rresht i matur ka emër shqip", () => {
    // I njëjti defekt si te verdiktet: pa etiketë, tabela do të shfaqte çelësin
    // e papërkthyer `blob/with_size` mes emrash shqip, dhe do të dukej e saktë.
    const measured = Object.keys(pmd.by_smell);

    expect(measured.length).toBeGreaterThan(0);
    expect(measured.filter((key) => !(key in PMD_ROW_SQ))).toEqual([]);
  });

  it("çdo ndryshim i raportuar e ka intervalin e vet", () => {
    // Dy MCC krah njëri-tjetrit pa interval ftojnë të lexohet fitore aty ku ka
    // lëkundje. Nëse njëra anë mungon, mungon edhe intervali dhe anasjelltas.
    for (const row of Object.values(pmd.by_smell)) {
      expect(row.ours === undefined).toBe(row.difference === undefined);
    }
  });
});

describe("pse nuk ndezin strategjitë", () => {
  it("çdo erë me llogari klauzolash është erë që vlerësohet", () => {
    for (const smell of Object.keys(pmd.by_smell)) {
      const name = smell.split("/")[0];
      if (blockingFor(name)) expect(rules.per_smell[name]).toBeDefined();
    }
  });

  it("rastet e bllokuara nga një klauzolë nuk i kalojnë të gjitha", () => {
    // `missed - blocked_by_one_clause` shkon te teksti si numri i atyre që
    // dështuan në më shumë se një klauzolë; nëse dilte negativ, fjalia do të
    // thoshte diçka të pamundur.
    for (const name of ["blob", "feature envy"]) {
      const blocking = blockingFor(name);
      expect(blocking).not.toBeNull();
      expect(blocking!.blocked_by_one_clause).toBeLessThanOrEqual(blocking!.missed);
    }
  });

  it("çdo bllokues i vetëm ka edhe distancën e vet", () => {
    for (const name of ["blob", "feature envy"]) {
      const blocking = blockingFor(name)!;
      for (const metric of Object.keys(blocking.sole_blocker)) {
        expect(blocking.median_shortfall[metric]).toBeGreaterThan(0);
      }
    }
  });
});
