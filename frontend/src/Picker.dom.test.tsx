// @vitest-environment jsdom
//
// Testet e zgjedhjes së projektit: dosje me klikim, ose depo nga GitHub.
//
// Secili test i përgjigjet një hapi të rrugës që dikush ndjek vërtet, sepse
// pikërisht kjo rrugë u shtua për t'i hequr shtypjen e shtegut me dorë
// (VD-126): hapja te rrënjët, hyrja brenda një dosjeje, kthimi lart, zgjedhja,
// dhe shkarkimi i një depoje nga një lidhje.

import axe from "axe-core";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Picker } from "./Picker";
import type { Listing } from "./types";

const ROOTS: Listing = {
  path: "",
  name: "",
  parent: null,
  folders: [
    { name: "workspace", path: "C:/kodi/workspace", java: true },
    { name: "projects", path: "C:/kodi/projects", java: true },
  ],
  roots: [
    { name: "workspace", path: "C:/kodi/workspace" },
    { name: "projects", path: "C:/kodi/projects" },
  ],
};

/** E njëjta listë kur serveri lexon vetëm nga një dosje. */
const ONE_ROOT: Listing = {
  ...ROOTS,
  folders: [ROOTS.folders[0]],
  roots: [ROOTS.roots[0]],
};

const WORKSPACE: Listing = {
  path: "C:/kodi/workspace",
  name: "workspace",
  parent: null,
  folders: [
    { name: "jsoup", path: "C:/kodi/workspace/jsoup", java: true },
    { name: "shenime", path: "C:/kodi/workspace/shenime", java: false },
    { name: "arkiva", path: "C:/kodi/workspace/arkiva", java: null },
  ],
  roots: ROOTS.roots,
};

const JSOUP: Listing = {
  path: "C:/kodi/workspace/jsoup",
  name: "jsoup",
  parent: "C:/kodi/workspace",
  folders: [],
  roots: ROOTS.roots,
};

const LISTINGS: Record<string, Listing> = {
  "": ROOTS,
  "C:/kodi/workspace": WORKSPACE,
  "C:/kodi/workspace/jsoup": JSOUP,
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Serveri i shfletimit, plus çfarëdo përgjigje për importin. */
function serve(options: { importResponse?: () => Response; roots?: Listing } = {}): void {
  const { importResponse, roots } = options;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, string>) : {};
      if (String(url).endsWith("/browse")) {
        const path = body.path ?? "";
        const listing = path === "" && roots ? roots : LISTINGS[path];
        if (!listing) {
          return json({ error: { code: "path_not_found", message: "x" } }, 400);
        }
        return json(listing);
      }
      if (String(url).endsWith("/projects/github")) {
        return importResponse ? importResponse() : json({ error: { code: "x" } }, 500);
      }
      return json({ error: { code: "not_found", message: "x" } }, 404);
    }),
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function open(onChoose = vi.fn()): { onChoose: ReturnType<typeof vi.fn> } {
  render(<Picker open recent={[]} onChoose={onChoose} onClose={vi.fn()} />);
  return { onChoose };
}

