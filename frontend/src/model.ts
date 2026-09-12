// Lining Approach B's verdicts up against Approach A's findings.
//
// The two arrive separately: `/analyze` returns the rules' smells as a flat list
// and the model's flags grouped per smell. Joining them here rather than in each
// component keeps one definition of "the same entity", which is the only thing
// that makes an agreement between the approaches mean anything.
//
// The mapping between the two vocabularies is **not** written here. Reviewers
// labelled `blob` where the strategy is called `GodClass`, and that
// correspondence is a backend contract — every reported comparison of A against
// B was computed through it — so the API sends it with each report as
// `rule_equivalent`. A second copy in this file could disagree with the first.

import type { ModelBlock, Prediction, Smell } from "./types";

/**
 * What identifies one entity to both approaches: where it starts.
 *
 * Deliberately not the method name. The rules report a method by signature
 * (`writeRange(int, int)`) and the model by bare name, and stripping the
 * signature to match them discards exactly what tells two overloads apart — so a
 * class holding `writeRange(int)` and `writeRange(double)` would file both
 * verdicts under one key and show whichever was written last. The starting line
 * is what both sides measured the entity at, and it is unambiguous.
 *
 * The smell type is appended by the callers, which also settles the one case a
 * line alone would not: in `class A { void m() {} }` the class and the method
 * begin on the same line, and no smell type belongs to both.
 */
function keyOf(file: string, className: string, startLine: number, smellType: string): string {
  // Serialised rather than concatenated with a separator: a path may legally
  // contain whatever character was chosen as the separator, and JSON escapes its
  // own delimiters, so two different entities cannot produce one key.
  return JSON.stringify([file, className, startLine, smellType]);
}

/** Every model verdict, reachable by the entity and the detector it corresponds to. */
export interface ModelIndex {
  /** Keyed by file, class, starting line and detector smell type. */
  flags: Map<string, Prediction>;
  /** Entities the model was never asked about, for honest counting. */
  incomplete: number;
  flagged: number;
}

export function indexModel(block: ModelBlock | undefined): ModelIndex | null {
  if (!block?.available) return null;

  const flags = new Map<string, Prediction>();
  let incomplete = 0;
  let flagged = 0;

  for (const report of block.smells) {
    incomplete += report.incomplete;
    flagged += report.flagged;
    for (const prediction of report.predictions) {
      // One model answers for every detector that asks the same question, so
      // the same verdict is filed under each of them.
      for (const smellType of report.rule_equivalent) {
        const key = keyOf(
          prediction.file_path,
          prediction.class_name,
          prediction.start_line,
          smellType,
        );
        flags.set(key, prediction);
      }
    }
  }

  return { flags, incomplete, flagged };
}

/**
 * The model's verdict on exactly what the rule flagged, when it has one.
 *
 * Absence is an answer when the model was consulted: it means the two approaches
 * disagree here, not that nothing is known. Whether it was consulted at all is
 * tracked by the caller, because only the caller can tell the two apart.
 */
export function agreementOn(index: ModelIndex | null, smell: Smell): Prediction | null {
  if (!index) return null;
  const key = keyOf(smell.file_path, smell.class_name, smell.start_line, smell.smell_type);
  return index.flags.get(key) ?? null;
}

/**
 * The model's flags on entities no rule flagged at all.
 *
 * These were always in the payload and never on the screen. The summary counted
 * them -- "Qasja B: 2 blob" -- and the list showed only what a rule had found,
 * so a reader was told a number and given no way to reach it. On one 322-file
 * project that hid 515 of 1870 model verdicts (VD-93).
 *
 * The comparison is per entity rather than per verdict: a rule finding of *any*
 * kind at the same place means the entity is already on the screen, and the
 * model's opinion of it is shown there as agreement or as silence. Only an
 * entity the rules never mentioned is unreachable.
 */
export function modelOnly(index: ModelIndex | null, smells: Smell[]): Prediction[] {
  if (!index) return [];

  const flagged = new Set(
    smells.map((s) => JSON.stringify([s.file_path, s.class_name, s.start_line])),
  );
  const seen = new Set<string>();
  const found: Prediction[] = [];
  for (const prediction of index.flags.values()) {
    const where = JSON.stringify([
      prediction.file_path,
      prediction.class_name,
      prediction.start_line,
    ]);
    if (flagged.has(where)) continue;
    // One verdict is filed under every detector that asks the same question, so
    // the same prediction arrives here once per equivalent and must be shown once.
    const once = JSON.stringify([where, prediction.smell]);
    if (seen.has(once)) continue;
    seen.add(once);
    found.push(prediction);
  }
  return found.sort((a, b) => b.probability - a.probability);
}
