#!/usr/bin/env python3
"""Brand-name check for the repo.

The blocklist is stored as SHA-256 hashes of lowercased real-organisation
names, never as plain names, so this file itself cannot leak or repeat a
real name. ``find_blocklisted`` hashes every single word and adjacent word
pair in the input text and reports any hash that appears in the blocklist.

Usage: ``python3 scripts/brand_check.py [path ...]`` (defaults to the repo
tree, excluding .git). Exit code 0 means no blocklisted name was found.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

# SHA-256 hashes of lowercased real-organisation names that must not appear
# in this repo (plain names intentionally not stored here).
BLOCKLIST_HASHES = {
    "38742cfe16d3d742bd90d71b2e5c28322ab176703f88408ee41442c4b5de4d9a",
    "584aab979226a1edd5b3441dad2a43c380347feeee48abfcabec00cf0292adf8",
    "719e9c2cfc4310b8ff6929883717041f9a5ca973faa2d4ae6ea13bfc5a703977",
    "49e02cf0eb74c1482c393c82209d49886931bd0d5334388271b04b50e8d8e99d",
    "aec1c299f2a3dd7bb2b109b68158f4b7347067525dcd4d91ab401984b76dcada",
    "68ee6a3b2b1297e6d2e056db03cd012a982865f78320e946ab493fc156dfe1c3",
    "45229aa173a7ef619803b74b9e8cb6405c2881e01bbe19c89528f6f2a2e581ee",
}

_WORD_RE = re.compile(r"[a-z0-9]+")


def _candidates(text: str) -> set[str]:
    words = _WORD_RE.findall(text.lower())
    phrases = set(words)
    phrases.update(f"{a} {b}" for a, b in zip(words, words[1:]))
    return phrases


def find_blocklisted(text: str, blocklist: set[str] = BLOCKLIST_HASHES) -> list[str]:
    """Return the blocklisted phrases (as hashes) found in ``text``."""
    found = []
    for phrase in sorted(_candidates(text)):
        digest = hashlib.sha256(phrase.encode("utf-8")).hexdigest()
        if digest in blocklist:
            found.append(digest)
    return found


def main(argv: list[str]) -> int:
    roots = [Path(p) for p in argv] if argv else [Path(__file__).resolve().parent.parent]
    hits = 0
    for root in roots:
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts)
        for path in files:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            found = find_blocklisted(text)
            if found:
                hits += len(found)
                print(f"{path}: blocklisted name hash(es): {found}")
    if hits:
        print(f"brand check FAILED: {hits} blocklisted hit(s)")
        return 1
    print("brand check passed: no blocklisted names found")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
