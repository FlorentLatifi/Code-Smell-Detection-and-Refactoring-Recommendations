import type { Analysis, ApiError, Preview, Smell } from "./types";

// The server answers a failure with { error: { code, message } } and never with
// a stack trace, so the message is safe to put in front of a user unchanged.
// Anything else means the request never reached the server.
async function post<T>(path: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Serveri nuk u arrit. A është i ndezur në portin 8000?");
  }

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const named = payload as ApiError | null;
    if (named?.error?.message) throw new Error(named.error.message);
    // FastAPI's own validation failures have a different shape; the detail is
    // for a developer, not for this screen.
    if (response.status === 422) throw new Error("Kërkesa nuk është e vlefshme.");
    throw new Error(`Serveri ktheu ${response.status}.`);
  }

  return payload as T;
}

export function analyse(path: string): Promise<Analysis> {
  return post<Analysis>("/analyze", { path });
}

export function preview(path: string, smell: Smell): Promise<Preview> {
  return post<Preview>("/refactor/preview", {
    path: smell.file_path ? `${path.replace(/\/+$/, "")}/${smell.file_path}` : path,
    class_name: smell.class_name,
    method: smell.method ? smell.method.replace(/\(.*$/, "") : null,
    start_line: smell.start_line,
    smell_type: smell.smell_type,
  });
}
