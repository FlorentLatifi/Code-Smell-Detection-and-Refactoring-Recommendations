// Fjalori i thjeshtë, i njëjti që përdor CLI-ja me `--thjeshte` (VD-144).
//
// Importohet nga `backend/javasmell/glossary/` gjatë ndërtimit, si rezultatet nga
// `data/results/`: një kopje këtu do të ishte burim i dytë që ndreqet te njëra anë
// dhe harrohet te tjetra. Plotësia e tij kundrejt asaj që prodhon sistemi
// kontrollohet nga `tests/test_glossary.py`.

import words from "../../backend/javasmell/glossary/plain_sq.json";
import type { Condition } from "./types";

export interface Entry {
  name: string;
  what: string;
}

export interface SmellEntry extends Entry {
  why: string;
  fix: string;
}

const SMELLS: Record<string, SmellEntry> = words.smells;
const ALIASES: Record<string, string> = words.smell_aliases;
const METRICS: Record<string, Entry> = words.metrics;
const THRESHOLD_METRICS: Record<string, string> = words.threshold_metrics;
const SEVERITIES: Record<string, Entry> = words.severities;
const REFACTORINGS: Record<string, Entry> = words.refactorings;
const OPERATORS: Record<string, string> = words.operators;
const TERMS: Record<string, Entry> = words.terms;

/** Era sipas emrit të detektorit (`GodClass`), të MLCQ-së (`feature envy`) ose të modelit. */
export function smellEntry(name: string): SmellEntry | null {
  return SMELLS[ALIASES[name.toLowerCase()] ?? name] ?? null;
}

/** Emri i thjeshtë i erës, ose vetë emri kur fjalori nuk e njeh. */
export function smellName(name: string): string {
  return smellEntry(name)?.name ?? name;
}

/** Metrika, edhe me parashtesat e veçorive të modelit (`c_WMC`, `m_ATFD`). */
export function metricEntry(name: string): Entry | null {
  const bare = /^[cm]_/.test(name) ? name.slice(2) : name;
  return METRICS[bare] ?? null;
}

export function metricName(name: string): string {
  return metricEntry(name)?.name ?? name;
}

/**
 * Emri i një pragu (`god_class_wmc`) përmes metrikës që kufizon.
 *
 * Pragjet kanë emrat e `Thresholds` në backend; një lexues i thjeshtë i njeh vetëm
 * përmes asaj që matin.
 */
export function thresholdName(name: string): string {
  const bare = THRESHOLD_METRICS[name];
  return bare ? metricName(bare) : name;
}

export function severityEntry(name: string): Entry | null {
  return SEVERITIES[name] ?? null;
}

export function severityName(name: string): string {
  return severityEntry(name)?.name ?? name;
}

export function refactoringEntry(name: string): Entry | null {
  return REFACTORINGS[name] ?? null;
}

export function refactoringName(name: string): string {
  return refactoringEntry(name)?.name ?? name;
}

/** Një term i përgjithshëm: `smell`, `mcc`, `recall`, ... */
export function term(key: string): Entry {
  return TERMS[key] ?? { name: key, what: "" };
}

/** TCC-ja vjen si 0.0183661; tri shifra pas presjes mjaftojnë për ta krahasuar. */
export function reading(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(3)));
}

/**
 * Një klauzolë si fjali: «Rreshtat e kodit të metodës: 77 (problem kur është mbi 35)».
 *
 * E njëjta fjali që shkruan CLI-ja. Kur metrika ose operatori nuk njihen, bie te
 * emrat teknikë në vend që të shpikë një shpjegim.
 */
export function conditionSentence(condition: Condition): string {
  const word = OPERATORS[condition.operator] ?? condition.operator;
  return (
    `${metricName(condition.metric)}: ${reading(condition.value)} ` +
    `(problem kur është ${word} ${reading(condition.threshold)})`
  );
}
