// Të dhëna të rreme, të shënuara si të tilla.
//
// Kjo faqe ekziston për të gjykuar pamjen, jo për të raportuar një analizë. Çdo
// shifër këtu është e shpikur, dhe kjo thuhet edhe në ekran: një panel që duket
// i vërtetë dhe nuk është do të ishte gjëja më e keqe që mund të ndërtohej te
// një projekt ku çdo numër tjetër vjen nga një skedar i komituar.

export type Severity = "high" | "medium" | "low";

export interface Finding {
  id: string;
  file: string;
  entity: string;
  smell: string;
  reason: string;
  severity: Severity;
  /** A e rishkruan motori vetë, apo mbetet propozim. */
  automated: boolean;
  /** Sa rreshta shton e heq rishkrimi i propozuar. */
  added: number;
  removed: number;
}

export const project = {
  name: "acme/ledger-service",
  branch: "main",
  lastScan: "2 minuta më parë",
  loc: 45_210,
  files: 312,
  duration: "8.4 s",
};

export const totals = {
  smells: 94,
  high: 36,
  medium: 42,
  low: 16,
  automated: 23,
  applied: 7,
};

export const byType = [
  { name: "Long Method", value: 31, color: "#6366f1" },
  { name: "Feature Envy", value: 24, color: "#22d3ee" },
  { name: "Data Class", value: 18, color: "#f59e0b" },
  { name: "Blob", value: 11, color: "#f43f5e" },
  { name: "Të tjera", value: 10, color: "#64748b" },
];

export const findings: Finding[] = [
  {
    id: "1",
    file: "src/services/OrderProcessor.java",
    entity: "OrderProcessor.processPayment()",
    smell: "Long Method",
    reason: "56 rreshta efektivë, mbi kufirin 30. Validimi dhe logimi ndahen pa varësi mes tyre.",
    severity: "high",
    automated: true,
    added: 24,
    removed: 18,
  },
  {
    id: "2",
    file: "src/models/CustomerProfile.java",
    entity: "CustomerProfile.updateContact()",
    smell: "Long Parameter List",
    reason: "8 parametra, mbi kufirin 5. Shtatë prej tyre vijnë nga i njëjti objekt.",
    severity: "medium",
    automated: true,
    added: 31,
    removed: 9,
  },
  {
    id: "3",
    file: "src/web/ProductSearch.java",
    entity: "ProductSearch.calculateTax()",
    smell: "Feature Envy",
    reason: "ATFD 7 mbi kufirin 5, LAA 0.12 nën 0.33. Llogaritja i takon TaxCalculator-it.",
    severity: "high",
    automated: false,
    added: 0,
    removed: 0,
  },
  {
    id: "4",
    file: "src/services/InvoiceRenderer.java",
    entity: "InvoiceRenderer.render()",
    smell: "Deep Nesting",
    reason: "Gjashtë nivele folezimi, mbi kufirin 3. Tri kushtet e para janë roje.",
    severity: "medium",
    automated: true,
    added: 19,
    removed: 22,
  },
  {
    id: "5",
    file: "src/models/ShoppingCart.java",
    entity: "ShoppingCart",
    smell: "Data Class",
    reason: "WOC 0, dhe 9 fusha publike me akses të drejtpërdrejtë nga katër klasa.",
    severity: "low",
    automated: false,
    added: 0,
    removed: 0,
  },
];

export const applied = [
  { id: "a1", entity: "AttributeStream.writeRange()", smell: "Long Method", when: "sot, 14:02" },
  { id: "a2", entity: "Envelope2D.intersect()", smell: "Deep Nesting", when: "sot, 13:58" },
  { id: "a3", entity: "MetadataTable.scan()", smell: "Long Method", when: "dje, 17:41" },
];

/** MCC për secilën erë, të dyja qasjet. Zero do të thotë «sa hamendja». */
export const scores = [
  { smell: "Long Method", rules: 0.58, model: 0.71 },
  { smell: "Feature Envy", rules: 0.27, model: 0.67 },
  { smell: "Data Class", rules: 0.28, model: 0.5 },
  { smell: "Blob", rules: 0.23, model: 0.49 },
];

export const smellyFiles = [
  { cls: "OrderManager", path: "src/services/", smells: 9, severity: "high" as Severity },
  { cls: "ProductController", path: "src/web/", smells: 7, severity: "medium" as Severity },
  { cls: "InvoiceRenderer", path: "src/services/", smells: 6, severity: "medium" as Severity },
  { cls: "ShoppingCart", path: "src/models/", smells: 5, severity: "low" as Severity },
  { cls: "CustomerProfile", path: "src/models/", smells: 4, severity: "low" as Severity },
];
