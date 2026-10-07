// Dy mënyra leximi: e thjeshtë për këdo, teknike për atë që i njeh emrat (VD-144).
//
// Mënyra nuk ndryshon asnjë numër dhe asnjë gjetje. Ndryshon vetëm si emërtohen:
// «Metodë shumë e gjatë» në vend të `LongMethod`, «Rreshtat e kodit të metodës: 77
// (problem kur është mbi 35)» në vend të `MLOC 77 > 35`. Të dhënat që vijnë nga
// serveri mbeten të njëjtat.
//
// Konteksti e jep mënyrën teknike kur nuk ka ofrues. Kështu një komponent që
// renderohet vetëm, si te testet e vjetra, sillet si më parë; aplikacioni e ofron
// mënyrën e zgjedhur, dhe për një vizitor të ri ajo është e thjeshta.

import { createContext, useContext } from "react";

export type Mode = "simple" | "technical";

export const ModeContext = createContext<Mode>("technical");

export function useMode(): Mode {
  return useContext(ModeContext);
}

/** E vërtetë kur lexuesi zgjodhi mënyrën e thjeshtë. */
export function useSimple(): boolean {
  return useContext(ModeContext) === "simple";
}

/** Çelësi i mënyrës te kujtesa e shfletuesit. */
export const REMEMBERED_MODE = "javasmell.mode";

/** Mënyra e kujtuar, ose e thjeshta për dikë që e hap mjetin për herë të parë. */
export function storedMode(read: (key: string) => string): Mode {
  return read(REMEMBERED_MODE) === "technical" ? "technical" : "simple";
}

/**
 * Dy butona, njëri i shtypur: zgjedhja duket pa e lexuar etiketën e një çelësi.
 *
 * `aria-pressed` e jo radio: janë dy veprime që ndërrojnë pamjen, dhe një lexues
 * ekrani i dëgjon si «e shtypur» / «e pashtypur», njësoj si skedat e vlerësimit.
 */
export function ModeToggle({ mode, onMode }: { mode: Mode; onMode: (next: Mode) => void }) {
  const options: Array<[Mode, string, string]> = [
    ["simple", "Thjeshtë", "Shpjegime të thjeshta, pa terma teknikë"],
    ["technical", "Teknike", "Emrat dhe matjet ashtu si i përdor literatura"],
  ];
  return (
    <div
      role="group"
      aria-label="Mënyra e shpjegimit"
      className="flex h-9 shrink-0 items-center rounded-md border border-ink-200 p-0.5 dark:border-ink-700"
    >
      {options.map(([value, label, hint]) => (
        <button
          key={value}
          type="button"
          aria-pressed={mode === value}
          title={hint}
          onClick={() => onMode(value)}
          className={
            mode === value
              ? "h-full rounded-[5px] border-0 bg-brand-600 px-2.5 text-xs font-semibold text-white"
              : "h-full rounded-[5px] border-0 bg-transparent px-2.5 text-xs font-medium text-ink-600 hover:text-ink-900 dark:text-ink-300 dark:hover:text-white"
          }
        >
          {label}
        </button>
      ))}
    </div>
  );
}
