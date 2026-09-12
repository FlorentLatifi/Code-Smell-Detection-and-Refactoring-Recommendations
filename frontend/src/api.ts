import type {
  Analysis,
  ApiError,
  PatchResult,
  ApplyResult,
  PatchProgress,
  Preview,
  RewriteNote,
  Smell,
  Source,
  TreeState,
} from "./types";

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

/**
 * Afati i veçantë i patch-it, sepse ai ka buxhetin e vet te serveri.
 *
 * `/refactor/patch` e ndalon vetë punën te `timeout_s`, 300 sekonda si
 * parazgjedhje, dhe kthen atë që arriti të planifikojë me numrin e skedarëve që
 * s'i mbërriti. Me afatin e përbashkët prej dy minutash shfletuesi e priste
 * lidhjen para se serveri ta mbaronte: një patch mbi 322 skedarë u mat 2 minuta
 * e 25 sekonda dhe do të dukej si dështim ndonëse serveri e kishte kryer. Afati
 * këtu rri mbi buxhetin e serverit, që ai të jetë i pari që dorëzohet dhe
 * përgjigja e pjesshme të mbërrijë (VD-96).
 */
const PATCH_TIMEOUT_MS = 330_000;

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

async function post<T>(
  path: string,
  body: unknown,
  signal?: AbortSignal,
  timeoutMs: number = TIMEOUT_MS,
): Promise<T> {
  // Afati vlen gjithmonë; sinjali i thirrësit, kur ka, i shtohet atij.
  const deadline = AbortSignal.timeout(timeoutMs);
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
/**
 * Përgatit patch-in, duke raportuar sa ka mbetur ndërsa punon.
 *
 * Rruga që përdoret është ajo me rrjedhë: serveri e kthen një objekt JSON për
 * rresht, një lexim pas çdo skedari dhe rezultatin te i fundit. Përgjigja e
 * vetme mbetet te `/refactor/patch` për këdo që e do atë formë, por ky ekran e
 * do tjetrën — një patch mbi 322 skedarë u mat dy minuta e gjysmë, dhe deri tani
 * e gjithë ajo kohë dukej njësoj si një mjet i ngecur (VD-98).
 *
 * Refuzimet e shtegut mbërrijnë ende si status jo-200 me kodin e vet, sepse
 * serveri i kontrollon para se ta hapë rrjedhën.
 */
export async function patch(
  path: string,
  signal?: AbortSignal,
  onProgress?: (progress: PatchProgress) => void,
): Promise<PatchResult> {
  const deadline = AbortSignal.timeout(PATCH_TIMEOUT_MS);
  const abort = signal ? AbortSignal.any([signal, deadline]) : deadline;

  let response: Response;
  try {
    response = await fetch("/api/refactor/patch/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
      signal: abort,
    });
  } catch (failure) {
    if (signal?.aborted) throw new Cancelled("Përgatitja u ndal.");
    if ((failure as Error).name === "TimeoutError") throw new Error(PATCH_TOO_LONG);
    throw new Error("Serveri nuk u arrit. A është i ndezur në portin 8000?");
  }

  if (!response.ok || !response.body) {
    await refuse(response);
  }

  let result: PatchResult | null = null;
  try {
    for await (const line of ndjson(response.body as ReadableStream<Uint8Array>)) {
      const message = JSON.parse(line) as { progress?: PatchProgress; result?: PatchResult };
      if (message.progress) onProgress?.(message.progress);
      if (message.result) result = message.result;
    }
  } catch (failure) {
    if (signal?.aborted) throw new Cancelled("Përgatitja u ndal.");
    if ((failure as Error).name === "TimeoutError") throw new Error(PATCH_TOO_LONG);
    throw failure;
  }

  // Rrjedha mbaroi pa rezultat do të thotë se serveri u këput në mes. Heshtja
  // këtu do ta linte ekranin te «Duke përgatitur…» përgjithmonë.
  if (result === null) throw new Error("Rrjedha mbaroi para se patch-i të mbërrinte.");
  return result;
}

const PATCH_TOO_LONG =
  "Përgatitja e patch-it zgjati më shumë se pesë minuta dhe u ndal. Provo një nëndosje.";

/**
 * Ndaje trupin e përgjigjes në rreshta JSON, sapo secili të mbërrijë.
 *
 * Një copë e lexuar nga rrjeti nuk përkon me një rresht: mund të mbajë gjysmë
 * objekti, ose tre e gjysmë. Mbajtësi e ruan bishtin e papërfunduar për copën
 * pasardhëse, dhe pa të një lexim i vetëm i ndarë keq do të prishte gjithçka pas
 * tij.
 */
async function* ndjson(body: ReadableStream<Uint8Array>): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let held = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    held += decoder.decode(value, { stream: true });
    const lines = held.split("\n");
    held = lines.pop() ?? "";
    for (const line of lines) {
      if (line.trim()) yield line;
    }
  }
  if (held.trim()) yield held;
}

