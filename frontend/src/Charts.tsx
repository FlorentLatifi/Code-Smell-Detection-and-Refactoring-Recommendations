// Dy grafikët e panelit, si SVG i shkruar këtu.
//
// Pa bibliotekë. Një unazë dhe katër shtylla janë gjeometri që zë tridhjetë
// rreshta, ndërsa çdo bibliotekë grafikësh sjell me vete një model të vetin
// të dhënash, një temë për t'u mbivendosur dhe njëqind kilobajt që udhëtojnë te
// çdo ngarkim. §7 i `ENGINEERING.md` e kërkon zgjidhjen më të thjeshtë që është
// e saktë, dhe këtu ajo është `path` dhe `rect`.
//
// Të dy grafikët e mbajnë numrin pranë ngjyrës. Një legjendë ku ngjyra është i
// vetmi çelës e detyron lexuesin të kalojë sytë mes dy vendeve, dhe dikush që
// nuk i dallon ngjyrat nuk e lexon dot fare.

const TAU = Math.PI * 2;

/** Rrezja e jashtme dhe e brendshme e unazës, në njësi të `viewBox`-it. */
const OUTER = 50;
const INNER = 31;

/**
 * Ngjyrat e prerjeve, nga paleta e figurave të punimit.
 *
 * Të njëjtat që përdor `scripts/build_figures.py`, që një figurë e Kapitullit 5
 * dhe ekrani të mos i japin të njëjtës erë dy ngjyra. Lista mbahet e shkurtër
 * dhe rrotullohet: tetë lloje erërash janë maksimumi që prodhon detektori, dhe
 * tetë ngjyra të dallueshme mbi letër janë më shumë se sa duhen.
 */
const SLICES = ["#1f4e79", "#4c7ba6", "#7ba7d1", "#8a5a12", "#b08033", "#5b636d", "#96a0ac", "#c9cbcd"];

export interface Slice {
  label: string;
  value: number;
  color: string;
}

export function slicesOf(counts: Record<string, number>): Slice[] {
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([label, value], index) => ({ label, value, color: SLICES[index % SLICES.length] }));
}

/**
 * Unaza e llojeve, me legjendën pranë.
 *
 * Unazë e jo byrek: vrima e mesit mban totalin, i cili është numri që lexohet i
 * pari dhe që përndryshe do të kërkonte një etiketë të vetën diku tjetër.
 */
export function Donut({ slices, total }: { slices: Slice[]; total: number }) {
  if (total <= 0 || slices.length === 0) return null;

  let sweep = 0;
  return (
    <div className="donut">
      <svg viewBox="-60 -60 120 120" role="img" aria-label={describe(slices, total)}>
        {slices.map((slice) => {
          const from = sweep;
          sweep += slice.value / total;
          return <path key={slice.label} d={ring(from, sweep)} fill={slice.color} />;
        })}
        <text className="middle" x="0" y="2">
          {total.toLocaleString("sq")}
        </text>
        <text className="under" x="0" y="16">
          erëra
        </text>
      </svg>
      <ul className="legend">
        {slices.map((slice) => (
          <li key={slice.label}>
            <span className="chip" style={{ background: slice.color }} aria-hidden="true" />
            <span className="name">{slice.label}</span>
            <span className="count">{slice.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Përshkrimi i tërë unazës për një lexues ekrani, meqë ajo vetë është pamje. */
function describe(slices: Slice[], total: number): string {
  const parts = slices.map((s) => `${s.label} ${s.value}`);
  return `${total} erëra gjithsej: ${parts.join(", ")}`;
}

/**
 * Një prerje e unazës si shteg i mbyllur.
 *
 * `from` dhe `to` janë pjesë të së tërës në [0, 1]. Fillimi zhvendoset një çerek
 * rrotullimi prapa, që prerja e parë të nisë nga lart e jo nga djathtas: një
 * unazë që nis nga ora tre lexohet e rrotulluar.
 */
function ring(from: number, to: number): string {
  // Një prerje e vetme që mbulon gjithçka nuk vizatohet dot me hark: pika e
  // fillimit dhe e mbarimit përputhen, dhe `A` nuk di cilën anë të marrë. Dy
  // gjysma e zgjidhin pa asnjë rast të veçantë te thirrësi.
  if (to - from >= 1) {
    return `${ring(from, from + 0.5)} ${ring(from + 0.5, from + 1)}`;
  }
  const start = (from - 0.25) * TAU;
  const end = (to - 0.25) * TAU;
  const large = to - from > 0.5 ? 1 : 0;
  const [ox1, oy1] = [Math.cos(start) * OUTER, Math.sin(start) * OUTER];
  const [ox2, oy2] = [Math.cos(end) * OUTER, Math.sin(end) * OUTER];
  const [ix1, iy1] = [Math.cos(end) * INNER, Math.sin(end) * INNER];
  const [ix2, iy2] = [Math.cos(start) * INNER, Math.sin(start) * INNER];
  return [
    `M ${ox1.toFixed(2)} ${oy1.toFixed(2)}`,
    `A ${OUTER} ${OUTER} 0 ${large} 1 ${ox2.toFixed(2)} ${oy2.toFixed(2)}`,
    `L ${ix1.toFixed(2)} ${iy1.toFixed(2)}`,
    `A ${INNER} ${INNER} 0 ${large} 0 ${ix2.toFixed(2)} ${iy2.toFixed(2)}`,
    "Z",
  ].join(" ");
}

export interface Column {
  label: string;
  value: number;
  tone: string;
}

/**
 * Shtyllat e ashpërsisë.
 *
 * Lartësia matet kundrejt shtyllës më të lartë e jo kundrejt totalit: tri
 * ashpërsi ku njëra mban gjysmën do të jepnin tri shtylla të shkurtra e të
 * ngjashme, dhe grafiku do të thoshte më pak se tri numra.
 */
export function Columns({ columns }: { columns: Column[] }) {
  const tallest = Math.max(...columns.map((c) => c.value), 1);
  return (
    <div className="columns" role="img" aria-label={columns.map((c) => `${c.label} ${c.value}`).join(", ")}>
      {columns.map((column) => (
        <div key={column.label} className="column">
          <span className="value">{column.value}</span>
          <span
            className={`stem ${column.tone}`}
            style={{ height: `${Math.max(2, (column.value / tallest) * 100)}%` }}
          />
          <span className="name">{column.label}</span>
        </div>
      ))}
    </div>
  );
}