describe("zgjedhja e dosjes", () => {
  it("hapet te rrënjët kur serveri lexon nga më shumë se një dosje", async () => {
    serve();
    open();

    expect(await screen.findByRole("button", { name: /workspace/ })).toBeDefined();
    expect(screen.getByRole("button", { name: /projects/ })).toBeDefined();
    expect(screen.getByText("Dosjet që serveri i lexon")).toBeDefined();
    // Te rrënjët nuk ka çfarë të analizohet: butoni pret një dosje.
    expect(screen.getByRole("button", { name: "Analizo këtë dosje" })).toHaveProperty(
      "disabled",
      true,
    );
  });

  it("me një rrënjë të vetme hyn drejt brenda saj", async () => {
    // Një listë me një rresht të vetëm do të ishte klikim i tepërt para se puna
    // të nisë, ndaj dialogu e kalon atë hap vetë.
    serve({ roots: ONE_ROOT });
    open();

    expect(await screen.findByRole("button", { name: /jsoup/ })).toBeDefined();
    expect(screen.getByRole("button", { name: "Analizo këtë dosje" })).toHaveProperty(
      "disabled",
      false,
    );
  });

  it("hyn brenda një dosjeje dhe e shënon atë që mban kod Java", async () => {
    serve();
    open();

    fireEvent.click(await screen.findByRole("button", { name: /workspace/ }));

    const jsoup = await screen.findByRole("button", { name: /jsoup/ });
    expect(jsoup.textContent).toContain("Java");
    // Tri gjendje e jo dy: dosja e madhe nuk duhet të dukej si dosje pa kod.
    expect((await screen.findByRole("button", { name: /shenime/ })).textContent).toContain(
      "pa Java",
    );
    expect((await screen.findByRole("button", { name: /arkiva/ })).textContent).toContain(
      "e madhe",
    );
  });

  it("e kthen shtegun e dosjes ku ndodhet, e jo emrin e saj", async () => {
    serve();
    const { onChoose } = open();

    fireEvent.click(await screen.findByRole("button", { name: /workspace/ }));
    fireEvent.click(await screen.findByRole("button", { name: /jsoup/ }));
    fireEvent.click(await screen.findByText("C:/kodi/workspace/jsoup"));
    fireEvent.click(screen.getByRole("button", { name: "Analizo këtë dosje" }));

    expect(onChoose).toHaveBeenCalledWith("C:/kodi/workspace/jsoup");
  });

  it("kthehet lart, dhe nga rrënja te lista e rrënjëve", async () => {
    serve();
    open();

    fireEvent.click(await screen.findByRole("button", { name: /workspace/ }));
    fireEvent.click(await screen.findByRole("button", { name: /jsoup/ }));
    // Nga `jsoup` te `workspace`, ku rreshtat e dosjeve dalin sërish.
    fireEvent.click(await screen.findByRole("button", { name: "↑ Lart" }));
    expect(await screen.findByRole("button", { name: /shenime/ })).toBeDefined();

    // Nga rrënja, «lart» çon te lista e rrënjëve e jo jashtë saj: përtej tyre
    // serveri nuk lexon, ndaj nuk ka hap tjetër për të ofruar.
    fireEvent.click(screen.getByRole("button", { name: "↑ Lart" }));

    expect(await screen.findByText("Dosjet që serveri i lexon")).toBeDefined();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Rrënjët" })).toHaveProperty("disabled", true),
    );
  });

  it("një refuzim i serverit del shqip dhe jo si kod", async () => {
    serve();
    render(<Picker open recent={["C:/mungon"]} onChoose={vi.fn()} onClose={vi.fn()} />);

    // Shtegu i kujtuar nuk ekziston më; shfletimi i tij refuzohet.
    fireEvent.click(await screen.findByRole("button", { name: /workspace/ }));
    await screen.findByRole("button", { name: /jsoup/ });

    LISTINGS["C:/kodi/workspace/jsoup"] = undefined as unknown as Listing;
    fireEvent.click(screen.getByRole("button", { name: /jsoup/ }));

    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      "Nuk ka asgjë te ky shteg. Kontrollo shkrimin e tij.",
    );
    LISTINGS["C:/kodi/workspace/jsoup"] = JSOUP;
  });

  it("një shteg i hapur së fundi zgjidhet me një klikim", async () => {
    serve();
    const onChoose = vi.fn();
    render(
      <Picker open recent={["C:/kodi/workspace/jsoup"]} onChoose={onChoose} onClose={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "workspace/jsoup" }));

    expect(onChoose).toHaveBeenCalledWith("C:/kodi/workspace/jsoup");
  });

  it("Escape e mbyll dialogun", async () => {
    serve();
    const onClose = vi.fn();
    render(<Picker open recent={[]} onChoose={vi.fn()} onClose={onClose} />);

    fireEvent.keyDown(window, { key: "Escape" });

    expect(onClose).toHaveBeenCalled();
  });
});

