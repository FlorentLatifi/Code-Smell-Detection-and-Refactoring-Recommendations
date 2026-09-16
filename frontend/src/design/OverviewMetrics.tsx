// Rreshti i parë: sa vende, sa rëndë, sa i rishkruan motori vetë, dhe cilat lloje.
//
// Ishte katër karta me ikona, një unazë me tetë ngjyra dhe një kartë automatizimi:
// rreth 540 piksela para gjetjes së parë. Unaza e ngjyroste GodClass-in me të
// kuqen e «rëndës» dhe FeatureEnvy-n me jeshilen e «lehtës», pra ngjyra thoshte dy
// gjëra njëherësh. Tani ngjyra mban vetëm ashpërsinë; llojet renditen si shirita
// të një ngjyre, dhe tërë rreshti zë gjysmën e hapësirës (VD-119).
//
// Ashpërsia numërohet **sipas vendit**, me të njëjtin rregull që përdor çdo
// rresht i listës: më e rënda që mban vendi. Kështu shuma e tri pjesëve barazon
// numrin e vendeve, dhe klikimi nga paneli te lista nuk ndryshon njësi në rrugë.

import { memo } from "react";
import { Card } from "./DashboardLayout";

export interface Slice {
  name: string;
  value: number;
}

export interface Overview {
  smells: number;
  high: number;
  medium: number;
  low: number;
  sites: number;
  automated: number;
  /** Rishkrimet e shkruara në këtë seancë, jo skedarët që i mbajnë. */
  applied: number;
  appliedFiles: number;
  byType: Slice[];
}

/**
 * Pjesa si tekst, pa e rrumbullakosur një numër jozero në zero.
 *
 * `Math.round` e shkruante DataClass me 4 erëra nga 1 450 si «0%», njësoj si një
 * lloj që nuk u gjet fare, dhe 999 nga 1 000 si «100%», njësoj si të gjitha. Të
 * dy skajet janë pohime të rreme për një lexues që e merr shifrën për të mirë
 * (VD-110).
 */
export function share(value: number, total: number): string {
  if (total <= 0) return "0%";
  const rounded = Math.round((value / total) * 100);
  if (value > 0 && rounded === 0) return "<1%";
  if (value < total && rounded === 100) return ">99%";
  return `${rounded}%`;
}

export function slicesOf(counts: Record<string, number>): Slice[] {
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value }));
}

/** Tri nivelet, nga më i rëndi. Fjala e MLCQ-së rri pranë emrit shqip. */
const LEVELS = [
  { key: "high", label: "E rëndë", word: "critical", bar: "bg-high", ink: "text-high-ink" },
  { key: "medium", label: "E mesme", word: "major", bar: "bg-medium", ink: "text-medium-ink" },
  { key: "low", label: "E lehtë", word: "minor", bar: "bg-low", ink: "text-low-ink" },
] as const;

/** Nuk varet nga filtrat; `memo` e mban jashtë çdo shkronje të kërkimit. */
export const OverviewMetrics = memo(function OverviewMetrics({ data }: { data: Overview }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
      {/* Kolonë me hapësirën mes dy blloqeve: rreshti i rrjetit e shtrin kartën
          sa lista e llojeve, dhe vizorja e ashpërsisë i përket fundit të saj e jo
          mesit, ku linte një boshllëk 110-pikselësh poshtë. */}
      <section
        aria-label="Leximi i projektit"
        className="flex min-w-0 flex-col justify-between gap-6 rounded-lg border border-ink-200 bg-white p-5 dark:border-ink-800 dark:bg-ink-900"
      >
        <div className="flex flex-wrap items-end justify-between gap-x-10 gap-y-4">
          <p className="m-0">
            <span className="block text-[44px] leading-none font-semibold tracking-[-0.02em] tabular-nums text-ink-900 dark:text-white">
              {data.sites.toLocaleString("sq")}
            </span>
            <span className="mt-2 block text-sm text-ink-600 dark:text-ink-300">
              vende me erëra, {data.smells.toLocaleString("sq")} erëra gjithsej
            </span>
          </p>
          <Automation data={data} />
        </div>
        <SeverityRuler data={data} />
      </section>

      <Card title="Sipas llojit">
        <TypeBars slices={data.byType} total={data.smells} />
      </Card>
    </div>
  );
});

/**
 * Ashpërsia si një vizore e vetme, e ndarë në tri pjesë.
 *
 * Tri kutiza me numra kërkonin që lexuesi t'i mblidhte vetë për të parë
 * përpjesën; një shirit i ndarë e jep përpjesën dhe numrat nën të japin sasinë.
 */
