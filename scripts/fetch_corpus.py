"""Materialise the MLCQ corpus: one source tree per reviewed repository.

MLCQ publishes labels, not code: each sample points at a GitHub repository, a
commit and a line range. This script fetches the tree at that exact commit and
keeps only the ``.java`` files, which is what the analysis needs and a small
fraction of what the archive contains.

Whole repositories rather than single files, deliberately. ATFD, DIT, NOC and
CBO are all defined against the *project's* types, so a one-file "project"
would report almost no foreign data access, God Class and Feature Envy would
essentially never fire, and the measured recall would describe the corpus
instead of the detectors. See docs/DECISIONS.md, VD-16.

    python scripts/fetch_corpus.py --limit 5        # try it on a few first
    python scripts/fetch_corpus.py                  # the whole corpus

Safe to interrupt and re-run: completed repositories are skipped, failures are
retried, and the manifest is written after every repository.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from javasmell.evaluation.corpus import (  # noqa: E402
    Corpus,
    Manifest,
    RepoStatus,
    long_path,
    repo_dirname,
)
from javasmell.evaluation.mlcq import Sample, load_samples  # noqa: E402

DEFAULT_MLCQ = Path("data/raw/MLCQCodeSmellSamples.csv")
DEFAULT_OUT = Path("data/corpus")

USER_AGENT = "javasmell-thesis (UBT bachelor project; contact via repository)"
CODELOAD = "https://codeload.github.com/{owner}/{name}/tar.gz/{commit}"

# Resource limits. A corpus fetch runs unattended for hours, so every step that
# talks to the network or the filesystem gets a ceiling.
DOWNLOAD_TIMEOUT_S = 300
MAX_ARCHIVE_MB = 900
MAX_JAVA_FILE_MB = 4
CHUNK = 1 << 16
PAUSE_BETWEEN_REPOS_S = 0.5  # courtesy to a free service we depend on


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mlcq", type=Path, default=DEFAULT_MLCQ)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--limit", type=int, help="Only process this many repositories (for a trial run)"
    )
    parser.add_argument(
        "--timeout", type=int, default=DOWNLOAD_TIMEOUT_S, help="Per-repository seconds"
    )
    parser.add_argument(
        "--max-archive-mb", type=int, default=MAX_ARCHIVE_MB, help="Skip archives larger than this"
    )
    return parser


def _download(url: str, target: Path, timeout: int, max_mb: int) -> int:
    """Stream one archive to disk, refusing anything past the size ceiling."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    limit = max_mb * 1024 * 1024
    written = 0
    with urllib.request.urlopen(request, timeout=timeout) as response, target.open("wb") as out:
        while chunk := response.read(CHUNK):
            written += len(chunk)
            if written > limit:
                raise ValueError(f"archive exceeds {max_mb} MB")
            out.write(chunk)
    return written


def _extract_java(archive: Path, destination: Path) -> tuple[int, int]:
    """Unpack only the ``.java`` members, and only below ``destination``.

    Archive members are attacker-controlled input in the general case, so each
    destination is resolved and checked to be inside the target directory
    before anything is written: the tar equivalent of zip-slip. GitHub's
    archives also wrap everything in a ``{name}-{sha}/`` directory, which is
    stripped so that paths line up with the repository-relative paths MLCQ
    publishes.
    """
    # A previous attempt may have stopped part way through; starting from a
    # clean directory keeps a half-extracted tree from being counted as whole.
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
            _, _, relative = member.name.partition("/")  # strip {name}-{sha}/
            if not relative:
                continue
            target = (destination / relative).resolve()
            if not target.is_relative_to(root):
                continue  # path traversal attempt, or a symlinked member
            source = tar.extractfile(member)
            if source is None:
                continue
            writable = long_path(target)
            writable.parent.mkdir(parents=True, exist_ok=True)
            with writable.open("wb") as out:
                shutil.copyfileobj(source, out)
            count += 1
            total += member.size
    return count, total


