"""Materialise PMD, the external detector this project is compared against.

    python scripts/fetch_pmd.py

Downloads one pinned release of PMD and unpacks it under ``data/tools/``. Nothing
else in the pipeline needs it; only ``compare_with_pmd.py`` does.

**Why an external tool at all.** Chapters 4 and 5 compare two approaches of this
project against each other and against MLCQ. That says which of the two is
better here; it does not say whether either is worth having next to what a
developer can already install. PMD is the honest reference point: free, widely
deployed, and its ``GodClass`` and ``DataClass`` rules implement the same
detection strategies from Lanza & Marinescu that this project's own detectors
cite. The comparison is therefore between two implementations of one published
strategy, not between this project and an unrelated tool.

**Pinned exactly**, like every other dependency (ENGINEERING.md section 7). A
comparison against "whatever PMD was installed that week" is not reproducible,
and PMD's default thresholds move between major versions. The archive's SHA-256
is recorded next to the unpacked tree so a third party can confirm they measured
the same binary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

#: Pinned. Bumping this invalidates every number in the comparison, so it is a
#: change to the experiment and not to a dependency.
PMD_VERSION = "7.27.0"
PMD_URL = (
    "https://github.com/pmd/pmd/releases/download/"
    f"pmd_releases/{PMD_VERSION}/pmd-dist-{PMD_VERSION}-bin.zip"
)

#: What GitHub's release metadata reported for this asset. Checked before the
#: archive is opened: a redirect to an error page is also a stream of bytes.
EXPECTED_BYTES = 133_318_348

DEFAULT_OUT = Path("data/tools")
MANIFEST_NAME = "pmd_manifest.json"

DOWNLOAD_TIMEOUT_S = 600
USER_AGENT = "javasmell-thesis (UBT bachelor project; contact via repository)"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the tree is already unpacked",
    )
    return parser


def unpacked_root(out: Path) -> Path:
    """Where the archive's own top-level directory lands."""
    return out / f"pmd-bin-{PMD_VERSION}"


def executable(out: Path) -> Path:
    """The launcher, whose name differs by platform."""
    windows = unpacked_root(out) / "bin" / "pmd.bat"
    return windows if windows.exists() else unpacked_root(out) / "bin" / "pmd"


def download(url: str, into: Path) -> str:
    """Fetch the archive, returning its SHA-256.

    Hashed while streaming rather than afterwards: the file is 127 MB and there
    is no reason to read it twice.
    """
    digest = hashlib.sha256()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with (
        urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_S) as response,
        into.open("wb") as handle,
    ):
        while chunk := response.read(1 << 20):
            digest.update(chunk)
            handle.write(chunk)
    return digest.hexdigest()


def unpack(archive: Path, out: Path) -> None:
    """Extract, refusing any member that would escape the destination.

    The archive is from a known project over HTTPS, but zip-slip is cheap to
    prevent and the web layer is held to this rule already (ENGINEERING.md
    section 6). A rule that applies only when the source feels untrusted is not
    a rule.
    """
    out.mkdir(parents=True, exist_ok=True)
    destination = out.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.namelist():
            target = (destination / member).resolve()
            if not target.is_relative_to(destination):
                raise ValueError(f"archive member escapes the destination: {member}")
        bundle.extractall(destination)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = unpacked_root(args.out)
    if root.is_dir() and not args.force:
        print(f"Already present: {root}")
        return 0
    if root.is_dir():
        shutil.rmtree(root)

    args.out.mkdir(parents=True, exist_ok=True)
    print(f"Downloading PMD {PMD_VERSION} ({EXPECTED_BYTES / 1e6:.0f} MB)...", flush=True)
    with tempfile.TemporaryDirectory() as scratch:
        archive = Path(scratch) / "pmd.zip"
        try:
            checksum = download(PMD_URL, archive)
        except (urllib.error.URLError, OSError) as failure:
            print(f"download failed: {failure}", file=sys.stderr)
            return 1

        size = archive.stat().st_size
        if size != EXPECTED_BYTES:
            print(
                f"unexpected size: got {size} bytes, expected {EXPECTED_BYTES}",
                file=sys.stderr,
            )
            return 1
        unpack(archive, args.out)

    manifest = {
        "version": PMD_VERSION,
        "url": PMD_URL,
        "bytes": EXPECTED_BYTES,
        "sha256": checksum,
    }
    (args.out / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    launcher = executable(args.out)
    if not launcher.exists():
        print(f"unpacked, but no launcher at {launcher}", file=sys.stderr)
        return 1
    print(f"PMD {PMD_VERSION} at {launcher}")
    print(f"sha256 {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
