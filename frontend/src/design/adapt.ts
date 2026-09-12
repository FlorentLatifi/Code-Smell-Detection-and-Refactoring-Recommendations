// Nga modeli i aplikacionit te format që panelit i duhen.
//
// Komponentët e panelit nuk dinë asgjë për `Site`, `Smell` ose për API-në: ata
// marrin forma të thjeshta dhe i vizatojnë. Përkthimi rri këtu, në një vend, që
// faqja e dizajnit me të dhëna të rreme dhe aplikacioni me ato të vërteta të
// ushqejnë të njëjtët komponentë (VD-106).

import { ml, rules, SMELLS, SMELL_SQ } from "../evaluation";
import { countByWorst, hotspots } from "../sites";
import type { Site } from "../sites";
import type { Summary } from "../types";
import type { Overview } from "./OverviewMetrics";
import { slicesOf } from "./OverviewMetrics";
import type { FileRow, ScoreRow, Severity } from "./Panels";
import type { Suggestion } from "./RefactoringActionList";

const ORDER: Severity[] = ["critical", "major", "minor"];

export function overviewOf(summary: Summary, sites: Site[], applied: number): Overview {
  const worst = countByWorst(sites);
  return {
    smells: summary.smells,
    high: worst.critical ?? 0,
    medium: worst.major ?? 0,
    low: worst.minor ?? 0,
    sites: sites.length,
    automated: sites.filter((site) => site.automated).length,
    applied,
    byType: slicesOf(summary.by_type),
  };
}

/**
 * Një sugjerim për vend, jo për erë.
 *
 * Një metodë e gjatë dhe e folezuar mban katër erëra, dhe katër rreshta për të
 * njëjtën metodë do të ishin katër herë e njëjta punë. Era e zgjedhur është ajo
 * që motori e rishkruan, kur ka një të tillë, sepse ajo është ajo që premton
 * butoni; përndryshe më e rënda.
 */
export function suggestionsOf(sites: Site[]): Suggestion[] {
  return sites.map((site) => {
    const smell = site.smells.find((s) => s.automated) ?? site.smells[0];
    return {
      key: site.key,
      entity: label(site),
      file: site.file_path,
      line: site.start_line,
      smell: smell.smell_type,
      reason: smell.rationale,
      refactoring: smell.refactorings[0] ?? "",
      severity: site.worst as Severity,
      automated: site.automated,
    };
  });
}

function label(site: Site): string {
  const method = site.method ? `.${site.method.replace(/\(.*$/, "")}` : "";
  return `${site.class_name}${method}`;
}

/** Skedarët me më shumë vende, me ashpërsinë më të rëndë të secilit. */
export function fileRowsOf(sites: Site[]): FileRow[] {
  const severest = new Map<string, Severity>();
  const className = new Map<string, string>();
  for (const site of sites) {
    const held = severest.get(site.file_path);
    const worst = site.worst as Severity;
    if (!held || ORDER.indexOf(worst) < ORDER.indexOf(held)) severest.set(site.file_path, worst);
    if (!className.has(site.file_path)) className.set(site.file_path, site.class_name);
  }

  return hotspots(sites).map((spot) => ({
    cls: className.get(spot.file) ?? (spot.file.split("/").pop() ?? spot.file),
    path: spot.file,
    file: spot.file,
    smells: spot.smells,
    severity: severest.get(spot.file) ?? "minor",
  }));
}

/**
 * MCC-ja e secilës erë për të dyja qasjet, nga skedarët e komituar.
 *
 * Të njëjtat vlera që raporton skeda e vlerësimit dhe Kapitulli 5. Grafiku nuk
 * llogarit asgjë; nëse një numër ndryshon, ai ndryshon te `data/results/`.
 */
export function scoreRows(): ScoreRow[] {
  return SMELLS.map((smell) => {
    const variant = rules.per_smell[smell]?.strategy;
    const per = ml.per_smell[smell];
    return {
      smell: SMELL_SQ[smell] ?? smell,
      rules: variant?.by_aggregation.mean.mcc ?? null,
      model: per ? (per.models[per.best_model]?.mcc ?? null) : null,
    };
  });
}
