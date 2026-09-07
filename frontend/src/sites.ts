// Një metodë ose klasë, me të gjitha erërat që u gjetën në të.
//
// Detektorët raportojnë një erë për strategji, jo një për vend, ndaj një metodë
// tepër e gjatë dhe tepër e folezuar kthehet katër herë: `LongMethod`,
// `BrainMethod`, `DeepNesting`, `LongParameterList`. Të gjitha janë të sakta dhe
// asnjëra nuk është e tepërt — secila e mat diçka tjetër — por lista e papërpunuar
// i vë si katër rreshta të barabartë me çdo rresht tjetër.
//
// Pasoja matet: mbi `commons-math/analysis`, 106 gjetje bien mbi 74 vende, dhe
// tetëmbëdhjetë vende mbajnë më shumë se një erë. Lista e mbivendos punën me 43%,
// dhe fsheh sinjalin më të dobishëm që ka: metoda me katër erëra njëherësh është
// më e keqja e projektit, jo katër probleme të zakonshme.
//
// Grupimi nuk heq asgjë. Të njëjtat erëra shfaqen, të mbledhura te vendi që i
// mban, dhe numri i tyre bëhet kriter renditjeje.

import type { Severity, Smell } from "./types";

export const SEVERITY_ORDER: Record<Severity, number> = { critical: 0, major: 1, minor: 2 };

export interface Site {
  /** Çelësi i vendit: skedari, klasa, rreshti fillestar. */
  key: string;
  file_path: string;
  class_name: string;
  method: string | null;
  start_line: number;
  /** Erërat e këtij vendi, më e rënda e para. */
  smells: Smell[];
  /** Ashpërsia më e rëndë mes tyre. */
  worst: Severity;
  /** Teprica më e madhe mes tyre. */
  score: number;
  /** A e rishkruan motori vetë të paktën njërën. */
  automated: boolean;
}

/**
 * Çelësi i vendit — pa llojin e erës, ndryshe nga çelësi te `model.ts`.
 *
 * Aty llojit i duhet të hyjë, sepse te `class A { void m() {} }` klasa dhe metoda
 * nisin në të njëjtin rresht dhe verdiktet duhen ndarë. Këtu ndarja bëhet nga
 * emri i metodës, i cili është `null` për një erë klase, ndaj dy entitetet nuk
 * përzihen dot as pa llojin.
 *
 * Serializohet e nuk bashkohet me ndarës, për të njëjtën arsye si te `model.ts`:
 * një shteg mund ta përmbajë ligjshëm çdo shenjë që do të zgjidhej si ndarës.
 */
function keyOf(smell: Smell): string {
  return JSON.stringify([smell.file_path, smell.class_name, smell.method, smell.start_line]);
}

function worse(a: Smell, b: Smell): number {
  return SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] || b.score - a.score;
}

/**
 * Mbledh erërat te vendet e tyre, duke ruajtur radhën e parë të shfaqjes.
 *
 * Radha e hyrjes vendos radhën e daljes, që thirrësi ta rendisë vetë pas kësaj:
 * grupimi nuk duhet ta imponojë një renditje mbi një listë që përdoruesi mund ta
 * ketë renditur sipas skedarit.
 */
export function groupBySite(smells: Smell[]): Site[] {
  const byKey = new Map<string, Site>();

  for (const smell of smells) {
    const key = keyOf(smell);
    const existing = byKey.get(key);
    if (existing) {
      existing.smells.push(smell);
      continue;
    }
    byKey.set(key, {
      key,
      file_path: smell.file_path,
      class_name: smell.class_name,
      method: smell.method ?? null,
      start_line: smell.start_line,
      smells: [smell],
      worst: smell.severity,
      score: smell.score,
      automated: smell.automated,
    });
  }

  for (const site of byKey.values()) {
    site.smells.sort(worse);
    site.worst = site.smells[0].severity;
    site.score = Math.max(...site.smells.map((s) => s.score));
    site.automated = site.smells.some((s) => s.automated);
  }
  return [...byKey.values()];
}

/**
 * Rendit vendet sipas asaj që një zhvillues do të hapte të parën.
 *
 * Ashpërsia vjen e para, pastaj **numri i erërave**, dhe vetëm pastaj teprica.
 * Numri hyn këtu me qëllim: një metodë që thyen katër strategji njëherësh nuk
 * është e barabartë me një që thyen një të vetme, dhe pikërisht ai dallim
 * humbiste kur secila erë zinte rreshtin e vet.
 */
export function bySeverity(sites: Site[]): Site[] {
  return [...sites].sort(
    (a, b) =>
      SEVERITY_ORDER[a.worst] - SEVERITY_ORDER[b.worst] ||
      b.smells.length - a.smells.length ||
      b.score - a.score,
  );
}

export function byScore(sites: Site[]): Site[] {
  return [...sites].sort((a, b) => b.score - a.score);
}

export function byFile(sites: Site[]): Site[] {
  return [...sites].sort(
    (a, b) => a.file_path.localeCompare(b.file_path) || a.start_line - b.start_line,
  );
}

/**
 * Sa vende bien nën secilën ashpërsi, sipas më të rëndës që mban secili.
 *
 * Shiriti përmbledhës numëronte erëra ndërsa lista poshtë tij numëron vende, dhe
 * të dy flisnin për të njëjtën analizë me njësi të ndryshme: 106 kundrejt 74, pa
 * asgjë që ta shpjegonte dallimin. Kjo e mat ashpërsinë me të njëjtin rregull që
 * përdor distinktivi i rreshtit, ndaj shifra lart dhe distinktivët poshtë
 * pajtohen gjithmonë.
 */
export function countByWorst(sites: Site[]): Record<Severity, number> {
  const tally: Record<Severity, number> = { critical: 0, major: 0, minor: 0 };
  for (const site of sites) tally[site.worst] += 1;
  return tally;
}