def fetch_one(sample: Sample, out_root: Path, timeout: int, max_mb: int) -> RepoStatus:
    owner, name = sample.owner_and_name
    directory = out_root / repo_dirname(sample)
    url = CODELOAD.format(owner=owner, name=name, commit=sample.commit_hash)
    status = RepoStatus(
        repository=sample.repository,
        commit_hash=sample.commit_hash,
        directory=directory.name,
        ok=False,
    )

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "repo.tar.gz"
        try:
            _download(url, archive, timeout, max_mb)
        except urllib.error.HTTPError as exc:
            status.reason = f"HTTP {exc.code}"  # 404: repository or commit is gone
            return status
        except ValueError as exc:
            status.reason = str(exc)
            return status
        except OSError as exc:
            # Deliberately broad. `URLError` only wraps what goes wrong before
            # the response arrives; a connection reset *while streaming the
            # body* surfaces as a plain ConnectionResetError, which is what
            # ended a 133-repository run. Every one of these is transient and
            # is retried on the next run, since the manifest records the
            # repository as not done.
            status.reason = f"download: {exc.__class__.__name__}"
            return status

        try:
            count, total = _extract_java(archive, directory)
        except (tarfile.TarError, OSError) as exc:
            status.reason = f"archive: {exc.__class__.__name__}"
            return status

    if count == 0:
        status.reason = "no .java files in the archive"
        return status

    status.ok = True
    status.java_files = count
    status.bytes_written = total
    return status


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.mlcq.exists():
        print(f"MLCQ not found at {args.mlcq}", file=sys.stderr)
        print("Download it from https://doi.org/10.5281/zenodo.3590101", file=sys.stderr)
        return 1

    samples = load_samples(args.mlcq)
    # One representative sample per repository, ordered so that the repositories
    # carrying the most ground truth are fetched first: an interrupted run then
    # still leaves the most useful corpus available.
    per_repo: dict[str, Sample] = {}
    weight: dict[str, int] = {}
    for sample in samples:
        per_repo.setdefault(sample.repository, sample)
        weight[sample.repository] = weight.get(sample.repository, 0) + 1
    ordered = sorted(per_repo.values(), key=lambda s: (-weight[s.repository], s.repository))
    if args.limit:
        ordered = ordered[: args.limit]

    manifest = Manifest.load(args.out)
    started = time.monotonic()
    done = failed = skipped = 0

    for index, sample in enumerate(ordered, 1):
        owner, name = sample.owner_and_name
        label = f"{owner}/{name}"
        if manifest.is_done(sample.repository):
            skipped += 1
            continue

        try:
            status = fetch_one(sample, args.out, args.timeout, args.max_archive_mb)
        except Exception as exc:
            # A fetch runs unattended for hours over hundreds of repositories.
            # Whatever one of them manages to raise, losing the other four
            # hundred to it is never the right outcome: record it, keep going,
            # and let the re-run retry it.
            status = RepoStatus(
                repository=sample.repository,
                commit_hash=sample.commit_hash,
                directory=repo_dirname(sample),
                ok=False,
                reason=f"unexpected: {exc.__class__.__name__}",
            )
        manifest.record(status)
        manifest.save(args.out)

        if status.ok:
            done += 1
            size_mb = status.bytes_written / 1048576
            print(
                f"[{index}/{len(ordered)}] {label}: "
                f"{status.java_files} .java, {size_mb:.1f} MB "
                f"({weight[sample.repository]} samples)",
                flush=True,
            )
        else:
            failed += 1
            print(f"[{index}/{len(ordered)}] {label}: FAILED ({status.reason})", flush=True)

        time.sleep(PAUSE_BETWEEN_REPOS_S)

    elapsed = time.monotonic() - started
    coverage = Corpus(args.out).coverage(samples)
    print(f"\nFetched {done}, failed {failed}, already present {skipped} in {elapsed / 60:.1f} min")
    print(f"Ground-truth coverage: {coverage.describe()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
