"""Rewriting a source file through byte ranges, or refusing to.

Every transformation in the engine ends up here: it decides *what* to change and
expresses it as a set of :class:`Edit`s, and this module is the only thing that
touches the bytes. Keeping that in one place means the properties below are
established once instead of per transformation.

**Bytes, not characters.** tree-sitter reports byte offsets, and Java source is
UTF-8: a file with a non-ASCII identifier, comment or string literal has more
bytes than characters. Slicing such a file by character index silently cuts
through a multi-byte sequence and produces mojibake or an undecodable file. The
whole pipeline therefore stays in bytes and decodes only at the edges.

**Overlaps are refused, never resolved.** Two edits that touch the same bytes
have no defined result, and picking one by some rule would mean the engine
sometimes discards a change it reported as applied. A conflict raises, the
transformation reports itself as not applicable, and the file is left alone --
which, per the engine's contract, is a correct outcome rather than a failure.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import pairwise


class EditConflict(Exception):
    """Two edits claim the same bytes, so the rewrite has no defined result."""


@dataclass(frozen=True, order=True)
class Edit:
    """Replace ``source[start:end]`` with ``replacement``.

    ``start == end`` inserts without removing anything; an empty
    ``replacement`` deletes. Ordering is by position so a set of edits sorts
    into document order without a key function.
    """

    start: int
    end: int
    replacement: bytes

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"negative start: {self.start}")
        if self.end < self.start:
            raise ValueError(f"end {self.end} precedes start {self.start}")

    @property
    def is_insertion(self) -> bool:
        return self.start == self.end

    def overlaps(self, other: Edit) -> bool:
        """True when the two claim a byte in common.

        Touching ranges do not overlap: one edit ending exactly where the next
        begins is the ordinary case of rewriting two adjacent statements. Two
        insertions at the same offset do conflict, because their order would
        decide the output and nothing here defines it.
        """
        if self.is_insertion and other.is_insertion:
            return self.start == other.start
        return self.start < other.end and other.start < self.end


def check(edits: Iterable[Edit]) -> tuple[Edit, ...]:
    """Put edits in document order, refusing any pair that overlaps."""
    ordered = tuple(sorted(edits))
    for earlier, later in pairwise(ordered):
        if earlier.overlaps(later):
            raise EditConflict(
                f"edit [{earlier.start}:{earlier.end}] overlaps [{later.start}:{later.end}]"
            )
    return ordered


def apply_edits(source: bytes, edits: Sequence[Edit]) -> bytes:
    """Rewrite ``source``, applying every edit exactly once.

    Applied back to front so that each edit's offsets still refer to the text it
    was computed against; applying forwards would shift every later range by the
    length change of every earlier one, and getting that arithmetic subtly wrong
    is how a rewriter corrupts a file while looking like it worked.
    """
    ordered = check(edits)
    if ordered and ordered[-1].end > len(source):
        raise ValueError(f"edit ends past the file: {ordered[-1].end} > {len(source)}")

    out = source
    for edit in reversed(ordered):
        out = out[: edit.start] + edit.replacement + out[edit.end :]
    return out


# ----------------------------------------------------------------------
# Indentation
# ----------------------------------------------------------------------
# Lifting a block out of a conditional moves it one level left, and the result
# has to look like the file it lands in. Nothing here assumes four spaces, or
# spaces at all: the unit is measured from the file, because a project that
# indents with tabs must come back out indented with tabs.


def line_start(source: bytes, offset: int) -> int:
    """Offset of the first byte of the line containing ``offset``."""
    newline = source.rfind(b"\n", 0, offset)
    return 0 if newline == -1 else newline + 1


def indent_at(source: bytes, offset: int) -> bytes:
    """The leading whitespace of the line containing ``offset``."""
    start = line_start(source, offset)
    cursor = start
    while cursor < len(source) and source[cursor : cursor + 1] in (b" ", b"\t"):
        cursor += 1
    return source[start:cursor]


def dedent(block: bytes, unit: bytes) -> bytes:
    """Strip one level of indentation from every line that carries it.

    Lines that do not begin with ``unit`` are left alone rather than trimmed by
    length. A continuation line, a line comment aligned by hand or a text block
    can sit at any depth, and cutting a fixed number of bytes off one of those
    would silently change the code -- inside a Java text block it would change
    the value of a string.
    """
    if not unit:
        return block
    out = []
    for line in block.split(b"\n"):
        out.append(line[len(unit) :] if line.startswith(unit) else line)
    return b"\n".join(out)
