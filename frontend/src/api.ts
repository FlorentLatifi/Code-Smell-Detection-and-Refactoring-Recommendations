import type { Analysis, ApiError, PatchResult, Preview, Smell, Source } from "./types";

// The server answers a failure with { error: { code, message } } and never with
// a stack trace, so the message is safe to put in front of a user unchanged.
// Anything else means the request never reached the server.
/**
 * Sa gjatë pritet një përgjigje para se të hiqet dorë.
 *
 * Pa afat, një projekt i madh e linte ekranin te «Duke matur skedarët…» pa fund
 * dhe pa dalje: `/analyze` nuk ka buxhet kohe te serveri, vetëm tavane numri dhe
 * madhësie skedarësh. Dy minuta janë mbi çdo analizë të arsyeshme mbi një pemë të
 * lejuar dhe nën durimin e dikujt që mendon se mjeti ka ngecur.
 */
const TIMEOUT_MS = 120_000;

/** Ndalimi nga vetë përdoruesi dhe ndalimi nga afati lexohen ndryshe. */
export class Cancelled extends Error {}

/**
 * Çfarë do të thotë çdo kod gabimi, shqip.
 *
 * Serveri i shkruan mesazhet anglisht, si çdo identifikues tjetër te ky projekt,
 * dhe deri tani ato dilnin të papërkthyera mes tekstit shqip — «the path does not
 * exist» ishte gjëja e parë që shihte dikush që shtypte një shteg të gabuar.
 * Kodi është pjesa e qëndrueshme e kontratës, ndaj përkthimi lidhet me të e jo me
 * fjalinë, e cila mund të ndryshojë pa paralajmërim.
 *
 * Teksti i thotë përdoruesit **çfarë të bëjë**, jo vetëm çfarë ndodhi. Një gabim
 * që e lë atë të pyesë «po tani?» nuk e ka kryer punën e vet.
 */
export const ERROR_SQ: Record<string, string> = {
  path_empty: "Shkruaj një shteg për të filluar.",
  root_missing: "Dosja e lejuar e serverit nuk ekziston. Kontrollo se si u nis serveri.",
  path_outside_root: "Ky shteg del jashtë dosjes që serveri e ka të lejuar.",
  path_not_found: "Nuk ka asgjë te ky shteg. Kontrollo shkrimin e tij.",
  too_many_files: "Tepër skedarë Java këtu. Zgjidh një nëndosje.",
  too_much_source: "Tepër kod burimi këtu. Zgjidh një nëndosje.",
  no_java_files: "Asnjë skedar Java te ky shteg.",
  not_a_file: "Kjo veprim kërkon një skedar të vetëm, jo një dosje.",
  bad_range: "Rangu i rreshtave mbaron para se të nisë.",
  unreadable: "Skedari nuk u lexua dot.",
  advisory_only: "Motori nuk e rishkruan vetë këtë erë; mbetet propozim.",
  not_found: "Asnjë entitet te ai rresht. Analiza mund të jetë e vjetruar; ri-ekzekutoje.",
};

async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  // Afati vlen gjithmonë; sinjali i thirrësit, kur ka, i shtohet atij.
  const deadline = AbortSignal.timeout(TIMEOUT_MS);
  const abort = signal ? AbortSignal.any([signal, deadline]) : deadline;

  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: abort,
    });
  } catch (failure) {
    if (signal?.aborted) throw new Cancelled("Analiza u ndal.");
    if ((failure as Error).name === "TimeoutError") {
      throw new Error(
        "Analiza zgjati më shumë se dy minuta dhe u ndal. Provo një shteg më të ngushtë.",
      );
    }
    throw new Error("Serveri nuk u arrit. A është i ndezur në portin 8000?");
  }

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const named = payload as ApiError | null;
    const code = named?.error?.code;
    if (code && ERROR_SQ[code]) throw new Error(ERROR_SQ[code]);
    // Një kod që kjo hartë nuk e njeh është gabim i ri te serveri. Mesazhi i tij
    // anglisht është më i mirë se heshtja, dhe testi e kap mungesën.
    if (named?.error?.message) throw new Error(named.error.message);
    // FastAPI's own validation failures have a different shape; the detail is
    // for a developer, not for this screen.
    if (response.status === 422) throw new Error("Kërkesa nuk është e vlefshme.");
    throw new Error(`Serveri ktheu ${response.status}.`);
  }

  return payload as T;
}

export function analyse(
  path: string,
  includeModel: boolean,
  signal?: AbortSignal,
): Promise<Analysis> {
  return post<Analysis>("/analyze", { path, include_model: includeModel }, signal);
}

/** Join the project path and the file path the analysis reported. */
function within(path: string, file: string): string {
  return file ? `${path.replace(/\/+$/, "")}/${file}` : path;
}

export function preview(path: string, smell: Smell): Promise<Preview> {
  return post<Preview>("/refactor/preview", {
    path: within(path, smell.file_path),
    class_name: smell.class_name,
    method: smell.method ? smell.method.replace(/\(.*$/, "") : null,
    start_line: smell.start_line,
    smell_type: smell.smell_type,
  });
}

/** Every safe rewrite under the analysed path, as one diff. Writes nothing. */
export function patch(path: string, signal?: AbortSignal): Promise<PatchResult> {
  return post<PatchResult>("/refactor/patch", { path }, signal);
}

export function source(path: string, smell: Smell): Promise<Source> {
  return post<Source>("/source", {
    path: within(path, smell.file_path),
    start_line: smell.start_line,
    end_line: smell.end_line,
  });
}
