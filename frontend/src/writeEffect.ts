// Çfarë bëri shkrimi me erërat, i matur me skanimin pas tij (VD-123).
//
// Pas një shkrimi, numri i erërave mund të mbetet i njëjtë ndonëse kodi ndryshoi:
// rishkrimi heq erën për të cilën u bë, por mund të sjellë një tjetër, si
// konstruktori i një objekti-parametër me po aq parametra. Numri i vetëm e fsheh
// këtë, ndaj ekrani i numëron veç: sa u hoqën, sa lindën, sa mbetën. Është e
// njëjta matje që Nënkapitulli 5.4 bën mbi korpusin.

import type { Smell } from "./types";

export interface Entry {
  file: string;
  /** Klasa, ose klasa dhe metoda. */
  entity: string;
  smell: string;
}

export interface WriteEffect {
  removed: Entry[];
  introduced: Entry[];
  kept: number;
}

/**
 * Entiteti sipas emrit, jo sipas rreshtit.
 *
 * Rishkrimi i lëviz rreshtat, ndaj rreshti nuk e njeh të njëjtin entitet pas tij.
 * Parametrat hiqen nga emri i metodës për të njëjtën arsye: Introduce Parameter
 * Object e ndryshon nënshkrimin, jo metodën (VD-44).
 */
function keyOf(smell: Smell): string {
  const method = smell.method ? smell.method.replace(/\(.*$/, "") : "";
  return JSON.stringify([smell.file_path, smell.class_name, method, smell.smell_type]);
}

function entryOf(smell: Smell): Entry {
  const method = smell.method ? `.${smell.method.replace(/\(.*$/, "")}` : "";
  return { file: smell.file_path, entity: `${smell.class_name}${method}`, smell: smell.smell_type };
}

function ordered(entries: Entry[]): Entry[] {
  return entries.sort(
    (a, b) =>
      a.file.localeCompare(b.file) ||
      a.entity.localeCompare(b.entity) ||
      a.smell.localeCompare(b.smell),
  );
}

/**
 * Krahasimi i erërave para dhe pas, si shumësi.
 *
 * Dy metoda me të njëjtin emër (mbingarkesa) japin të njëjtin çelës, ndaj
 * numërohen: nëse para kishte dy dhe pas një, njëra u hoq.
 */
export function writeEffect(before: Smell[], after: Smell[]): WriteEffect {
  const remaining = new Map<string, Smell[]>();
  for (const smell of after) {
    const key = keyOf(smell);
    remaining.set(key, [...(remaining.get(key) ?? []), smell]);
  }

  const removed: Entry[] = [];
  let kept = 0;
  for (const smell of before) {
    const matches = remaining.get(keyOf(smell));
    if (matches && matches.length > 0) {
      matches.pop();
      kept += 1;
    } else {
      removed.push(entryOf(smell));
    }
  }

  const introduced = [...remaining.values()].flat().map(entryOf);
  return { removed: ordered(removed), introduced: ordered(introduced), kept };
}
