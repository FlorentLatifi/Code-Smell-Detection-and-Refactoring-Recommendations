// Krahasimi i erërave para dhe pas një shkrimi (VD-123).
//
// Pritjet dalin me dorë nga fikstuarat: çdo test thotë cilat erëra janë të
// njëjtat, cilat mungojnë pas, dhe cilat nuk ishin para.

import { describe, expect, it } from "vitest";

import type { Smell } from "./types";
import { writeEffect } from "./writeEffect";

function smell(method: string | null, smellType: string, startLine = 10, className = "Ledger"): Smell {
  return {
    smell_type: smellType,
    scope: method ? "method" : "class",
    class_name: className,
    method,
    package: "com.acme",
    file_path: "com/acme/Ledger.java",
    start_line: startLine,
    end_line: startLine + 40,
    severity: "minor",
    score: 1.2,
    rationale: "",
    conditions: [],
    refactorings: [],
    metrics: {},
    automated: true,
  };
}

describe("erërat pas shkrimit", () => {
  it("e njeh të njëjtën erë edhe kur rishkrimi i lëvizi rreshtat", () => {
    // Guard Clauses shton rreshta sipër, ndaj metoda nis më poshtë.
    const effect = writeEffect([smell("post(int)", "LongMethod", 10)], [smell("post(int)", "LongMethod", 14)]);

    expect(effect).toEqual({ removed: [], introduced: [], kept: 1 });
  });

  it("e njeh metodën edhe kur Introduce Parameter Object ia ndryshoi nënshkrimin", () => {
    const before = [smell("create(String, String, int)", "FeatureEnvy")];
    const after = [smell("create(CreateParams)", "FeatureEnvy")];

    expect(writeEffect(before, after).kept).toBe(1);
  });

  it("i numëron veç të hequrat dhe të rejat", () => {
    // Si te projekti i testimit: dy erëra u hoqën, një lindi te konstruktori i ri.
    const before = [
      smell("post(int)", "LongMethod"),
      smell("flag(Student)", "DeepNesting"),
      smell("create(String, String, int)", "LongParameterList"),
    ];
    const after = [
      smell("post(int)", "LongMethod", 20),
      smell("CreateParams(String, String, int)", "LongParameterList", 30, "CreateParams"),
    ];

    expect(writeEffect(before, after)).toEqual({
      removed: [
        { file: "com/acme/Ledger.java", entity: "Ledger.create", smell: "LongParameterList" },
        { file: "com/acme/Ledger.java", entity: "Ledger.flag", smell: "DeepNesting" },
      ],
      introduced: [
        {
          file: "com/acme/Ledger.java",
          entity: "CreateParams.CreateParams",
          smell: "LongParameterList",
        },
      ],
      kept: 1,
    });
  });

  it("i numëron mbingarkesat si shumësi", () => {
    // Dy metoda `post` me të njëjtën erë para, një pas: njëra u hoq.
    const before = [smell("post(int)", "DeepNesting", 10), smell("post(long)", "DeepNesting", 60)];
    const after = [smell("post(long)", "DeepNesting", 55)];

    const effect = writeEffect(before, after);

    expect(effect.kept).toBe(1);
    expect(effect.removed).toHaveLength(1);
    expect(effect.introduced).toHaveLength(0);
  });

  it("nuk ngatërron erë klase me erë metode në të njëjtën klasë", () => {
    const effect = writeEffect([smell(null, "GodClass")], [smell(null, "LargeClass")]);

    expect(effect.removed).toEqual([{ file: "com/acme/Ledger.java", entity: "Ledger", smell: "GodClass" }]);
    expect(effect.introduced).toEqual([
      { file: "com/acme/Ledger.java", entity: "Ledger", smell: "LargeClass" },
    ]);
  });
});