/** E njëjta hartë kodesh si te `post`, për një përgjigje që s'u hap dot si rrjedhë. */
async function refuse(response: Response): Promise<never> {
  const payload = (await response.json().catch(() => null)) as ApiError | null;
  const code = payload?.error?.code;
  if (code && ERROR_SQ[code]) throw new Error(ERROR_SQ[code]);
  if (payload?.error?.message) throw new Error(payload.error.message);
  throw new Error(`Serveri ktheu ${response.status}.`);
}

export function source(path: string, smell: Smell): Promise<Source> {
  return post<Source>("/source", {
    path: within(path, smell.file_path),
    start_line: smell.start_line,
    end_line: smell.end_line,
  });
}

/**
 * Emri i dosjes brenda së cilës serveri lejon të lexohet.
 *
 * Vetëm emri, jo shtegu i plotë: serveri e kthen ashtu me qëllim (§6), dhe për
 * përdoruesin ai është informacioni që mungonte. Rrënja caktohet me një
 * ndryshore mjedisi kur niset serveri, ndaj dikush që e hap ndërfaqen nuk e di
 * dot ndryshe se ku lejohet të kërkojë, dhe e mësonte vetëm duke gabuar (VD-95).
 *
 * Dështimi kthen `null` e nuk hidhet: ky është tregues ndihmës, dhe një ekran që
 * nuk hapet dot sepse `/health` nuk u përgjigj do të ishte më keq se mungesa e tij.
 */
export async function allowedRoot(): Promise<string | null> {
  try {
    const response = await fetch("/api/health", { signal: AbortSignal.timeout(5_000) });
    if (!response.ok) return null;
    const body = (await response.json()) as { root?: unknown };
    return typeof body.root === "string" && body.root ? body.root : null;
  } catch {
    return null;
  }
}

/**
 * Çfarë thotë secili shënim i një rishkrimi, shqip.
 *
 * Lidhur me kodin e jo me fjalinë, për të njëjtën arsye si `ERROR_SQ`: kodi është
 * pjesa e qëndrueshme e kontratës. Një shënim pa përkthim shfaqet si kodi i vet,
 * çka është e shëmtuar por e sinqertë, dhe nuk e prish ekranin.
 */
export function noteText(note: RewriteNote): string {
  if (note.code === "wide_parameter_list") {
    return (
      `Metoda e nxjerrë merr ${note.parameters} parametra, mbi kufirin ${note.threshold} ` +
      "që ky mjet vetë e shënon si Long Parameter List. Një bllok që kërkon kaq hyrje " +
      "shpesh është prerja e gabuar për t'u ngritur."
    );
  }
  return note.code;
}

/**
 * Çfarë do të thotë secili refuzim i shkrimit, shqip.
 *
 * Lidhur me kodin si çdo gabim tjetër. Teksti i thotë përdoruesit çfarë të bëjë,
 * sepse çdo njëri prej këtyre refuzimeve ka një veprim që e zgjidh.
 */
export const APPLY_REFUSAL_SQ: Record<string, string> = {
  not_requested: "Shkrimi nuk u konfirmua.",
  not_a_repository:
    "Ky shteg nuk është brenda një depoje git. Motori shkruan vetëm aty ku një «git restore .» " +
    "mund ta kthejë gjithçka.",
  tree_not_clean:
    "Pema e punës ka ndryshime të paruajtura. Komito ose hidhi ato së pari, që kthimi të prekë " +
    "vetëm atë që shkruan mjeti.",
  nothing_to_write: "Asnjë rishkrim i verifikuar për t'u shkruar.",
  file_changed:
    "Një skedar ka ndryshuar që kur u mat. Ri-ekzekuto analizën, që rishkrimi të llogaritet mbi " +
    "atë që është në disk tani.",
};

/** A do të lejohej një shkrim te ky shteg, pa planifikuar ende asgjë. */
export function treeState(path: string): Promise<TreeState> {
  return post<TreeState>("/refactor/tree", { path });
}

/**
 * Shkruaj rishkrimet e verifikuara te skedarët.
 *
 * I vetmi funksion i këtij moduli që e ndryshon kodin e përdoruesit. `confirm`
 * dërgohet shprehimisht e nuk nënkuptohet, dhe afati është ai i patch-it sepse
 * puna është e njëjta: planifikimi mat me minuta.
 */
export async function applyPatch(path: string, signal?: AbortSignal): Promise<ApplyResult> {
  try {
    return await post<ApplyResult>(
      "/refactor/apply",
      { path, confirm: true },
      signal,
      PATCH_TIMEOUT_MS,
    );
  } catch (failure) {
    throw new Error(translateRefusal((failure as Error).message));
  }
}

/**
 * Refuzimet e shkrimit mbërrijnë si 409 me kodin e vet, të cilin `post` e lë të
 * pandryshuar sepse nuk është te `ERROR_SQ`. Përkthimi bëhet këtu, që harta e
 * gabimeve të përgjithshme të mos mbushet me kode që i takojnë një rruge të vetme.
 */
function translateRefusal(message: string): string {
  return APPLY_REFUSAL_SQ[message] ?? message;
}
