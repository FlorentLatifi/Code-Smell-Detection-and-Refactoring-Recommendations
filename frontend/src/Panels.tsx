// Primitivat që të gjitha panelet e rezultateve i ndajnë.
//
// Të nxjerra nga `Results.tsx` sepse ai kishte arritur 548 rreshta dhe gjysma e
// tyre ishin shirita, qeliza dhe korniza që nuk dinë asgjë për erërat: ato lexohen
// një herë dhe pastaj janë vetëm zhurmë mes paneleve që mbajnë kuptimin.

export function Distribution({
  counts,
  labels,
  total,
}: {
  counts: Record<string, number>;
  labels: Record<string, string>;
  total: number;
}) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return (
    <table className="grid">
      <tbody>
        {entries.map(([key, value]) => (
          <tr key={key}>
            <th scope="row">{labels[key] ?? key}</th>
            <td>
              <Bar value={value / total} tone="rules" format="percent" />
            </td>
            <td className="figures quiet">{value.toLocaleString("sq")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
export function Bar({
  value,
  tone,
  format = "score",
}: {
  value: number | null;
  tone: string;
  // MCC-ja lexohet si koeficient dhe shkruhet me tri shifra; një pjesë e së tërës
  // lexohet si përqindje. I shkruar njësoj, njëri nga të dy do të dilte i çuditshëm.
  format?: "score" | "percent";
}) {
  if (value === null) return <span className="quiet">i papërcaktuar</span>;
  // MCC-ja shkon nga -1 në 1, por çdo vlerë e matur këtu është jo-negative; një
  // shirit i gjatësisë negative do të ishte i pakuptimtë, ndaj pritet te zeroja.
  const width = Math.max(0, Math.min(1, value)) * 100;
  const text = format === "percent" ? `${(value * 100).toFixed(1)}%` : value.toFixed(3);
  return (
    <span className="bar" title={text}>
      <span className={`fill ${tone}`} style={{ width: `${width}%` }} />
      <b>{text}</b>
    </span>
  );
}
export function Cell({ value, strong }: { value: number | null; strong?: boolean }) {
  return (
    <td className={strong ? "figures strong" : "figures"}>
      {value === null ? "—" : value.toFixed(3)}
    </td>
  );
}
export function Figure({
  value,
  label,
  accent,
}: {
  value: string | number;
  label: string;
  accent?: boolean;
}) {
  return (
    <div className={accent ? "figure accent" : "figure"}>
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}
export function Panel({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      {note && <p className="quiet">{note}</p>}
      {children}
    </section>
  );
}
export function Missing() {
  return <span className="quiet">s'ka</span>;
}
