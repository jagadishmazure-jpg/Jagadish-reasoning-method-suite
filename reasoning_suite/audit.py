"""Hash-chained audit log.

Each entry stores the SHA-256 of (previous hash + payload), starting from a
fixed genesis hash. ``verify()`` recomputes the whole chain, so deleting,
editing, or reordering an entry breaks verification. The log holds only
method names, task ids, and scores -- never task content or user data.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

GENESIS_HASH = "0" * 64


def _entry_hash(prev_hash: str, payload: str) -> str:
    return hashlib.sha256(f"{prev_hash}:{payload}".encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditEntry:
    index: int
    prev_hash: str
    payload: str
    entry_hash: str


class HashChainedAuditLog:
    """Append-only, tamper-evident audit trail for harness runs."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def append(self, event: str, method: str, task_id: str, solved: bool) -> AuditEntry:
        payload = json.dumps(
            {"event": event, "method": method, "task_id": task_id, "solved": solved},
            sort_keys=True,
        )
        prev = self._entries[-1].entry_hash if self._entries else GENESIS_HASH
        entry = AuditEntry(
            index=len(self._entries),
            prev_hash=prev,
            payload=payload,
            entry_hash=_entry_hash(prev, payload),
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def verify(self) -> bool:
        prev = GENESIS_HASH
        for i, entry in enumerate(self._entries):
            if entry.index != i or entry.prev_hash != prev:
                return False
            if entry.entry_hash != _entry_hash(prev, entry.payload):
                return False
            prev = entry.entry_hash
        return True
