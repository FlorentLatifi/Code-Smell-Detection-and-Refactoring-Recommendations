"""Fetching a public GitHub repository so it can be analysed without a checkout.

The interface used to require that the code already sat inside the allowed
directory, which meant cloning a repository by hand before the tool could say
anything about it. That is a step a developer trying the tool has no reason to
take on trust (VD-126).

**The archive, not ``git clone``.** ``codeload.github.com`` serves a tarball of
one ref, which is one HTTPS request, needs no git on the machine, and carries no
history -- the analysis reads a snapshot, so a clone would download the past for
nothing. This is the same route ``scripts/fetch_corpus.py`` takes for the MLCQ
corpus, and for the same reasons.

**Only ``.java`` members are written**, which is what the analysis reads and a
small fraction of what an archive holds. It also bounds the damage a hostile
archive can do: a member is attacker-controlled input, so each destination is
resolved and checked to be inside the target directory before anything is
written, every member has a size ceiling, and the archive has one of its own.

**What this deliberately does not do.** It does not run anything from the
repository, it does not follow archive symlinks, and it does not fetch private
repositories: a URL that needs credentials is refused rather than prompted for,
because a tool that asks for a token to read a repository is a tool asking for
more trust than it needs.
"""

from __future__ import annotations

import re
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from javasmell.filesystem import long_path

USER_AGENT = "javasmell (UBT bachelor project; contact via repository)"
CODELOAD = "https://codeload.github.com/{owner}/{name}/tar.gz/{ref}"

#: Kur nuk jepet degë, merret koka e degës së parazgjedhur. Pa këtë, importi do
#: të kërkonte nga përdoruesi t'i dinte emrin e degës — «main» apo «master» —
#: që është pikërisht hollësia që ky import synon ta heqë.
DEFAULT_REF = "HEAD"

GITHUB_HOSTS = {"github.com", "www.github.com"}

#: Emrat e pronarit dhe të depos, sipas asaj që lejon GitHub-u.
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
#: Degë, etiketë ose commit. Pa «..», që një ref të mos ndërtojë shteg tjetër.
REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")

# Kufijtë. Çdo hap që prek rrjetin ose diskun ka tavan, sepse një kërkesë e
# vetme HTTP nuk guxon të zërë serverin pa fund (ENGINEERING.md §6).
DEFAULT_TIMEOUT_S = 120
MAX_ARCHIVE_MB = 400
MAX_JAVA_FILE_MB = 4
MAX_JAVA_FILES = 20_000
CHUNK = 1 << 16

#: Ndarësi mes pronarit dhe emrit te dosja, dy nënvija: një depo mund të mbajë
#: vizë në emër, ndaj një ndarës me një shenjë do t'i bashkonte dy emra të
#: ndryshëm te i njëjti shteg.
SEPARATOR = "__"

Opener = Callable[[urllib.request.Request], IO[bytes]]


class ImportRejected(Exception):
    """Depoja nuk u importua, dhe ``code`` thotë saktësisht pse.

    Kodet janë kontratë me ndërfaqen, si te refuzimet e shtegut: ajo i përkthen
    në shqip një nga një, ndaj një kod i ri pa përkthim del anglisht mes tekstit
    shqip dhe duket menjëherë.
    """

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Repository:
    """Një depo publike, ashtu si e emërton URL-ja."""

    owner: str
    name: str
    ref: str = DEFAULT_REF

    @property
    def directory(self) -> str:
        """Emri i dosjes ku zbret depoja, i lexueshëm dhe i pangatërrueshëm."""
        parts = [self.owner, self.name]
        if self.ref != DEFAULT_REF:
            parts.append(self.ref.replace("/", "-"))
        return SEPARATOR.join(parts)

    @property
    def label(self) -> str:
        at = "" if self.ref == DEFAULT_REF else f"@{self.ref}"
        return f"{self.owner}/{self.name}{at}"


@dataclass(frozen=True)
class Imported:
    """Ç'u shkrua në disk, që ndërfaqja të thotë çfarë mori."""

    repository: Repository
    path: Path
    java_files: int
    bytes_written: int


def parse(url: str) -> Repository:
    """Depoja që një lidhje emërton, ose një refuzim që thotë pse jo.

    Pranohen format që një përdorues kopjon vërtet: lidhja e faqes, e njëjta me
    «.git», lidhja e një dege te «/tree/», forma «git@github.com:owner/repo.git»
    që përdor edhe MLCQ, dhe thjesht «owner/repo».
    """
    text = url.strip()
    if not text:
        raise ImportRejected("the link is empty", "link_empty")

    # Forma SSH nuk është URL me skemë, ndaj kthehet te rruga e njohur para se të
    # provohet ndarja normale.
    ssh = re.match(r"^git@([^:]+):(.+)$", text)
    if ssh:
        host, path = ssh.groups()
        return _from_parts(host, path, "")

    if "://" not in text:
        text = f"https://github.com/{text.lstrip('/')}"

    parsed = urllib.parse.urlsplit(text)
    if parsed.scheme not in {"http", "https"}:
        raise ImportRejected("only https links are accepted", "bad_scheme")
    if parsed.username or parsed.password:
        # Një lidhje me kredenciale është depo private, dhe ky import lexon
        # vetëm publiket: më mirë refuzim i qartë se një 404 i pashpjegueshëm.
        raise ImportRejected("a link with credentials is not accepted", "credentials_in_link")
    return _from_parts(parsed.hostname or "", parsed.path, parsed.fragment)


