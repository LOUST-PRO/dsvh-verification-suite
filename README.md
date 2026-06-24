# DSVH Verification Suite

> **Companion paper**: [LOUST-PRO/deterministic-sovereign-rag](https://github.com/LOUST-PRO/deterministic-sovereign-rag)
> **Operator**: David Mireles — ORCID [0009-0008-4374-2254](https://orcid.org/0009-0008-4374-2254)
> **License**: Apache-2.0

This repository packages the **verification suite** that backs the
formalization in the companion paper
[*Deterministic Sovereign RAG via Signed-Hash Projection*](https://github.com/LOUST-PRO/deterministic-sovereign-rag).
The paper is the arXiv-submission-friendly reduced subset; this
repository contains the **executable checks** — the deterministic test
vectors, the FNV-1a round-trip property tests, the L2 spherical
projection trace dumps, the Bayesian backoff golden files, and the
math ↔ runtime drift auditor.

For the full architecture and the operator-stack used in production,
see [loust.pro/dsvh](https://loust.pro/dsvh).

## Status

This repository is published as a **publication-provenance artifact**:
it records the IP-boundary discipline applied to the companion
paper's verification surface. The IP-boundary contract (binding
list of forbidden patterns, operator-internal paths, and tooling
identifiers) is documented in
[`verification/anonymization-lexicon.md`](https://github.com/LOUST-PRO/deterministic-sovereign-rag/blob/main/verification/anonymization-lexicon.md)
in the companion paper repository.

The boundary is enforced on the publication side by a pre-publish
guard hook that fires on Write/Edit to public-staging paths, and by
the public-surface curator sweep applied before publication.

## What is in this repository

```
dsvh-verification-suite/
├── README.md                       # this file
├── LICENSE                         # Apache-2.0
├── MANIFEST.md                     # publication provenance + open items
├── .gitignore                      # defensive (IP-boundary + secrets)
├── scripts/                        # Zenodo API authentication E2E test
│   └── zenodo_oauth_test.py        # (referenced from MANIFEST §3)
└── .github/
    ├── DISCUSSIONS.md              # Discussions categories spec
    └── PROJECTS-arxiv-submission.md  # arXiv submission board spec
```

The test vectors (`tests/`), trace dumps (`traces/`), and the
math ↔ runtime drift auditor (`auditors/`) are tracked as
**open items** in [`MANIFEST.md`](./MANIFEST.md) §3 and are
filled incrementally as the verification suite matures. The
artifact paths are reserved; see MANIFEST §3 for the current
completion status.

## What is NOT in this repository

This repository is the **public verification surface** for the
paper. It does NOT include:

- The production runtime (Jaccard, AVX2 paths, cold-cache
  mitigations). See [loust.pro/dsvh](https://loust.pro/dsvh) for
  the operator-stack.
- The proprietary components referenced as "spec-aligned reduced
  alternatives" in the paper.
- Internal strategy memos, counter-intel notes, or persona
  diagnoses.
- ORCID credentials, signing keys, or operator-side tokens.

The boundary is enforced by `anonymization-lexicon.md` in the
companion paper repo (binding) and by the operator's pre-publish
guard hook on the publication side.

## Contributing / Endorsement

If you have an **arXiv endorsement** in `cs.IR` or `cs.DS` and
are willing to **endorse this submission** (or co-review a draft),
please open a GitHub Discussion in the
[Endorsement category](./.github/DISCUSSIONS.md#endorsement)
(private reviewer-to-author) or email **research@loust.pro**.

For methodology questions, reproducibility audits, or to report
discrepancies between the paper's math and the verification
vectors, open a GitHub Discussion in the
[Q&A category](./.github/DISCUSSIONS.md#qa).

## Citation

If you use this verification suite or the companion paper,
please cite both:

```bibtex
@misc{mireles2026deterministic,
  author       = {Mireles, David},
  title        = {Deterministic Sovereign RAG via Signed-Hash Projection:
                  An Operator-Stack Formalization of FNV-1a 64-bit +
                  L2 Spherical Projection at D=128 for Reproducible
                  Retrieval on Sovereign Cloud Infrastructure},
  year         = {2026},
  howpublished = {arXiv preprint},
  orcid        = {0009-0008-4374-2254},
}
```

The full `CITATION.cff` will be added once the verification
vectors and auditor are populated (see MANIFEST §3).

## License

Apache License 2.0. See [`LICENSE`](./LICENSE) for the full text
and third-party attribution.
