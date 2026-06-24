# MANIFEST-2026-06-23-dsvh-verification-suite

> **Stage**: published (public, Apache-2.0)
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
- Runtime trace dumps (sanitized, no PII).
- Math ↔ runtime drift auditor.

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
├── .gitignore                      # defensive
├── scripts/                        # Zenodo API authentication E2E test
│   └── zenodo_oauth_test.py        # (public: stdlib only, raw socket)
├── tests/                          # [OPEN] deterministic vectors + property tests
│   ├── fnv1a_64_vectors.json       # [pending]
│   ├── l2_projection_golden.json   # [pending]
│   ├── bayesian_backoff_golden.json # [pending]
│   └── zero_token_keepalive_trace.json  # [pending]
├── traces/                         # [OPEN] runtime trace dumps (sanitized)
│   └── 2026-06-23-zero-token-keepalive.jsonl  # [pending]
├── auditors/                       # [OPEN] math ↔ runtime drift checker
│   └── math_runtime_drift.py       # [pending]
└── .github/
    ├── DISCUSSIONS.md              # Discussions categories spec
    └── PROJECTS-arxiv-submission.md  # arXiv submission board spec
```

Items marked `[pending]` are tracked as open work in this
MANIFEST and filled incrementally as the verification suite
matures. The artifact paths are reserved to provide a stable
public surface for downstream deep-research agents.

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
- [ ] CITATION.cff with ORCID — pending; added once test
      vectors are populated
- [x] `.github/DISCUSSIONS.md` spec with 4 categories
      (Endorsement is private)
- [x] `.github/PROJECTS-arxiv-submission.md` spec with 6-column
      board (operator-tooling references scrubbed)
- [x] `scripts/zenodo_oauth_test.py` public-safe (operator
      config path → `<config-path>` placeholder)
- [ ] Test vectors populated in `tests/` — pending; generated
      from the production runtime per the paper's §11
- [ ] Math ↔ runtime drift auditor implemented in `auditors/` —
      pending
- [ ] Trace dumps populated in `traces/` — pending
- [ ] Public-surface curator sweep verdict: clean

## 7. Companion paper

This repository is the verification surface for the paper in
[LOUST-PRO/deterministic-sovereign-rag](https://github.com/LOUST-PRO/deterministic-sovereign-rag).
The two repos are designed to be cross-linked:

- The paper repo's README points to the verification suite.
- The verification suite's README points to the paper.
- The paper's sections are referenced by file:line in the
  verification vectors' metadata (e.g., `paper_section: §3.1`)
  once the test vectors are populated.

## 8. Date

Publication provenance: 2026-06-23. Generated by the operator's
publication pipeline under the stage-local-first contract.