def _from_parts(host: str, path: str, fragment: str) -> Repository:
    if host.lower() not in GITHUB_HOSTS:
        raise ImportRejected("only github.com links are accepted", "not_github")

    segments = [segment for segment in path.split("/") if segment]
    if len(segments) < 2:
        raise ImportRejected("the link does not name a repository", "no_repository")

    owner, name = segments[0], segments[1]
    if name.endswith(".git"):
        name = name[: -len(".git")]
    if not NAME.match(owner) or not NAME.match(name):
        raise ImportRejected("the owner or repository name is not usable", "bad_repository")

    ref = DEFAULT_REF
    if len(segments) > 3 and segments[2] in {"tree", "commit"}:
        # Çdo gjë pas «/tree/» merret si ref. Një degë me vija të pjerrëta dhe një
        # shteg brenda depos nuk dallohen dot nga lidhja, ndaj ref-i i gabuar del
        # si «nuk u gjet» dhe thuhet si i tillë, e nuk hamendësohet.
        ref = "/".join(segments[3:])
        if fragment:
            raise ImportRejected("the link points inside a file, not at a repository", "bad_ref")
        if not REF.match(ref) or ".." in ref:
            raise ImportRejected("the branch or commit is not usable", "bad_ref")

    return Repository(owner=owner, name=name, ref=ref)


def _download(url: str, target: Path, timeout_s: int, opener: Opener) -> None:
    """Rrjedh arkivin te disku, dhe refuzon kudo ku ai e kalon tavanin."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    limit = MAX_ARCHIVE_MB * 1024 * 1024
    written = 0
    try:
        with opener(request) as response, target.open("wb") as out:
            while chunk := response.read(CHUNK):
                written += len(chunk)
                if written > limit:
                    raise ImportRejected(
                        f"the repository archive is larger than {MAX_ARCHIVE_MB} MB",
                        "archive_too_large",
                    )
                out.write(chunk)
    except urllib.error.HTTPError as failure:
        if failure.code == 404:
            raise ImportRejected(
                "no public repository or branch under that link", "repository_not_found"
            ) from failure
        if failure.code in {403, 429}:
            raise ImportRejected(
                "GitHub refused the request; try again later", "rate_limited"
            ) from failure
        raise ImportRejected(f"GitHub answered with HTTP {failure.code}", "http_error") from failure
    except TimeoutError as failure:
        raise ImportRejected("the download timed out", "timeout") from failure
    except OSError as failure:
        # Deliberately broad, as in the corpus fetcher: a connection reset while
        # the body streams is a plain OSError, not a URLError.
        raise ImportRejected("the download did not finish", "network") from failure


def extract_java(archive: Path, destination: Path) -> tuple[int, int]:
    """Shpaketon vetëm anëtarët ``.java``, dhe vetëm nën ``destination``.

    Anëtarët e një arkivi janë hyrje e kontrolluar nga jashtë, ndaj çdo shteg
    zgjidhet dhe kontrollohet se bie brenda dosjes së synuar para se të shkruhet
    gjë: ekuivalenti me tar i «zip-slip». Arkivat e GitHub-ut e mbështjellin
    gjithçka te një dosje ``{emri}-{sha}/``, e cila hiqet, që shtigjet të dalin
    relative ndaj depos.
    """
    if destination.exists():
        shutil.rmtree(long_path(destination), ignore_errors=True)
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    count = 0
    total = 0
    size_cap = MAX_JAVA_FILE_MB * 1024 * 1024

    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith(".java"):
                continue
            if member.size > size_cap:
                continue
            _, _, relative = member.name.partition("/")  # heq {emri}-{sha}/
            if not relative:
                continue
            target = (destination / relative).resolve()
            if not target.is_relative_to(root):
                continue  # përpjekje për të dalë nga dosja, ose anëtar i lidhur
            source = tar.extractfile(member)
            if source is None:
                continue
            writable = long_path(target)
            writable.parent.mkdir(parents=True, exist_ok=True)
            with writable.open("wb") as out:
                shutil.copyfileobj(source, out)
            count += 1
            total += member.size
            if count > MAX_JAVA_FILES:
                raise ImportRejected(
                    f"the repository holds more than {MAX_JAVA_FILES} Java files",
                    "too_many_java_files",
                )
    return count, total


def fetch(
    repository: Repository,
    into: Path,
    *,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    opener: Opener | None = None,
) -> Imported:
    """Shkarkon dhe shpaketon një depo te ``into``, ose refuzon me arsye.

    ``opener`` injektohet që testet të mos varen nga rrjeti: ai është i vetmi
    hap që dikush tjetër duhet t'i zëvendësojë, dhe pjesa tjetër — kontrolli i
    shtegut, kufijtë, numërimi — ekzekutohet e vërteta.
    """
    destination = into / repository.directory
    url = CODELOAD.format(owner=repository.owner, name=repository.name, ref=repository.ref)
    actual = opener or (lambda request: urllib.request.urlopen(request, timeout=timeout_s))

    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "repo.tar.gz"
        _download(url, archive, timeout_s, actual)
        try:
            count, total = extract_java(archive, destination)
        except tarfile.TarError as failure:
            shutil.rmtree(long_path(destination), ignore_errors=True)
            raise ImportRejected(
                "the downloaded archive is not readable", "archive_broken"
            ) from failure

    if count == 0:
        # Një dosje bosh do të kalonte te analiza dhe do të refuzohej atje me
        # «asnjë skedar Java»; hiqet, që një provë e dytë të nisë nga pastër.
        shutil.rmtree(long_path(destination), ignore_errors=True)
        raise ImportRejected("the repository holds no Java files", "no_java_files")

    return Imported(repository=repository, path=destination, java_files=count, bytes_written=total)
