// Tests for lining Approach B's verdicts up against Approach A's findings.
//
// This join is where a real defect lived: keyed on the method's bare name, two
// overloads collapsed onto one key and the second verdict silently replaced the
// first. The tests below are written around that case rather than around the
// happy path, because the happy path never showed the bug.

import { describe, expect, it } from "vitest";

import { agreementOn, indexModel } from "./model";
import type { ModelBlock, Prediction, Smell } from "./types";

function prediction(over: Partial<Prediction> = {}): Prediction {
  return {
    smell: "long method",
    file_path: "Ledger.java",
    class_name: "Ledger",
    method: "writeRange",
    start_line: 10,
    end_line: 40,
    probability: 0.9,
    contributions: [],
    ...over,
  };
}

function smell(over: Partial<Smell> = {}): Smell {
  return {
    smell_type: "LongMethod",
    scope: "method",
    class_name: "Ledger",
    method: "writeRange(int)",
    package: "com.acme",
    file_path: "Ledger.java",
    start_line: 10,
    end_line: 40,
    severity: "major",
    score: 1.2,
    rationale: "",
    conditions: [],
    refactorings: [],
    metrics: {},
    automated: true,
    ...over,
  };
}

function block(predictions: Prediction[], rule_equivalent = ["LongMethod"]): ModelBlock {
  return {
    available: true,
    smells: [
      {
        smell: "long method",
        rule_equivalent,
        considered: 10,
        incomplete: 0,
        flagged: predictions.length,
        predictions,
      },
    ],
  };
}

describe("indexModel", () => {
  it("returns nothing when the model was not available", () => {
    const reason: ModelBlock = { available: false, reason: "no trained model" };

    expect(indexModel(reason)).toBeNull();
    expect(indexModel(undefined)).toBeNull();
  });

  it("carries the counts the interface reports beside the findings", () => {
    const index = indexModel({
      available: true,
      smells: [
        {
          smell: "long method",
          rule_equivalent: ["LongMethod"],
          considered: 30,
          incomplete: 7,
          flagged: 1,
          predictions: [prediction()],
        },
      ],
    });

    expect(index).not.toBeNull();
    expect(index?.incomplete).toBe(7);
    expect(index?.flagged).toBe(1);
  });

  it("files one verdict under every detector that asks the same question", () => {
    // Blob maps to GodClass in the published strategy; a model that flags the
    // class has answered for each detector the mapping names.
    const index = indexModel(
      block([prediction({ smell: "blob", method: null })], ["GodClass", "LargeClass"]),
    );

    const asGod = agreementOn(index, smell({ smell_type: "GodClass", method: null }));
    const asLarge = agreementOn(index, smell({ smell_type: "LargeClass", method: null }));

    expect(asGod).not.toBeNull();
    expect(asLarge).not.toBeNull();
    expect(asGod).toBe(asLarge);
  });
});

describe("agreementOn", () => {
  it("matches a finding to the verdict on the same entity", () => {
    const index = indexModel(block([prediction()]));

    expect(agreementOn(index, smell())?.probability).toBe(0.9);
  });

  it("keeps two overloads apart", () => {
    // The whole reason the key is the starting line. Both methods are called
    // writeRange; only the line tells them apart, and the rules report the
    // signature while the model reports the bare name, so the name cannot.
    const index = indexModel(
      block([
        prediction({ start_line: 10, probability: 0.7 }),
        prediction({ start_line: 50, probability: 0.95 }),
      ]),
    );

    const first = agreementOn(index, smell({ method: "writeRange(int)", start_line: 10 }));
    const second = agreementOn(index, smell({ method: "writeRange(double)", start_line: 50 }));

    expect(first?.probability).toBe(0.7);
    expect(second?.probability).toBe(0.95);
  });

  it("does not match a finding the model did not flag", () => {
    // Absence is a disagreement, not a gap: the model was asked about this file
    // and said nothing about the entity on line 99.
    const index = indexModel(block([prediction({ start_line: 10 })]));

    expect(agreementOn(index, smell({ start_line: 99 }))).toBeNull();
  });

  it("does not match across files that share a class and a line", () => {
    const index = indexModel(block([prediction({ file_path: "a/Ledger.java" })]));

    expect(agreementOn(index, smell({ file_path: "b/Ledger.java" }))).toBeNull();
  });

  it("does not match a different smell on the same entity", () => {
    // The model flagged it as a Long Method; that says nothing about whether it
    // is also a Deep Nesting, and the badge must not claim it does.
    const index = indexModel(block([prediction()]));

    expect(agreementOn(index, smell({ smell_type: "DeepNesting" }))).toBeNull();
  });

  it("tells a class apart from a method that begins on the same line", () => {
    // `class A { void m() {} }` puts both on line 1. The smell type is what
    // separates them, since no smell type belongs to both levels.
    const index = indexModel(
      block([prediction({ smell: "blob", method: null, start_line: 1 })], ["GodClass"]),
    );

    expect(agreementOn(index, smell({ smell_type: "GodClass", method: null, start_line: 1 })))
      .not.toBeNull();
    expect(agreementOn(index, smell({ smell_type: "LongMethod", start_line: 1 }))).toBeNull();
  });

  it("answers nothing when there is no index at all", () => {
    expect(agreementOn(null, smell())).toBeNull();
  });
});
