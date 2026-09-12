export type Severity = "minor" | "major" | "critical";

/** One clause of a detection strategy, with the value that satisfied it. */
export interface Condition {
  metric: string;
  operator: string;
  threshold: number;
  value: number;
}

export interface Smell {
  smell_type: string;
  scope: string;
  class_name: string;
  method: string | null;
  package: string;
  file_path: string;
  start_line: number;
  end_line: number;
  severity: Severity;
  score: number;
  rationale: string;
  conditions: Condition[];
  refactorings: string[];
  metrics: Record<string, number>;
  automated: boolean;
}

/**
 * One measurement's share of a single verdict from the model.
 *
 * `drop` is how far the predicted probability falls when the measurement is set
 * to `typical`; `decisive` says that alone takes it below the decision boundary.
 */
export interface Contribution {
  feature: string;
  value: number;
  typical: number;
  drop: number;
  decisive: boolean;
}

/** One entity the model flagged, with the measurements that hold the verdict up. */
export interface Prediction {
  smell: string;
  file_path: string;
  class_name: string;
  method: string | null;
  start_line: number;
  end_line: number;
  probability: number;
  contributions: Contribution[];
}

export interface ModelReport {
  smell: string;
  /** The detector smell types that answer the same question, from the backend. */
  rule_equivalent: string[];
  considered: number;
  /** Entities skipped for want of a measurement, rather than judged on a zero. */
  incomplete: number;
  flagged: number;
  predictions: Prediction[];
}

/**
 * Approach B's answer, or why there is none.
 *
 * `data/models/` is not committed, so a fresh checkout that has not run the
 * training script gets `available: false` and a reason rather than an error.
 */
export type ModelBlock =
  | { available: true; smells: ModelReport[] }
  | { available: false; reason: string };

export interface Summary {
  files: number;
  /**
   * Sa nga ata skedarë nuk u parsuan pastër.
   *
   * Opsionale, sepse një server i vjetër nuk e dërgon; mungesa lexohet si
   * «nuk dihet» e jo si zero, ndaj paralajmërimi nuk shfaqet pa të dhëna.
   */
  unparsed?: number;
  classes: number;
  methods: number;
  smells: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
}

export interface Analysis {
  summary: Summary;
  smells: Smell[];
  /** Present only when the request asked for a second opinion. */
  model?: ModelBlock;
}

/** Një shënim mbi një rishkrim: kodi, plus numrat që teksti i tij përdor. */
export interface RewriteNote {
  code: string;
  [value: string]: string | number;
}

export interface Preview {
  applied: boolean;
  refactoring: string;
  target: string;
  refusal?: string | null;
  detail?: string;
  /**
   * Gjëra të vërteta për një rishkrim që zbatohet, e jo arsye për ta refuzuar.
   *
   * Kod dhe numra, jo fjali: serveri shkruan anglisht dhe ky ekran shqip, ndaj
   * përkthimi lidhet me kodin, njësoj si te gabimet.
   *
   * Opsionale për të njëjtën arsye si `Summary.unparsed`: një server i vjetër
   * nuk i dërgon, dhe mungesa nuk duhet lexuar si «nuk ka asgjë për të thënë».
   */
  notes?: RewriteNote[];
  before?: string;
  after?: string;
}

/** One rewrite that made it into the patch. */
export interface AppliedChange {
  file_path: string;
  refactoring: string;
  smell_type: string;
  class_name: string;
  method: string | null;
  start_line: number;
}

/** A file the engine rewrote but would not offer, because it did not verify. */
export interface DroppedFile {
  file_path: string;
  verdict: string;
  detail: string;
}

/**
 * Every rewrite the engine can make under a path, as one unified diff.
 *
 * The counts are not decoration: a patch is short for four different reasons,
 * and only naming them separately lets a reader tell "nothing to fix" from
 * "ran out of time".
 */
/**
 * One site the engine would not rewrite, and the reason it gave.
 *
 * The count alone answered "how many" and left the question a user actually
 * asks. The reasons were computed all along and thrown away by the planner
 * (VD-90).
 */
export interface DeclinedSite {
  file_path: string;
  class_name: string;
  method: string | null;
  start_line: number;
  smell_type: string;
  refactoring: string;
  reason: string;
  detail: string;
}

/**
 * Sa larg ka shkuar përgatitja e patch-it.
 *
 * `changes` rri pranë numëruesve sepse «34 nga 322 skedarë» dhe «34 nga 322
 * skedarë, ende asnjë ndryshim» janë dy pritje të ndryshme, dhe një shirit që
 * numëron vetëm skedarë nuk e thotë dot cila prej të dyjave është.
 */
export interface PatchProgress {
  files_done: number;
  files_total: number;
  changes: number;
}

/** Çfarë arriti te skedarët, dhe komanda që e kthen gjithçka. */
export interface ApplyResult {
  written: string[];
  revert: string;
  changes: number;
  verified_with_javac: boolean;
}

/** A do të lejohej një shkrim këtu, pyetur para se të planifikohet gjë. */
export interface TreeState {
  writable: boolean;
  reason: string | null;
  detail: string;
}

export interface PatchResult {
  diff: string;
  files: number;
  changes: number;
  /** Sites with no safe rewrite. */
  declined: number;
  /** Why each of those sites was declined; `declined` is its length. */
  declines: DeclinedSite[];
  /** Rewrites that collide with one already in the patch; offered again next run. */
  deferred: number;
  /** Files the time budget never reached. */
  unreached: number;
  /** False when javac was absent, so the rewrite was only checked for syntax. */
  verified_with_javac: boolean;
  dropped: DroppedFile[];
  applied: AppliedChange[];
}

export interface ApiError {
  error: { code: string; message: string };
}

/** The lines of one file around a finding, as `/source` returns them. */
export interface Source {
  start_line: number;
  end_line: number;
  truncated: boolean;
  lines: string[];
}
