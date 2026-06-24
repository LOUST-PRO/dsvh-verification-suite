# GitHub Projects — arXiv submission board

This document specifies the GitHub Projects board for tracking
the arXiv submission pipeline of the companion paper
*Deterministic Sovereign RAG via Signed-Hash Projection*.

## Board name

`arXiv submission pipeline — Deterministic Sovereign RAG`

## Visibility

**Public** (anyone can view, maintainers can move cards). This
is intentional — the board acts as a **strategic signal** of
the paper's submission status. Endorsers and reviewers often
check the board to gauge whether a paper is in active
submission.

## Columns

| # | Column | Entry criteria | Exit criteria |
|---|---|---|---|
| 1 | `Draft` | Initial prose written, not yet ready for internal review | Reviewed by ≥ 1 maintainer + ≥ 1 external reader |
| 2 | `Internal review` | Ready for operator review; verification vectors cross-checked | Operator has read the PDF cover-to-cover + signed off on prose |
| 3 | `Public staging` | Public-surface curator verdict: clean; MANIFEST published; no IP-boundary markers | Endorser identified or arXiv submit attempted |
| 4 | `Endorsement requested` | Submission package prepared (source tarball, license, ORCID linked) | Endorser confirmed via Endorsement Discussion or direct message |
| 5 | `Submitted` | arXiv submit attempted (with approval phrase) | Submission accepted (arXiv ID assigned) |
| 6 | `Endorsed & Live` | arXiv ID assigned, paper live on arXiv.org | — (terminal state) |

## Card contents (required fields)

For each card:

- **Title**: short label (`v1 — first formalization pass`,
  `v1.1 — L2 notation hardening`, `v2 — adversarial §12 added`,
  etc.)
- **Description**: link to MANIFEST in `_staging/` and the
  verification suite commit hash
- **Assignee**: maintainer responsible
- **Labels** (suggested):
  - `arxiv-submission` (all cards)
  - `endorsement-pending` (cards in column 4)
  - `counter-intel-required` (cards that touched internal-only
    material)
  - `ip-boundary-clean` (cards with curator verdict: clean)
  - `blocker` (cards that cannot move without operator
    intervention)

## Workflow rules

- **No card can skip a column.** The pipeline is sequential:
  Draft → Internal review → Public staging → Endorsement
  requested → Submitted → Endorsed & Live. A card moving from
  `Draft` to `Endorsement requested` in one jump is a process
  bug.
- **A card cannot enter `Public staging` without a public-
  surface curator verdict of `clean`.** This is enforced by
  the operator's pre-publish IP-boundary guard hook for
  Write/Edit operations, and by the public-surface curator
  sweep for the final pre-submit verification.
- **A card cannot enter `Endorsement requested` without the
  operator's literal approval phrase** for the publish or
  submit action. This is the stage-local-first rule from the
  operator's documented workflow.

## Strategic signaling rationale

arXiv endorsement is **organic, not transactional**: most
endorsers read the public surface (README, MANIFEST, board,
discussions) to gauge the maturity of the submission. A board
that is **public, up-to-date, and shows the pipeline
progressing** signals to potential endorsers that:

1. The work is real and reproducible (verification suite
   exists).
2. The submission is being prepared carefully (sequential
   pipeline).
3. The author is reachable (Discussions + research@loust.pro).

This is the highest-leverage organic channel available; it is
preferred over private solicitation.

## How to create the board on first publish

```bash
gh project create --owner LOUST-PRO \
  --title "arXiv submission pipeline — Deterministic Sovereign RAG" \
  --visibility public
```

Then create the 6 columns in order, and add the labels. The
maintainer-only Announcements Discussion
("arXiv submission v1 — endorsement requested") should be
created in the same publish turn.