function SeverityRuler({ data }: { data: Overview }) {
  const total = data.high + data.medium + data.low;
  return (
    <div>
      <div className="flex h-2.5 gap-px overflow-hidden rounded-sm bg-ink-100 dark:bg-ink-800" aria-hidden="true">
        {LEVELS.map((level) =>
          data[level.key] > 0 ? (
            <span
              key={level.key}
              className={`h-full ${level.bar}`}
              style={{ width: `${(data[level.key] / total) * 100}%` }}
            />
          ) : null,
        )}
      </div>
      <div className="mt-3 grid grid-cols-3 gap-4">
        {LEVELS.map((level) => (
          <section key={level.key} aria-label={level.label} className="min-w-0">
            <p className="m-0 flex items-baseline gap-2">
              <b className={`text-2xl font-semibold tabular-nums ${level.ink}`}>
                {data[level.key].toLocaleString("sq")}
              </b>
              <span className="text-xs tabular-nums text-ink-500 dark:text-ink-400">
                {share(data[level.key], total)}
              </span>
            </p>
            <p className="m-0 mt-0.5 text-sm text-ink-700 dark:text-ink-200">
              {level.label}{" "}
              <span className="font-mono text-xs text-ink-500 dark:text-ink-400">{level.word}</span>
            </p>
          </section>
        ))}
      </div>
    </div>
  );
}

/**
 * Sa nga vendet i rishkruan motori vetë.
 *
 * Pyetje tjetër nga «sa ka»: kjo është ajo që vendos se çfarë bëhet pas këtij
 * ekrani. «Aplikuar» numëron vetëm atë që ka shkuar te disku në këtë seancë, dhe
 * është i vetmi numër i ekranit që merr jeshilen.
 */
function Automation({ data }: { data: Overview }) {
  const width = data.sites ? (data.automated / data.sites) * 100 : 0;
  // Pa «në pritje»: ai numër zbriste rishkrime nga vende, dhe pas një skanimi të
  // ri vendet e ndrequra nuk janë më te lista, ndaj zbritja i numëronte dy herë
  // (VD-122).
  return (
    <section aria-label="Sa mund të ndreqet vetë" className="min-w-[240px] flex-1 sm:max-w-[340px]">
      <p className="m-0 text-sm text-ink-700 dark:text-ink-200">
        <b className="text-lg font-semibold tabular-nums text-ink-900 dark:text-white">
          {data.automated.toLocaleString("sq")}
        </b>{" "}
        nga {data.sites.toLocaleString("sq")} vende i rishkruan motori vetë
      </p>
      <div className="mt-2 h-1.5 overflow-hidden rounded-sm bg-ink-100 dark:bg-ink-800" aria-hidden="true">
        <div className="h-full bg-brand-500 dark:bg-brand-400" style={{ width: `${width}%` }} />
      </div>
      <p className="m-0 mt-1.5 text-xs text-ink-500 dark:text-ink-400">
        {share(data.automated, data.sites)} e vendeve.{" "}
        {data.applied > 0 ? (
          <span className="font-medium text-ok-ink">
            {data.applied} {data.applied === 1 ? "ndryshim u aplikua" : "ndryshime u aplikuan"} në{" "}
            {data.appliedFiles} {data.appliedFiles === 1 ? "skedar" : "skedarë"}.
          </span>
        ) : (
          "Asgjë e aplikuar ende."
        )}
      </p>
    </section>
  );
}

/**
 * Llojet si shirita të renditur, të një ngjyre.
 *
 * Gjatësia matet kundrejt llojit më të shpeshtë, jo kundrejt totalit, që dallimi
 * mes të dytit dhe të tretit të shihet; pjesa e totalit shkruhet pranë. Paragrafi
 * me rolin `img` e përshkruan tërë shpërndarjen për një lexues ekrani, dhe lista
 * mbetet listë e lexueshme.
 *
 * Te ekranet e ngushta emri merr pjesën që mbetet dhe shiriti mban një gjerësi të
 * fiksuar: me kolonën e emrit të fiksuar, te 390 piksela shiriti tkurrej në zero.
 */
function TypeBars({ slices, total }: { slices: Slice[]; total: number }) {
  if (total <= 0 || slices.length === 0) return null;
  const label = `${total} erëra gjithsej: ${slices.map((s) => `${s.name} ${s.value}`).join(", ")}`;
  const most = slices[0].value;

  return (
    <div className="px-4 pb-4">
      <p role="img" aria-label={label} className="m-0 text-xs text-ink-500 dark:text-ink-400">
        {total.toLocaleString("sq")} erëra, nga më i shpeshti
      </p>
      <ul className="m-0 mt-3 list-none space-y-2 p-0">
        {slices.map((slice) => (
          <li
            key={slice.name}
            className="grid grid-cols-[minmax(0,1fr)_4.5rem_2rem_2.5rem] items-center gap-3 text-sm sm:grid-cols-[minmax(0,10.5rem)_minmax(0,1fr)_2.5rem_2.75rem]"
          >
            <span className="truncate font-mono text-[13px] text-ink-800 dark:text-ink-100">
              {slice.name}
            </span>
            <span className="h-2 rounded-sm bg-ink-100 dark:bg-ink-800" aria-hidden="true">
              <span
                className="block h-full rounded-sm bg-brand-600 dark:bg-brand-400"
                style={{ width: `${(slice.value / most) * 100}%` }}
              />
            </span>
            <span className="text-right tabular-nums text-ink-800 dark:text-ink-100">{slice.value}</span>
            <span className="text-right text-xs tabular-nums text-ink-500 dark:text-ink-400">
              {share(slice.value, total)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
