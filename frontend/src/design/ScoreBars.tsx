// Vizatimi i MCC-së me Recharts, në copën e vet (VD-123).
//
// Recharts-i ishte pjesa më e rëndë e paketës, dhe ekrani i parë nuk e përdor:
// grafiku shfaqet vetëm pas një analize. I ndarë këtu, ai shkarkohet kur duhet, dhe
// ekrani i parë hapet pa të.

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ScoreRow } from "./Panels";

const TOOLTIP = {
  borderRadius: 6,
  border: "1px solid #232b34",
  background: "#151b22",
  color: "#e3e8ee",
  fontSize: 12,
} as const;

/**
 * Ngjyrat e grafikut, si vlera e jo si variabla CSS.
 *
 * Recharts-i i shkruan si atribute `fill` të SVG-së, dhe një atribut nuk e lexon
 * `var(...)`. Të dyja zgjidhen që të mbeten të dallueshme mbi të dyja temat:
 * grafiti i rregullave dhe blu-ja e modelit, e njëjta blu si te punimi (VD-119).
 */
const RULES_FILL = "#7a8591";
const MODEL_FILL = "#2f6699";
const AXIS = "#5b6672";

export default function ScoreBars({ scores }: { scores: ScoreRow[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={scores} barGap={4} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
        <CartesianGrid stroke="#95a0ac33" vertical={false} />
        <XAxis
          dataKey="smell"
          tick={{ fill: AXIS, fontSize: 12 }}
          axisLine={{ stroke: "#95a0ac66" }}
          tickLine={false}
        />
        <YAxis
          domain={[0, 1]}
          ticks={[0, 0.25, 0.5, 0.75, 1]}
          tick={{ fill: AXIS, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip contentStyle={TOOLTIP} cursor={{ fill: "#95a0ac1f" }} />
        <Legend
          iconType="square"
          wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
          formatter={(value) => (value === "rules" ? "A: rregullat" : "B: modeli")}
        />
        <Bar dataKey="rules" fill={RULES_FILL} radius={[2, 2, 0, 0]} isAnimationActive={false} />
        <Bar dataKey="model" fill={MODEL_FILL} radius={[2, 2, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}
