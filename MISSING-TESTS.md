# MISSING-TESTS — proposed gaps in the v0.1.1 verification surface

This file enumerates claims in the companion paper
*Deterministic Sovereign RAG via Signed-Hash Projection* that are
**not yet pinned down by a test vector in `tests/` and not yet
recomputed by the auditor**. For each gap, a proposed vector file
and an estimated complexity are listed.

Nothing in this file is implemented; the operator decides whether
to accept, defer, or discard each proposal.

## Inventory

### Gap 1 — §4 Lamport/Marzullo clock-drift defense

**Paper claim** (one sentence): The Marzullo intersection of N
clock-measurement intervals of width `2·δ_max` returns a non-empty
feasible interval whenever fewer than N/2 clocks are Byzantine, and
the local time `T_n` recorded by the APG is bounded by
`δ_max` of the upstream's true clock under Lamport happens-before.

**Source file:line**: `paper/sections/section-5-clock-drift.tex:31`
(section), `:142` (Lemma: Bounded Clock Drift), `:208-211`
(Marzullo intersection step).

**Status**: **RESOLVED in v0.2.0**. See "Closed in v0.2.0" below.

### Gap 2 — §8 Bayesian backoff (Weibull + asymmetric EMA)

**Paper claim** (one sentence): Given probe interval `t`,
posterior gammas `(gamma_hit, gamma_miss)`, and indicator `S_n`,
the backoff in milliseconds is
`tau_n = (1 - F(t)) * 1000 * (0.4 + 0.6 * S_n)` with
`F(t) = 1 - exp(-(t/lambda)^k)`, where `(lambda, k) = (0.85, 1.7)`
are the operator-corpus Weibull parameters.

**Source file:line**: `tests/bayesian_backoff_golden.json:5-13`
(declares the model and formulas). Paper source: `paper/sections/section-8-det.tex:150-200`
(Weibull identification theorem), `:43-67` (asymmetric EMA).

**Status**: **RESOLVED in v0.2.0**. See "Closed in v0.2.0" below.

### Gap 3 — §7 Production polyglot stack

**Paper claim** (one sentence): The DSVH Rust crate and APG Go
module together deliver sub-millisecond retrieval with the
production runtime characteristics (640 ns match latency, 25/25
concurrency stress test).

**Source file:line**: `paper/deterministic-sovereign-rag.tex:1926-2066`
(`Production Stack: Code and Configuration`), `:1949-2066`
(Appendix A.3-A.4).

**Why it's NOT testable here**: The production runtime is operator
IP (per `MANIFEST.md` §5). Including a JSON vector would either
leak implementation details (offsets, magic numbers) or require
synthesizing stand-in values that don't exercise anything real.

**Proposed vector file**: None. This gap is **deliberately out of
scope** for the public verification surface; it is verified by the
production benchmark suite on the operator's substrate.

**Estimated complexity**: **N/A** (not testable in this surface).

### Gap 4 — §11 Operational bound on pagination throughput

**Paper claim** (one sentence): For paginated upstream scans with
rate limit R, the throughput `R_throughput` satisfies
`R_throughput ≤ R / (1 + p)` where `p` is the proportion of
pages that trigger a full prefill.

**Source file:line**: `paper/deterministic-sovereign-rag.tex:1197-1303`
(Operational Bound 1: Pagination Throughput Limit).

**Why it's NOT testable**: Pure analytical bound; the right-hand
side is provable from the rate-limit interaction. A JSON vector
would just be `(R, p) → R_throughput ≤ R/(1+p)`, which is a
tautology once the inequality is restated.

**Proposed vector file**: None. The bound is verified by the
operational argument in §11 itself.

**Estimated complexity**: **N/A** (analytical).

### Gap 5 — §12 Adversarial: When NOT to Use DET (negative vectors)

**Paper claim** (one sentence): FNV-1a + L2 projection fails on
(i) distribution shift between training and query, (ii) dense
embedding regimes where 768-dim embedders dominate, (iii)
adversarial inputs engineered to collide under the parity-bit
Rademacher sign.

**Source file:line**: `paper/deterministic-sovereign-rag.tex:1750-1846`
(`Discussion: When NOT to Use This Primitive`), `:1760-1802`
(Four Failure Modes), `:1803-1845` (Three Reviewer Attack Vectors).

**Why it's testable**: A "negative vector" carrying two FNV-1a
inputs `s_1 ≠ s_2` engineered to hash to `±1` parity patterns that
maximize inner-product under the projection would let the auditor
assert the failure mode rather than assert success. The
construction is well-known (birthday-attack on 64-bit hashes).

