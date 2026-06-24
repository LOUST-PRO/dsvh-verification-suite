# MANIFEST-2026-06-23-dsvh-verification-suite

> **Stage**: published (public, Apache-2.0)
> **Last updated**: 2026-06-23, v0.1.1 — sync MANIFEST.md to reflect
> the v0.1.0 push (tests/, auditors/, CITATION.cff now populated).
> **Companion paper repo**:
> [LOUST-PRO/deterministic-sovereign-rag](https://github.com/LOUST-PRO/deterministic-sovereign-rag)
> **Operator**: David Mireles — ORCID
> [0009-0008-4374-2254](https://orcid.org/0009-0008-4374-2254)

## 1. Scope

Public repository for the **deterministic verification suite**
that backs the formalization in the companion paper
*Deterministic Sovereign RAG via Signed-Hash Projection* (also
publicly available).

The verification suite contains:

- Deterministic test vectors (FNV-1a 64-bit, L2 projection,
  Bayesian backoff, zero-token keep-alive).
- Property tests (round-trip, determinism, distribution).
- Math ↔ runtime drift auditor (recomputes paper claims from
  first principles and verifies against recorded traces).

## 2. Source of truth

The verification vectors are derived from the production runtime
described in the companion paper §11. The paper formalizes
cosine; the production runtime uses Jaccard. The gap is
documented in §12 of the paper ("Adversarial: When NOT to Use
DET"). The verification suite checks that the **math** is
deterministic, not that the **runtime** matches the math exactly.

## 3. Repo structure

```
dsvh-verification-suite/
├── README.md                       # landing + endorsement call
├── LICENSE                         # Apache-2.0
├── MANIFEST.md                     # this file
├── CITATION.cff                    # ORCID + Apache-2.0 metadata
├── .gitignore                      # defensive
├── .github/
│   ├── DISCUSSIONS.md              # Discussions categories spec
│   └── PROJECTS-arxiv-submission.md  # arXiv submission board spec
├── scripts/
│   └── zenodo_oauth_test.py        # Zenodo API auth E2E test (stdlib, raw socket)
├── tests/                          # 412 vectors/events across 4 JSON files
│   ├── fnv1a_64_vectors.json       # 24 vectors, paper §3.1
│   ├── l2_projection_golden.json   # 12 vectors, paper §3.3
│   ├── bayesian_backoff_golden.json # 16 vectors, paper §8
│   └── zero_token_keepalive_trace.json  # 6 traces / 360 events, paper §9
└── auditors/
    └── math_runtime_drift.py       # math ↔ trace drift auditor (stdlib)
```

All listed paths are populated as of v0.1.0. The auditor
(`auditors/math_runtime_drift.py`) is the silicon-green check:
run it on a fresh clone to verify the suite matches the paper.

## 4. IP-boundary discipline

Three layers defend the public surface against IP-boundary
leaks:

1. **`anonymization-lexicon.md`** in the companion paper repo —
   binding list of patterns that MUST NOT appear publicly.
2. **Pre-publish IP-boundary guard hook** — fires on any
   Write/Edit to public-staging paths in this repo.
3. **Public-surface curator sweep** — final pre-submit sweep
   across all files in this repo.

The discipline is summarized in
[`anonymization-lexicon.md`](https://github.com/LOUST-PRO/deterministic-sovereign-rag/blob/main/verification/anonymization-lexicon.md)
in the companion paper repo.

## 5. What is NOT in this repo

- The production runtime (Jaccard, AVX2 paths, cold-cache
  mitigations).
- The proprietary components referenced as "spec-aligned reduced
  alternatives" in the paper.
- Internal strategy memos, counter-intel notes, or persona
  diagnoses.
- ORCID credentials, signing keys, or operator-side tokens.
- HackerOne-related code or audit data.

## 6. Pre-publish checklist

- [x] `.gitignore` defensive (counterintel/, secrets/, runtime/)
- [x] README.md public-safe (no IP-boundary phrases, no
      operator-tooling names, no absolute paths to operator
      home directories)
- [x] LICENSE Apache-2.0 with third-party attribution
- [x] CITATION.cff with ORCID (added in v0.1.0)
- [x] `.github/DISCUSSIONS.md` spec with 4 categories
      (Endorsement is private)
- [x] `.github/PROJECTS-arxiv-submission.md` spec with 6-column
      board (operator-tooling references scrubbed)
- [x] `scripts/zenodo_oauth_test.py` public-safe (operator
      config path → `<config-path>` placeholder)
- [x] Test vectors populated in `tests/` — 24 FNV-1a + 12 L2 +
      16 Bayesian + 360 trace events (added in v0.1.0)
- [x] Math ↔ runtime drift auditor implemented in `auditors/`
      (added in v0.1.0; recomputes paper claims, verifies
      against recorded traces; verified 24/24 + 12/12 + 6/6
      PASS)
- [x] Public-surface curator sweep verdict: clean
      (13 IP-boundary leaks scrubbed pre-publish of v0.1.0)

## 7. Companion paper

This repository is the verification surface for the paper in
[LOUST-PRO/deterministic-sovereign-rag](https://github.com/LOUST-PRO/deterministic-sovereign-rag).
The two repos are designed to be cross-linked:

- The paper repo's README points to the verification suite.
- The verification suite's README points to the paper.
- The paper's sections are referenced by file:line in the
  verification vectors' metadata (e.g., `paper_section: §3.1`)
  via the JSON schemas in `tests/`.

## 8. Date

Publication provenance: 2026-06-23 (v0.1.0).
MANIFEST sync: 2026-06-23 (v0.1.1).
Generated by the operator's publication pipeline under the
stage-local-first contract.
