# Threat model and design decisions

This is a local measurement instrument with no network, no user data, and
no model calls, so the threat surface is small. The notes below follow a
STRIDE-style pass over what remains, plus the design decisions (ADRs) that
follow from it.

## STRIDE pass

- **Spoofing.** No identities, no auth. The confirmation gate's "named
  approver" is a label in a local API, not an identity proof — it must
  not be mistaken for authentication if this code is ever reused in a
  real approval flow (see ADR-3).
- **Tampering.** Harness results could be misreported if the reporter
  re-scored. Mitigation: the reporter formats evaluator output only, and
  the demo test pins exact numbers from a real run. Audit entries are
  hash-chained so tampering breaks `verify()`.
- **Repudiation.** The audit log records method, task, and outcome per
  run. It deliberately excludes task content and any user data.
- **Information disclosure.** PII redaction covers email, card, phone,
  and SSN-style values. The repo contains no real data; the brand check
  stores blocklisted names as hashes only.
- **Denial of service.** Search trees are implicit and bounded by budget;
  a run cannot expand more nodes than its budget. Task parameters are
  validated (branching ≥ 2, depth ≥ 1, traps ≥ 0, budget ≥ 0).
- **Elevation of privilege.** No privileged operations exist. Nothing in
  this repo creates cloud resources, sends mail, or touches credentials.

## Decisions (ADRs)

- **ADR-1 — Simulated walks, not model calls.** Keeps runs deterministic,
  free, and offline, at the cost of not measuring real models. Stated
  plainly in the README so the numbers are never over-read.
- **ADR-2 — One scoring rule, owned by the evaluator.** Methods cannot
  grade themselves; the evaluator checks only the walk outcome.
- **ADR-3 — Gates are illustrative, not authentication.** The
  confirmation gate demonstrates the approval properties (named,
  single-use, scoped, expiring, contradiction-aware) as tested behaviour
  for a local harness. Reuse in a real system would need real identity
  and a durable approval store.
- **ADR-4 — Fictional example lab.** The provisional example name
  collided with real firms (its first word is a real-firm name), so the
  example lab is Zindlewick Labs, with the check documented in the README.
  Fictional names are used throughout.