**Proposed vector file**: `tests/adversarial_collision_golden.json`
with schema:

- `vectors[]`: `[{id, scenario: "collision" | "distribution_shift" | "dense_dominated", input_a, input_b, expected_inner_product, recall_at_5_vs_dense_768}]`

**Estimated complexity**: **Medium** — collision-finding requires
either a brute-force precomputation (~2^32 attempts per 64-bit
collision class) or a closed-form construction; either way the
generation is non-trivial. The auditor check is trivial once the
vector exists.

### Gap 6 — §5 Per-axis mean and variance of the signed-hash estimator (Theorem 1, Theorem 2)

**Paper claim** (one sentence): Under the parity-bit Rademacher
sign, the signed-hash inner-product estimator is unbiased with
variance bounded by the Weinberger 2009 covariance formula.

**Source file:line**: `paper/deterministic-sovereign-rag.tex:552-728`
(Theorem 1 and Theorem 2).

**Why it's NOT directly testable**: The variance is a population
quantity over the hash family; a sample-based estimator from a
finite JSON file would conflate Monte-Carlo noise with the
theoretical variance. A determinism-style check ("two computations
agree") is already covered by the §3.1 vectors (FNV-1a is
deterministic by construction).

**Proposed vector file**: None — would require sampling N ≥ 10^6
hashes to bound the variance to 1% relative error, which is
infeasible as a static JSON file. A future streaming harness could
exercise this; out of scope for v0.2.

**Estimated complexity**: **High** (and not recommended for this
surface).

## Closed in v0.2.0

### Gap 1 — clock-drift defense (closed)

- New vector file: `tests/clock_drift_vectors.json` (12 vectors:
  5 Marzullo intersection cases including the disjoint-set empty
  case, 3 Lamport happens-before relations covering strict chain,
  send→receive, and concurrent non-chain, and 4 bounded-drift
  bound computations covering NTP-synchronized, free-running TCXO,
  pathological quartz, and sub-millisecond jitter regimes).
- New auditor function: `audit_clock_drift` in
  `auditors/math_runtime_drift.py` (tolerance `1e-12` s on
  Marzullo lo/hi endpoints, Lamport strict-less checks, and the
  bounded-drift bound `tau_n * rho + 2 * delta_max`).
- Status row in `TRACEABILITY.md` flipped from `NOT under test` to
  `PASS` for §4.

### Gap 2 — Bayesian backoff (closed)

- Existing golden file `tests/bayesian_backoff_golden.json` is now
  consumed by the auditor (no schema change to the file).
- New auditor function: `audit_bayesian_backoff` in
  `auditors/math_runtime_drift.py` (tolerance `1e-6` ms on the
  recomputed Weibull CDF + asymmetric-EMA `tau_n_ms`).
- Status row in `TRACEABILITY.md` flipped from `STAGED for v0.2`
  to `PASS` for both §8 rows (Weibull identification and
  asymmetric EMA update rule).

## Summary by complexity

| Tier | Count | Gaps |
| --- | --- | --- |
| Low (closed in v0.2.0) | 2 | Gap 1 (Lamport/Marzullo), Gap 2 (Bayesian backoff) |
| Medium (deferrable) | 1 | Gap 5 (§12 adversarial negative vectors) |
| High (not recommended) | 1 | Gap 6 (Theorem 1/2 variance sampling) |
| N/A (out of scope) | 2 | Gap 3 (§7 polyglot stack), Gap 4 (§11 throughput bound) |

**Total flagged gaps**: 6 (4 paper sections + 2 analytical results).
**Open after v0.2.0**: 4 (Gaps 3, 4, 5, 6).

## Recommendation

Accept Gaps 1 and 2 for v0.2: both are low-complexity, the golden
file for Gap 2 already exists, and they round out the verification
surface to cover §4, §8, §9 with the same depth as §3.1 and §3.3.

Defer Gap 5: the negative-vector construction needs design
discussion before committing to a schema. Open a paper-issue or a
GitHub Discussion in the Q&A category for review.

Reject Gaps 3, 4, 6 as out-of-scope by design. Document the
rejection in `MANIFEST.md` §3 (open items) when v0.2 ships.

## Cross-references

- Companion paper:
  [LOUST-PRO/deterministic-sovereign-rag](https://github.com/LOUST-PRO/deterministic-sovereign-rag)
- Test vectors (current):
  [`tests/`](./tests/)
- Auditor (current):
  [`auditors/math_runtime_drift.py`](./auditors/math_runtime_drift.py)
- Claim-to-test map (current):
  [`TRACEABILITY.md`](./TRACEABILITY.md)
