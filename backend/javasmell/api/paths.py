"""Confining a user-supplied path to the directory the server is allowed to read.

The application binds to localhost and has one user, so the risks worth
defending against are not authentication but path handling and resource use
(ENGINEERING.md §6). An analysis path arrives as a string from an HTTP request,
and the only thing standing between that string and the whole filesystem is this
module.

Three separate things have to hold, and each is checked rather than assumed:

* the path resolves inside the allowed root, after ``..`` and ``.`` are collapsed;
* it resolves there *after symlinks are followed*, because a link inside the root
  can point anywhere;
* it exists and is the kind of thing the caller asked for.

Resolution comes first and comparison second. Comparing the string before
resolving is the classic mistake: ``/allowed/../etc/passwd`` starts with the
allowed prefix and is not inside it.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

#: Sa skedarë shihen para se kërkimi i një `.java` të ndalet e të thotë «nuk e
#: dita». Shfletimi i dosjeve ndodh ndërsa përdoruesi pret, ndaj ai nuk guxon të
#: ecë një dru të tërë vetëm për të zbehur një rresht të listës.
JAVA_PROBE_FILES = 4_000

#: Sa nënndosje kthen një shfletim. Një dosje me mijëra nënndosje nuk lexohet
#: dot as në ekran, dhe lista e plotë do të ishte vetëm ngarkesë.
MAX_FOLDERS = 500


class PathRejected(Exception):
    """The path is outside the allowed root, or is not usable.

    The message is safe to show a caller: it never contains a resolved absolute
    path, because echoing one back tells an attacker where the root is and
    confirms what exists outside it.

    ``code`` names *which* rejection this is. All seven used to arrive at the
    caller under one code, which meant an interface could not tell "you typed
    nothing" from "that tree is too large" without matching on English prose.
    A caller that has to parse a message to know what happened does not have a
    contract, it has a guess.
    """

    def __init__(self, message: str, code: str = "path_rejected") -> None:
        super().__init__(message)
        self.code = code


def _resolved(path: Path) -> Path:
    """Absolute, with ``..`` collapsed and every symlink followed."""
    return path.resolve(strict=False)


def allowed_roots(roots: Path | Sequence[Path]) -> tuple[Path, ...]:
    """Të gjitha rrënjët që ekzistojnë vërtet, të zgjidhura dhe pa dublikate.

    Një rrënjë e dytë u shtua kur ndërfaqja mori importin nga GitHub: depot e
    shkarkuara nuk rrinë brenda dosjes që zgjodhi përdoruesi, ndaj analiza duhet
    të lexojë edhe atje (VD-126). Një rrënjë e konfiguruar që nuk ekziston nuk e
    ndal shërbimin; ajo thjesht nuk hyn mes të lejuarave, sepse dosja e depove
    krijohet vetëm kur importohet e para.
    """
    candidates = [roots] if isinstance(roots, Path) else list(roots)
    found: list[Path] = []
    for candidate in candidates:
        resolved = _resolved(candidate)
        if resolved.is_dir() and resolved not in found:
            found.append(resolved)
    return tuple(found)


def confine(candidate: str, roots: Path | Sequence[Path]) -> Path:
    """The path ``candidate`` names inside one of ``roots``, or raise.

    ``candidate`` may be absolute or relative; either way it must land inside an
    allowed root. A relative path is taken as relative to a root rather than to
    the process's working directory, which is not something an HTTP caller can
    see or reason about; the roots are tried in order, so the first one wins a
    name that exists in two of them.
    """
    if not candidate or not candidate.strip():
        raise PathRejected("the path is empty", "path_empty")

    allowed = allowed_roots(roots)
    if not allowed:
        raise PathRejected("the configured root is not a directory", "root_missing")

    requested = Path(candidate)
    inside: Path | None = None
    for root in allowed:
        joined = requested if requested.is_absolute() else root / requested
        target = _resolved(joined)
        # Resolution has already followed every symlink, so this single check
        # covers both `..` traversal and a link pointing out of the root.
        if target != root and root not in target.parents:
            continue
        if target.exists():
            return target
        # Brenda një rrënje por i paqenë: mbahet, që mesazhi të thotë «nuk
        # ekziston» në vend që «jashtë dosjes», sepse të dyja ndreqen ndryshe.
        inside = inside or target

    if inside is None:
        # The folder's *name*, never its absolute path. Without it the caller is
        # told the path is wrong and given nothing to correct it with, which on
        # a tool whose root is set by an environment variable is most of the
        # error's usefulness (VD-95). The name alone tells an attacker nothing
        # they could not learn by trying one path.
        names = ", ".join(repr(root.name) for root in allowed)
        one = len(allowed) == 1
        which = "directory, which is" if one else "directories, which are"
        raise PathRejected(
            f"the path is outside the allowed {which} {names}",
            "path_outside_root",
        )

    raise PathRejected("the path does not exist", "path_not_found")


@dataclass(frozen=True)
class Folder:
    """Një nënndosje, ashtu si e shfaq lista e zgjedhjes.

    ``java`` është ``None`` kur kërkimi u ndal te kufiri, e jo kur dosja është
    bosh. Dallimi mbahet, sepse «nuk ka kod Java» dhe «nuk e dita» i thonë
    përdoruesit dy gjëra të kundërta.
    """

    name: str
    path: str
    java: bool | None


def contains_java(directory: Path, *, limit: int = JAVA_PROBE_FILES) -> bool | None:
    """A ka kod Java brenda kësaj dosjeje, pa e ecur tërë drurin.

    Kërkimi ndalet te skedari i parë `.java`, ndaj rasti i mirë është i shpejtë;
    rasti i keq, një dru i madh pa asnjë `.java`, ndalet te kufiri dhe kthen
    ``None``. Pa kufi, shfletimi i dosjes së përdoruesit mund të zgjatur minuta
    për një rresht liste.
    """
    seen = 0
    for _, _, files in os.walk(directory):
        for name in files:
            if name.endswith(".java"):
                return True
            seen += 1
            if seen > limit:
                return None
    return False


def subfolders(target: Path, *, limit: int = MAX_FOLDERS) -> list[Folder]:
    """Nënndosjet e ``target``, të renditura, me shënimin nëse mbajnë Java.

    Dosjet e fshehura nuk listohen: nuk ka kod Java për analizë brenda
    ``.git``, dhe një listë ku ato zënë rreshtat e para është listë që
    përdoruesi duhet ta kalojë me sy para se të gjejë projektin e vet. Lidhjet
    simbolike lihen jashtë sepse ato mund të çojnë kudo, dhe një shteg që del
    nga rrënja refuzohet gjithsesi te `confine`.
    """
    if not target.is_dir():
        raise PathRejected("the path is not a directory", "path_not_directory")

    found: list[Folder] = []
    for entry in sorted(target.iterdir(), key=lambda path: path.name.lower()):
        if len(found) >= limit:
            break
        if entry.name.startswith(".") or not entry.is_dir() or entry.is_symlink():
            continue
        found.append(Folder(entry.name, str(entry), contains_java(entry)))
    return found


def java_files_under(target: Path, *, max_files: int, max_bytes: int) -> list[Path]:
    """Every ``.java`` file at or under ``target``, refusing an oversized tree.

    The caps exist because a single request must not be able to occupy the
    server indefinitely. Both are checked while walking rather than afterwards:
    counting the whole tree first would already have done the expensive work.
    """
    if target.is_file():
        files = [target] if target.suffix == ".java" else []
    else:
        files = []
        total = 0
        for path in sorted(target.rglob("*.java")):
            if not path.is_file():
                continue
            files.append(path)
            if len(files) > max_files:
                raise PathRejected(
                    f"more than {max_files} Java files; narrow the path", "too_many_files"
                )
            total += path.stat().st_size
            if total > max_bytes:
                raise PathRejected(
                    f"more than {max_bytes // 1_000_000} MB of source; narrow the path",
                    "too_much_source",
                )

    if not files:
        raise PathRejected("no Java files found at that path", "no_java_files")
    return files
