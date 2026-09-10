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

import blockingJson from "../../data/results/blocking_conditions.json";
import datasetJson from "../../data/results/mlcq_dataset.json";
import mlJson from "../../data/results/ml_evaluation.json";
import pmdJson from "../../data/results/pmd_comparison.json";
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
  per_smell: Record<string, ModelSmell>;  environment: { commit: string; python: string; platform: string };
}

interface RefactoringEvaluation {
  files: number;
  detected: number;
  applied: number;
  refused: number;
  unlocatable: number;
  refused_by_reason: Record<string, number>;
  verdicts: Record<string, number>;
  applied_by_refactoring: Record<string, number>;  environment: { commit: string; python: string; platform: string };
}

interface Dataset {
  rows: number;
  samples_considered: number;
  repositories: number;
  by_smell: Record<string, number>;
  by_entity_type: Record<string, number>;  environment: { commit: string; python: string; platform: string };
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
  per_smell: Record<string, Record<string, SweepPoint[]>>;  environment: { commit: string; python: string; platform: string };
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

// Çdo verdikt që `Verdict` mund të prodhojë, jo vetëm ata që korpusi nxori. Një
// verdikt pa përkthim nuk e prish pamjen — tabela bie te vetë çelësi — por e
// shfaq atë çelës anglisht mes etiketave shqip, dhe pikërisht kështu `parses`
// qëndroi i papërkthyer në panel.
export const VERDICT_SQ: Record<string, string> = {
  no_new_errors: "pa gabim të ri",
  compiles: "kompilon plotësisht",
  parses: "parsohet, pa kontroll kompilimi",
  new_errors: "me gabim të ri",
  broken_syntax: "sintaksë e prishur",
  not_checked: "i pakontrolluar",
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




// ----------------------------------------------------------------------
// Pse nuk ndezin strategjitë
// ----------------------------------------------------------------------
// Paneli tregon recall-in e Blob-it si 10%, dhe deri tani nuk thoshte asgjë për
// arsyen. Një strategji e Lanza & Marinescu-t është konjunksion, ndaj çdo
// mospërputhje ka shkak të emërtueshëm: një klauzolë, dy, ose të tria nuk
// qëndruan. Këta numra e mbajnë atë përgjigje.

export interface Blocking {
  missed: number;
  blocked_by_one_clause: number;
  clauses_failing: Record<string, number>;
  sole_blocker: Record<string, number>;
  median_shortfall: Record<string, number>;
}

interface BlockingFile {
  by_smell: Record<string, Blocking>;
  environment: { commit: string; python: string; platform: string };
}

const blockingData = blockingJson as BlockingFile;

/** Llogaria e klauzolave për një erë, ose null kur strategjia s'është konjunksion. */
export function blockingFor(smell: string): Blocking | null {
  return blockingData.by_smell[smell] ?? null;
}

// ----------------------------------------------------------------------
// Krahasimi me një mjet të jashtëm
// ----------------------------------------------------------------------
// Dy MCC krah njëri-tjetrit ftojnë lexuesin të lexojë fitore aty ku ka vetëm
// lëkundje, ndaj intervali i çiftuar shkon bashkë me to dhe kurrë veç.

export interface PmdSide {
  mcc: number | null;
  precision: number | null;
  recall: number;
}

export interface PmdDifference {
  low: number;
  high: number;
  median: number;
  excludes_zero: boolean;
}

export interface PmdRow {
  scored: number;
  pmd: PmdSide;
  ours?: PmdSide;
  difference?: PmdDifference;
}

interface PmdFile {
  pmd_version: string;
  repositories: number;
  repositories_failed: string[];
  files_pmd_could_not_read: number;
  by_smell: Record<string, PmdRow>;
  environment: { commit: string; python: string; platform: string };
}

export const pmd = pmdJson as PmdFile;

/** Emrat e rreshtave si i shkruan punimi, që tabela të mos flasë me çelësa. */
export const PMD_ROW_SQ: Record<string, string> = {
  "blob/strategy": "Blob, strategjia",
  "blob/with_size": "Blob, me madhësinë",
  "data class/strategy": "Data Class",
  "feature envy/law_of_demeter": "Feature Envy (LawOfDemeter)",
  "long method/strategy": "Long Method",
};

/**
 * Çdo commit që qëndron pas numrave të këtij paneli, pa përsëritje.
 *
 * Paneli i lexon disa skedarë rezultati dhe secili mban mjedisin e vet.
 * Eksperimentet u ekzekutuan sipas radhës në të cilën u shkruan, ndaj ata
 * mjedise nuk janë një: fusnota shtypte commit-in e `rules_evaluation.json`
 * sikur t'i kishte prodhuar të gjithë, dhe ai ishte i saktë vetëm për dy nga
 * pesë. I njëjti defekt te punimi u ndreq si VD-59.
 *
 * Lista rritet bashkë me panelin. Kur u shtuan krahasimi me PMD-në dhe llogaria
 * e klauzolave, fusnota do të kishte vazhduar të pretendonte prejardhjen e vjetër
 * po të mos ishin shtuar edhe këtu — pikërisht defekti që kjo listë ekziston për
 * ta ndaluar.
 */
export const SOURCES = [rules, ml, refactoring, dataset, sweep, pmd, blockingData] as const;

export const COMMITS: string[] = [
  ...new Set(SOURCES.map((source) => source.environment.commit.slice(0, 10))),
].sort();
