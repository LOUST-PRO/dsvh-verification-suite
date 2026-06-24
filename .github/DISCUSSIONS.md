# GitHub Discussions — categories spec

This document specifies the GitHub Discussions categories to
enable when this repository is published. The categories are
designed to support the arXiv submission pipeline: public
announcement, private endorsement coordination, methodology
Q&A, and implementation sharing.

## Categories to enable

### Announcements

- **Visibility**: public, read-only for non-maintainers
- **Purpose**: release notes, arXiv submission status updates,
  endorsement received, paper revisions
- **Posting**: maintainers only
- **Examples**:
  - "v0.2.0 released — added L2 projection property tests"
  - "arXiv submission v1 posted (endorsement requested)"
  - "arXiv submission v1 endorsed, DOI assigned"

### Endorsement

- **Visibility**: **private** (reviewer-to-author only)
- **Purpose**: arXiv endorsement coordination, draft co-review,
  methodological objections
- **Posting**: maintainers + invited reviewers
- **Examples**:
  - "Endorsement request: David Mireles <research@loust.pro>"
  - "Co-review draft v1 — open methodological question on §7.3"
  - "Endorsement received from cs.IR endorser X (commitment
    message)"

> **Why private**: arXiv endorsement is reviewer-to-author
> communication. Public endorsement threads leak the chain of
> trust and discourage other endorsers. GitHub Discussions
> supports per-category private threads; this is the supported
> channel.

### Q&A

- **Visibility**: public
- **Purpose**: methodology questions, reproducibility audits,
  discrepancies between paper and verification vectors
- **Posting**: open
- **Examples**:
  - "How does the FNV-1a 64-bit determinism test in
    `tests/fnv1a_64_vectors.json` map to §3.1 of the paper?"
  - "Bayesian backoff golden file disagrees with §6.2 by 1 ULP
    — intentional rounding or bug?"

### Show and tell

- **Visibility**: public
- **Purpose**: downstream implementations, ports to other
  languages, benchmarks, performance reports
- **Posting**: open
- **Examples**:
  - "Ported the L2 spherical projection to C++ — 3.2x faster
    on AVX-512"
  - "Reproduced §6.4 with a different corpus — happy to share
    the evaluation harness"

## How to enable on first publish

The repository is created with Discussions enabled by default
for public repositories. In the repository Settings →
Discussions → Categories, create the 4 categories above with
the visibility, purpose, and examples specified.

The first Announcement post should be: "Initial publication —
arXiv endorsement requested (see Endorsement category for
private reviewer-to-author channel)."

## Pinned discussions

- Welcome / how to engage (Q&A)
- arXiv submission status (Announcements — pinned to category)
- Endorsement contact (Endorsement — pinned to category)
