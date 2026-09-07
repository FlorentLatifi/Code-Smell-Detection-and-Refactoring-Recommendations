// A i mbledh erërat te vendi që i mban, dhe a i rendit sipas asaj që lexuesi do të hapte?
//
// Pritshmëritë nxirren me dorë nga tabelat e vogla që çdo test i shkruan vetë.

import { describe, expect, it } from "vitest";

import { bySeverity, byFile, byScore, groupBySite } from "./sites";
import type { Severity, Smell } from "./types";

function smell(overrides: Partial<Smell> = {}): Smell {
  return {
    smell_type: "LongMethod",
    severity: "major" as Severity,
    score: 1,
    file_path: "src/Ledger.java",
    class_name: "Ledger",
    method: "post(int)",
    start_line: 10,
    end_line: 60,
    package: "org.acme",
    scope: "method",
    automated: false,
    conditions: [],
    metrics: {},
    rationale: "",
    refactorings: [],
    ...overrides,
  } as Smell;
}

describe("grupimi sipas vendit", () => {
  it("mbledh disa erëra të një metode në një rresht", () => {
    const sites = groupBySite([
      smell({ smell_type: "LongMethod" }),
      smell({ smell_type: "BrainMethod" }),
      smell({ smell_type: "DeepNesting" }),
    ]);

    expect(sites).toHaveLength(1);
    expect(sites[0].smells.map((s) => s.smell_type).sort()).toEqual([
      "BrainMethod",
      "DeepNesting",
      "LongMethod",
    ]);
  });

  it("nuk i përzien dy mbingarkesa të së njëjtës metodë", () => {
    // Të njëjtin emër e ndajnë, por nisin në rreshta të ndryshëm — dhe rreshti
    // është ajo që të dyja anët e matën.
    const sites = groupBySite([
      smell({ method: "write(int)", start_line: 10 }),
      smell({ method: "write(double)", start_line: 40 }),
    ]);

    expect(sites).toHaveLength(2);
  });

  it("nuk e përzien klasën me metodën që nis në të njëjtin rresht", () => {
    // `class A { void m() {} }` — të dyja nisin te rreshti 1. Emri i metodës,
    // `null` për erën e klasës, është ajo që i ndan.
    const sites = groupBySite([
      smell({ method: null, smell_type: "LargeClass", start_line: 1 }),
      smell({ method: "m()", smell_type: "LongMethod", start_line: 1 }),
    ]);

    expect(sites).toHaveLength(2);
  });

  it("i ndan skedarët që ndajnë emrin e klasës", () => {
    const sites = groupBySite([
      smell({ file_path: "a/Ledger.java" }),
      smell({ file_path: "b/Ledger.java" }),
    ]);

    expect(sites).toHaveLength(2);
  });

  it("merr ashpërsinë më të rëndë dhe tepricën më të madhe të vendit", () => {
    const sites = groupBySite([
      smell({ smell_type: "LongMethod", severity: "minor", score: 1.2 }),
      smell({ smell_type: "BrainMethod", severity: "critical", score: 0.4 }),
    ]);

    expect(sites[0].worst).toBe("critical");
    expect(sites[0].score).toBe(1.2);
    expect(sites[0].smells[0].smell_type).toBe("BrainMethod");
  });

  it("e quan vendin të automatizuar nëse motori e rishkruan qoftë njërën erë", () => {
    const sites = groupBySite([
      smell({ smell_type: "LongMethod", automated: false }),
      smell({ smell_type: "BrainMethod", automated: true }),
    ]);

    expect(sites[0].automated).toBe(true);
  });

  it("nuk humb asnjë erë", () => {
    const input = [
      smell({ smell_type: "LongMethod" }),
      smell({ smell_type: "BrainMethod" }),
      smell({ file_path: "other/Other.java", class_name: "Other" }),
    ];

    const kept = groupBySite(input).flatMap((site) => site.smells);

    expect(kept).toHaveLength(input.length);
  });
});

describe("renditja e vendeve", () => {
  it("vë numrin e erërave para tepricës, pas ashpërsisë", () => {
    // Dy vende po aq të rënda: ai me dy erëra vjen i pari edhe pse teprica e tij
    // është më e vogël. Kjo është arsyeja pse grupimi u bë.
    const many = groupBySite([
      smell({ class_name: "Many", smell_type: "LongMethod", score: 0.2 }),
      smell({ class_name: "Many", smell_type: "BrainMethod", score: 0.2 }),
    ])[0];
    const one = groupBySite([smell({ class_name: "One", score: 9 })])[0];

    expect(bySeverity([one, many]).map((s) => s.class_name)).toEqual(["Many", "One"]);
  });

  it("ashpërsia mbetet kriteri i parë", () => {
    const heavy = groupBySite([smell({ class_name: "Heavy", severity: "critical", score: 0.1 })])[0];
    const light = groupBySite([
      smell({ class_name: "Light", severity: "minor", smell_type: "LongMethod" }),
      smell({ class_name: "Light", severity: "minor", smell_type: "BrainMethod" }),
    ])[0];

    expect(bySeverity([light, heavy]).map((s) => s.class_name)).toEqual(["Heavy", "Light"]);
  });

  it("sipas skedarit rendit me shteg e pastaj me rresht", () => {
    const sites = groupBySite([
      smell({ file_path: "b.java", start_line: 5 }),
      smell({ file_path: "a.java", start_line: 90 }),
      smell({ file_path: "a.java", start_line: 20 }),
    ]);

    expect(byFile(sites).map((s) => `${s.file_path}:${s.start_line}`)).toEqual([
      "a.java:20",
      "a.java:90",
      "b.java:5",
    ]);
  });

  it("sipas tepricës rendit vetëm me tepricën më të madhe të vendit", () => {
    const sites = groupBySite([
      smell({ class_name: "Small", score: 0.5 }),
      smell({ class_name: "Big", score: 4 }),
    ]);

    expect(byScore(sites).map((s) => s.class_name)).toEqual(["Big", "Small"]);
  });

  it("nuk e rendit listën origjinale në vend", () => {
    const sites = groupBySite([
      smell({ class_name: "B", severity: "minor" }),
      smell({ class_name: "A", severity: "critical" }),
    ]);
    const before = sites.map((s) => s.class_name);

    bySeverity(sites);

    expect(sites.map((s) => s.class_name)).toEqual(before);
  });
});
