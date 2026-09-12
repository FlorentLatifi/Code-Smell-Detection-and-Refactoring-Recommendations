// Paneli: gjithçka që lexohet paralelisht, në një ekran.
//
// Lista e gjetjeve rri poshtë tij dhe nuk zëvendësohet — aty është shpjegimi,
// klauzolat, kodi dhe diff-i, dhe ai është pjesa që e dallon këtë mjet nga një
// numërues erërash. Paneli i përgjigjet pyetjeve që vijnë para se dikush të hapë
// një gjetje: sa janë, çfarë lloji, sa rëndë, ku përqendrohen, nga t'ia nis.
//
// Tri kolona sepse ato janë tri pyetje të ndryshme: çfarë ka (majtas), çfarë të
// bëj (në mes), me çfarë (djathtas). Nën 1100px bëhen dy dhe nën 760px një.

import { Columns, Donut, slicesOf } from "./Charts";
import { Recommendations } from "./Recommendations";
import { countByWorst, hotspots } from "./sites";
import type { Site } from "./sites";
import type { Analysis, Severity, Smell } from "./types";

/** Ashpërsitë në radhën e tyre, e jo sipas numrit. */
const SEVERITIES: Severity[] = ["critical", "major", "minor"];

export function Dashboard({
  analysis,
  sites,
  onPick,
  onChoose,
  tools,
}: {
  analysis: Analysis;
  sites: Site[];
  /** Kliko një skedar për ta parë vetëm atë; shkruan te kërkimi i listës. */
  onPick: (file: string) => void;
  onChoose: (site: Site, smell: Smell) => void;
  /** Kolona e djathtë, e ndërtuar nga thirrësi sepse ajo mban gjendjen e tij. */
  tools: React.ReactNode;
}) {
  return (
    <div className="dashboard">
      <div className="col left">
        <Overview analysis={analysis} sites={sites} />
        <SeverityPanel sites={sites} />
        <TopFiles sites={sites} onPick={onPick} />
      </div>

      <div className="col middle">
        <Recommendations sites={sites} onChoose={onChoose} />
      </div>

      <div className="col right">{tools}</div>
    </div>
  );
}

function Panel({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="card" aria-label={title}>
      <h2>{title}</h2>
      {note && <p className="caption">{note}</p>}
      {children}
    </section>
  );
}

/** Sa u gjet, dhe si ndahet sipas llojit. */
function Overview({ analysis, sites }: { analysis: Analysis; sites: Site[] }) {
  const { summary } = analysis;
  const worst = countByWorst(sites);
  return (
    <Panel title="Përmbledhja">
      <div className="tallies">
        <Tally value={summary.smells} label="erëra" accent />
        {SEVERITIES.map((level) => (
          <Tally key={level} value={worst[level] ?? 0} label={level} tone={level} />
        ))}
      </div>
      <Donut slices={slicesOf(summary.by_type)} total={summary.smells} />
    </Panel>
  );
}

function Tally({
  value,
  label,
  tone,
  accent,
}: {
  value: number;
  label: string;
  tone?: string;
  accent?: boolean;
}) {
  return (
    <div className={`tally${accent ? " accent" : ""}`}>
      <b className={tone}>{value.toLocaleString("sq")}</b>
      <span>{label}</span>
    </div>
  );
}

/**
 * Ashpërsia e vendeve, e jo e erërave.
 *
 * E njëjta njësi si shiriti përmbledhës dhe si distinktivi i çdo rreshti: më e
 * rënda që mban vendi. Përndryshe shuma e tri shtyllave nuk do të barazonte
 * numrin e vendeve, dhe klikimi nga grafiku te lista do të ndërronte njësi në
 * rrugë.
 */
function SeverityPanel({ sites }: { sites: Site[] }) {
  const worst = countByWorst(sites);
  return (
    <Panel title="Sipas ashpërsisë" note="Më e rënda që mban secili vend.">
      <Columns
        columns={SEVERITIES.map((level) => ({
          label: level,
          value: worst[level] ?? 0,
          tone: level,
        }))}
      />
    </Panel>
  );
}

/** Skedarët ku përqendrohet puna, me ashpërsinë më të rëndë të secilit. */
function TopFiles({ sites, onPick }: { sites: Site[]; onPick: (file: string) => void }) {
  const top = hotspots(sites);
  if (top.length === 0) return null;

  const severest = new Map<string, Severity>();
  for (const site of sites) {
    const held = severest.get(site.file_path);
    if (!held || SEVERITIES.indexOf(site.worst) < SEVERITIES.indexOf(held)) {
      severest.set(site.file_path, site.worst);
    }
  }

  return (
    <Panel title="Skedarët më të ndotur" note="Kliko një rresht për ta parë vetëm atë.">
      <table className="files">
        <thead>
          <tr>
            <th scope="col">Skedari</th>
            <th scope="col">Vende</th>
            <th scope="col">Ashpërsia</th>
          </tr>
        </thead>
        <tbody>
          {top.map((spot) => (
            <tr key={spot.file}>
              <th scope="row">
                <button className="link" onClick={() => onPick(spot.file)} title={spot.file}>
                  {spot.file.split("/").pop()}
                </button>
              </th>
              <td className="number">{spot.sites}</td>
              <td>
                <span className={`pill ${severest.get(spot.file)}`}>
                  {severest.get(spot.file)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}
