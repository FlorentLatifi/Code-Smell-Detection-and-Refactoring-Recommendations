// A i mbledh erërat te vendi që i mban, dhe a i rendit sipas asaj që lexuesi do të hapte?
//
// Pritshmëritë nxirren me dorë nga tabelat e vogla që çdo test i shkruan vetë.

import { describe, expect, it } from "vitest";

import {
  automatable,
  bySeverity,
  byFile,
  byScore,
  countByWorst,
  groupBySite,
  hotspots,
} from "./sites";
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

describe("numërimi i vendeve sipas ashpërsisë", () => {
  it("e numëron çdo vend një herë, sipas erës së tij më të rëndë", () => {
    // Katër erëra, por dy vende: njëri critical (sepse mban një critical), tjetri minor.
    const sites = groupBySite([
      smell({ class_name: "Heavy", smell_type: "LongMethod", severity: "minor" }),
      smell({ class_name: "Heavy", smell_type: "BrainMethod", severity: "critical" }),
      smell({ class_name: "Light", smell_type: "LongMethod", severity: "minor" }),
      smell({ class_name: "Light", smell_type: "BrainMethod", severity: "minor" }),
    ]);

    expect(countByWorst(sites)).toEqual({ critical: 1, major: 0, minor: 1 });
  });

  it("shuma e tij barazon numrin e vendeve, jo të erërave", () => {
    const sites = groupBySite([
      smell({ smell_type: "LongMethod" }),
      smell({ smell_type: "BrainMethod" }),
      smell({ class_name: "Other", smell_type: "LongMethod" }),
    ]);
    const tally = countByWorst(sites);

    expect(tally.critical + tally.major + tally.minor).toBe(sites.length);
    expect(sites.length).toBe(2);
  });
});

describe("ku përqendrohet puna", () => {
  it("i rendit skedarët sipas numrit të vendeve", () => {
    const sites = groupBySite([
      smell({ file_path: "a.java", start_line: 1 }),
      smell({ file_path: "a.java", start_line: 20 }),
      smell({ file_path: "b.java", start_line: 1 }),
    ]);

    expect(hotspots(sites).map((h) => [h.file, h.sites])).toEqual([
      ["a.java", 2],
      ["b.java", 1],
    ]);
  });

  it("numëron edhe erërat, jo vetëm vendet", () => {
    const sites = groupBySite([
      smell({ file_path: "a.java", smell_type: "LongMethod" }),
      smell({ file_path: "a.java", smell_type: "BrainMethod" }),
    ]);

    expect(hotspots(sites)[0]).toEqual({ file: "a.java", sites: 1, smells: 2 });
  });

  it("kthen vetëm aq sa i kërkohen", () => {
    const sites = groupBySite(
      ["a", "b", "c", "d"].map((name) => smell({ file_path: `${name}.java` })),
    );

    expect(hotspots(sites, 2)).toHaveLength(2);
  });

  it("i ndan barazimet me emrin, që radha të mos varet nga hyrja", () => {
    const one = groupBySite([smell({ file_path: "z.java" }), smell({ file_path: "a.java" })]);
    const other = groupBySite([smell({ file_path: "a.java" }), smell({ file_path: "z.java" })]);

    expect(hotspots(one).map((h) => h.file)).toEqual(hotspots(other).map((h) => h.file));
  });
});

describe("sa mund ta rishkruajë motori", () => {
  it("numëron vendet me të paktën një rishkrim të automatizuar", () => {
    const sites = groupBySite([
      smell({ class_name: "A", smell_type: "LongMethod", automated: false }),
      smell({ class_name: "A", smell_type: "BrainMethod", automated: true }),
      smell({ class_name: "B", automated: false }),
    ]);

    expect(automatable(sites)).toBe(1);
  });

  it("është zero kur motori nuk prek asgjë", () => {
    expect(automatable(groupBySite([smell({ automated: false })]))).toBe(0);
  });
});
