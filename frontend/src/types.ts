export type Severity = "minor" | "major" | "critical";

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
  refactorings: string[];
  metrics: Record<string, number>;
  automated: boolean;
}

export interface Summary {
  files: number;
  classes: number;
  methods: number;
  smells: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
}

export interface Analysis {
  summary: Summary;
  smells: Smell[];
}

export interface Preview {
  applied: boolean;
  refactoring: string;
  target: string;
  refusal?: string | null;
  detail?: string;
  before?: string;
  after?: string;
}

export interface ApiError {
  error: { code: string; message: string };
}
