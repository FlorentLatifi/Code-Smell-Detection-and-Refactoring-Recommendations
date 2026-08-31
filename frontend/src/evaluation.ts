// Rezultatet e vlerësimit, të lexuara nga `data/results/` gjatë ndërtimit.
//
// Këto nuk janë të dhëna të drejtpërdrejta: janë faktet e matura të punimit, të
// prodhuara nga skriptet dhe të komituara. Prandaj nuk kalojnë nëpër API — një
// endpoint do t'i shndërronte në diçka që varet nga serveri, ndërkohë që ato nuk
// ndryshojnë kurrë ndërmjet dy ekzekutimeve. I importuar këtu, paneli i
// rezultateve hapet edhe kur backend-i nuk është i ndezur, çka është pikërisht
// gjendja e një prezantimi.
//
// Burimi i vetëm mbetet `data/results/`; asnjë numër nuk kopjohet në frontend.

import datasetJson from "../../data/results/mlcq_dataset.json";
import mlJson from "../../data/results/ml_evaluation.json";
import refactoringJson from "../../data/results/refactoring_evaluation.json";
import rulesJson from "../../data/results/rules_evaluation.json";
import sweepJson from "../../data/results/threshold_sweep.json";

export type Aggregation = "mean" | "max" | "min" | "unanimous";

export const AGGREGATIONS: Aggregation[] = ["mean", "max", "min", "unanimous"];

// Si zgjidhet mospajtimi mes rishikuesve. Teksti shpjegon çka do të thotë secila,
// sepse ndryshimi mes tyre është vetë një rezultat i punimit.
export const AGGREGATION_SQ: Record<Aggregation, string> = {
  mean: "mesatarja e rishikimeve",
  max: "mjafton një rishikues",
  min: "rishikuesi më i butë",
  unanimous: "vetëm kur pajtohen të gjithë",
};

export interface Score {
  accuracy: number;
  precision: number;
  recall: number;
  f1: number | null;
  mcc: number | null;
  tp: number;
  fp: number;
  tn: number;
  fn: number;
  support_positive: number;
}

export interface SeverityRecall {
  caught: number;
  recall: number;
  support: number;
}

export interface RuleVariant {
  by_aggregation: Record<Aggregation, Score>;
  recall_by_severity: Record<string, SeverityRecall>;
}

interface RulesEvaluation {
  scored: number;
  per_smell: Record<string, Record<string, RuleVariant>>;
  environment: { commit: string; python: string; platform: string };
}

export interface Agreement {
  both: number;
  only_rules: number;
  only_model: number;
  neither: number;
  kappa: number;
  n: number;
}

export interface ModelSmell {
  best_model: string;
  models: Record<string, Score>;
  top_features: string[];
  vs_rules: Agreement;
  data: { samples: number; positives: number; repositories: number; features: number };
}

interface MlEvaluation {
  label: string;
  folds: number;
  seed: number;
  per_smell: Record<string, ModelSmell>;
}

interface RefactoringEvaluation {
  files: number;
  detected: number;
  applied: number;
  refused: number;
  unlocatable: number;
  refused_by_reason: Record<string, number>;
  verdicts: Record<string, number>;
  applied_by_refactoring: Record<string, number>;
}

interface Dataset {
  rows: number;
  samples_considered: number;
  repositories: number;
  by_smell: Record<string, number>;
  by_entity_type: Record<string, number>;
}

export interface SweepPoint {
  factor: number;
  value: number;
  mcc: number | null;
  f1: number;
  precision: number;
  recall: number;
  fired: number;
}

interface Sweep {
  factors: number[];
  per_smell: Record<string, Record<string, SweepPoint[]>>;
}

export const rules = rulesJson as unknown as RulesEvaluation;
export const ml = mlJson as unknown as MlEvaluation;
export const refactoring = refactoringJson as unknown as RefactoringEvaluation;
export const dataset = datasetJson as unknown as Dataset;
export const sweep = sweepJson as unknown as Sweep;

// Varianti parësor i çdo ere. `blob` ka edhe një të dytë — God Class plus madhësia
// — që raportohet veç, sepse bashkimi është konstrukt i këtij punimi dhe jo një
// strategji e botuar.
export const PRIMARY_VARIANT = "strategy";

export const SMELLS = Object.keys(rules.per_smell).sort();

export const SMELL_SQ: Record<string, string> = {
  blob: "Blob",
  "data class": "Data Class",
  "feature envy": "Feature Envy",
  "long method": "Long Method",
};

export const MODEL_SQ: Record<string, string> = {
  gradient_boosting: "Gradient Boosting",
  random_forest: "Random Forest",
  logistic: "Regresion logjistik",
  majority: "Klasifikuesi i shumicës",
};

export const REFUSAL_SQ: Record<string, string> = {
  shape_not_matched: "forma e kodit nuk përputhet",
  control_flow_escapes: "rrjedha e kontrollit del nga blloku",
  not_definitely_assigned: "vlerë hyrëse e pacaktuar ende",
  multiple_outputs: "më shumë se një vlerë dalëse",
  unresolved_name: "emër i pazgjidhur",
  possible_side_effect: "efekt anësor i mundshëm",
  ambiguous_overload: "mbingarkesë e paqartë",
  edit_conflict: "editime që mbivendosen",
  unparseable: "skedar që nuk parsohet",
};

export const VERDICT_SQ: Record<string, string> = {
  no_new_errors: "pa gabim të ri",
  compiles: "kompilon plotësisht",
  new_errors: "me gabim të ri",
  broken_syntax: "sintaksë e prishur",
};

/** Rezultati i rregullave për një erë, në variantin parësor dhe agregimin e dhënë. */
export function ruleScore(smell: string, aggregation: Aggregation): Score {
  return rules.per_smell[smell][PRIMARY_VARIANT].by_aggregation[aggregation];
}

/** Varianti i dytë, kur ekziston: sot vetëm `blob` e ka. */
export function variantScore(smell: string, aggregation: Aggregation): Score | null {
  const variants = rules.per_smell[smell];
  const extra = Object.keys(variants).find((name) => name !== PRIMARY_VARIANT);
  return extra ? variants[extra].by_aggregation[aggregation] : null;
}