describe("importi nga GitHub", () => {
  function toGithub(): void {
    fireEvent.click(screen.getByRole("tab", { name: /Nga GitHub/ }));
  }

  it("shkarkon depon dhe kthen shtegun ku u shkrua", async () => {
    serve({
      importResponse: () =>
        json({
          path: "C:/kodi/data/projects/jhy__jsoup",
          name: "jhy__jsoup",
          repository: "jhy/jsoup",
          java_files: 288,
          cached: false,
        }),
    });
    const { onChoose } = open();
    toGithub();

    fireEvent.change(screen.getByLabelText("Lidhja e një depoje publike"), {
      target: { value: "https://github.com/jhy/jsoup" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Shkarko dhe analizo/ }));

    await waitFor(() => expect(onChoose).toHaveBeenCalledWith("C:/kodi/data/projects/jhy__jsoup"));
  });

  it("nuk kërkon gjë derisa lidhja të jetë shkruar", () => {
    serve();
    open();
    toGithub();

    expect(screen.getByRole("button", { name: /Shkarko dhe analizo/ })).toHaveProperty(
      "disabled",
      true,
    );
  });

  it("një lidhje që nuk është GitHub del shqip", async () => {
    serve({
      importResponse: () => json({ error: { code: "not_github", message: "only github" } }, 400),
    });
    open();
    toGithub();

    fireEvent.change(screen.getByLabelText("Lidhja e një depoje publike"), {
      target: { value: "https://gitlab.com/a/b" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Shkarko dhe analizo/ }));

    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      "Për tani importohen vetëm depo nga github.com.",
    );
  });

  it("e thotë se kodi nuk ekzekutohet, para se dikush të shkarkojë", () => {
    serve();
    open();
    toGithub();

    expect(screen.getByText(/nuk ekzekutohet kurrë/)).toBeDefined();
  });
});

describe("rishkarkimi dhe aksesueshmëria (VD-127)", () => {
  it("rishkarkimi dërgohet vetëm kur kërkohet", async () => {
    serve({
      importResponse: () =>
        json({
          path: "C:/p/jhy__jsoup",
          name: "jhy__jsoup",
          repository: "jhy/jsoup",
          java_files: 1,
          cached: false,
        }),
    });
    const { onChoose } = open();
    toGithubTab();
    fireEvent.change(screen.getByLabelText("Lidhja e një depoje publike"), {
      target: { value: "jhy/jsoup" },
    });
    fireEvent.click(
      screen.getByLabelText("Shkarko versionin më të ri, edhe nëse depoja është importuar më parë"),
    );
    fireEvent.click(screen.getByRole("button", { name: /Shkarko dhe analizo/ }));
    await waitFor(() => expect(onChoose).toHaveBeenCalled());

    const calls = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls;
    const sent = calls.find(([url]) => String(url).endsWith("/projects/github"));
    expect(JSON.parse(String((sent?.[1] as RequestInit).body))).toEqual({
      url: "jhy/jsoup",
      refresh: true,
    });
  });

  it("Tab-i nga elementi i fundit kthehet brenda dialogut", async () => {
    serve();
    open();
    await screen.findByRole("button", { name: /workspace/ });

    const dialog = screen.getByRole("dialog");
    const focusable = Array.from(dialog.querySelectorAll<HTMLElement>("button:not([disabled])"));
    focusable[focusable.length - 1].focus();
    fireEvent.keyDown(window, { key: "Tab" });

    expect(document.activeElement).toBe(focusable[0]);
  });

  it("pas mbylljes fokusi kthehet te butoni që e hapi", () => {
    serve();
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();

    const { rerender } = render(<Picker open recent={[]} onChoose={vi.fn()} onClose={vi.fn()} />);
    rerender(<Picker open={false} recent={[]} onChoose={vi.fn()} onClose={vi.fn()} />);

    expect(document.activeElement).toBe(opener);
    opener.remove();
  });

  it("axe nuk gjen shkelje në asnjërën nga dy skedat", async () => {
    serve();
    const { container } = render(
      <Picker open recent={["C:/kodi/workspace/jsoup"]} onChoose={vi.fn()} onClose={vi.fn()} />,
    );
    await screen.findByRole("button", { name: /workspace/ });
    expect(await violations(container)).toEqual([]);

    toGithubTab();
    expect(await violations(container)).toEqual([]);
  });
});

function toGithubTab(): void {
  fireEvent.click(screen.getByRole("tab", { name: /Nga GitHub/ }));
}

/** Vetëm shkeljet, me të njëjtat rregulla të fikura si te `a11y.dom.test.tsx`. */
async function violations(container: HTMLElement): Promise<string[]> {
  const result = await axe.run(container, {
    rules: { "color-contrast": { enabled: false }, region: { enabled: false } },
  });
  return result.violations.map((v) => `${v.id}: ${v.nodes.length} — ${v.help}`);
}
