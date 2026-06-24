# auditors/ — Math vs. trace drift auditor

This folder holds the **executable verification** for the golden
files in `../tests/`. The auditor reads a JSON file, recomputes the
math claim from first principles using only the Python standard
library, and asserts that its recomputation matches the recorded
value within a declared tolerance.

There is currently **one auditor** in this folder:

- `math_runtime_drift.py` — verifies paper §3.1 (FNV-1a), §3.3
  (L2 spherical projection), §4 (Lamport/Marzullo clock-drift
  defense), §8 (Bayesian backoff), and §9 (zero-prefill keep-alive
  protocol). Recomputes 24 + 12 + 12 + 16 + 360 = 424 entries
  across five JSON files.

## What `math_runtime_drift.py` verifies

For each paper section the auditor performs an **independent
rederivation** and compares against the recorded value:

### Paper §3.1 — FNV-1a 64-bit determinism

For every vector in `tests/fnv1a_64_vectors.json`:

1. Decode `expected_hash_hex` (must start with `0x`) and assert that
   `int(hex, 16) == expected_hash_decimal`. This catches transcription
   drift between the two representations.
2. Compute `fnv1a_64(input_string.encode("utf-8"))` from first
   principles using the constants at the top of the file
   (`FNV1A_OFFSET = 0xcbf29ce484222325`, `FNV1A_PRIME =
   0x100000001b3`, `FNV1A_MASK = 0xFFFFFFFFFFFFFFFF`).
3. Assert byte equality with `expected_hash_decimal`.

### Paper §3.3 — L2 spherical projection

For every vector in `tests/l2_projection_golden.json`:

1. Verify `len(raw_128_vector) == output_dimension` (which is 128).
2. Verify every entry is in `{-1, +1}` (the Rademacher constraint).
3. Recompute the L2 norm from the raw ±1 sequence and compare to
   `l2_norm_before` within `L2_TOLERANCE = 1e-9`.
4. Verify that the normalized vector's norm is 1.0 within tolerance.
5. Compare each component of the recorded unit vector against the
   recomputed unit vector, tracking the worst-case index.
6. Verify that every component of `l2_normalized` matches the
   expected `±1/sqrt(D) = ±1/sqrt(128)` pattern within tolerance.
7. Verify `l2_norm_after == 1.0` within tolerance.

### Paper §4 — Lamport/Marzullo clock-drift defense

For every vector in `tests/clock_drift_vectors.json` (12 vectors
across three scenario families):

1. **Marzullo scenarios** (`marzullo_*`): recompute the intersection
   `([max(lo_i), min(hi_i)])` from the recorded `intervals[]`,
   compare against `expected_intersection_lo`/`hi` within
   `CLOCK_DRIFT_TOLERANCE_S = 1e-12` s, and assert
   `expected_non_empty` matches whether the computed intersection
   was empty or not. This covers clean overlap, singletons, disjoint
   (empty) inputs, wide envelopes, and the degenerate single-endpoint
   case.
2. **Lamport scenarios** (`lamport_*`): verify the recorded
   strict-less comparisons `T_a < T_b` and (when present)
   `T_b < T_c` from the events list. Strict chains
   (`a -> b -> c` in the same process) must satisfy the inequality;
   concurrent events on different processes must NOT.
3. **Bounded-drift scenarios** (`bounded_drift_*`): recompute the
   Lemma 1 bound `tau_n * rho + 2 * delta_max` from the recorded
   `(tau_n, rho, delta_max)` triple and compare to
   `expected_drift_bound` within `1e-12` s. Covers NTP-synchronized,
   free-running TCXO, pathological quartz, and sub-millisecond
   jitter regimes.

### Paper §8 — Bayesian backoff (Weibull + asymmetric EMA)

For every vector in `tests/bayesian_backoff_golden.json` (16
scenarios):

1. Read `lambda_scale` and `k_shape` from the file's `model` block
   (operator-corpus values `0.85` and `1.7`).
2. Compute `F(t) = 1 - exp(-(t / lambda)^k)` from the recorded
   `keep_alive_probe_seconds`.
3. Compute `tau_n_ms = (1 - F(t)) * 1000 * (0.4 + 0.6 * S_n)` where
   `S_n` is the recorded `indicator_function_S_n` (drives the
   asymmetric EMA's hit-vs-miss branch).
4. Compare the recomputed `tau_n_ms` to the recorded
   `expected_backoff_ms` within `BAYESIAN_TOLERANCE_MS = 1e-6` ms
   (six decimal places matches the recorded precision).

### Paper §9 — Zero-Prefill Keep-Alive Protocol

For every event in every trace of
`tests/zero_token_keepalive_trace.json`, check four invariants:

1. `action == "hit"` iff `S_n_indicator == 1` (action-indicator
   coherence).
2. `tau_n_index` is strictly sequential from the previous event
   (probe numbering is contiguous).
3. `t` is monotonically non-decreasing (timestamps do not go
   backwards within a trace).
4. `prefill_tokens == 0` (the zero-prefill invariant from the
   protocol definition).

The auditor also reports per-trace `rtt_us` summary statistics
(min, max, mean) so reviewers can spot timing outliers without
re-parsing the JSON.

## How to interpret the output

The auditor prints five labeled sections and a one-line verdict:

```
================================================================
DSVH verification suite: math <-> trace drift auditor
  Suite root:        <absolute path of the suite root, from the auditor's SUITE_ROOT constant>
  L2 tolerance:      1e-09
  Clock-drift tol.:  1e-12 s
  Bayesian tol.:     1e-06 ms
  Timing tol.:       1 us
================================================================

[paper Section 3.1 (FNV-1a 64-bit hashing)] FNV-1a 64-bit determinism
  vectors: 24/24 pass

[paper Section 3.3 (L2 spherical projection)] L2 spherical projection
  D = 128, expected |v_i| = 1/sqrt(D) = 0.088388347648318
  vectors: 12/12 pass

[paper Section 4 (Asynchronous Network and Bounded Clock Drift)] Lamport/Marzullo clock-drift defense
  tolerance: 1e-12 s (Marzullo lo/hi + bounded-drift bound)
  vectors: 12/12 pass

[paper Section 8 (Stochastic State Synchronization Protocol)] Bayesian backoff (Weibull model)
  lambda = 0.85, k = 1.7, tolerance = 1e-06 ms
  vectors: 16/16 pass

[paper Section 9 (Zero-Prefill Keep-Alive Protocol)] Zero-Prefill Keep-Alive Protocol
  traces: 6, events: 360
  rtt_us: min=… max=… mean=…
  invariants checked:
    - action == 'hit' iff S_n_indicator == 1
    - tau_n_index sequential from 0
    - t monotonically non-decreasing
    - prefill_tokens == 0 (zero-prefill protocol)
  all 360 events pass

================================================================
RESULT: PASS  (all math claims match recorded values within tolerance)
================================================================
```

`vectors: <passed>/<total> pass` (and `events: … pass`) lines are
the human-readable signal. Any line beginning with `DRIFT:` is a
**specific vector or event that failed recomputation**; the auditor
prints the vector id (or `trace_id:event_idx`) and the exact
mismatch reason. A passing run prints no `DRIFT:` lines.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | All five sections pass within tolerance. |
| `1` | At least one drift detected. The offending vector or event is named in the `DRIFT:` lines above the verdict. |
| `1` | A required JSON file is missing — the auditor prints `MISSING: <path>` to stderr before exiting. |

The auditor never imports the production runtime and never reads
anything outside `tests/` and `auditors/`. It is hermetic.

## Tolerance constants

Defined at the top of `math_runtime_drift.py`:

| Constant | Value | Where it applies |
| --- | --- | --- |
| `L2_TOLERANCE` | `1e-9` | Per-component drift on the L2-normalized vector, and the absolute delta between computed and recorded `l2_norm_before`. Matches the §3.3 analytical floor. |
| `CLOCK_DRIFT_TOLERANCE_S` | `1e-12` | Seconds. Tolerance on Marzullo intersection lo/hi endpoints and on the bounded-drift bound `tau_n * rho + 2 * delta_max`. Tight because the inputs are pure synthetic values. |
| `BAYESIAN_TOLERANCE_MS` | `1e-6` | Milliseconds. Tolerance on the recomputed `tau_n_ms` against the recorded `expected_backoff_ms` (six decimal places matches the recorded precision). |
| `TIMING_TOLERANCE_US` | `1` | Microseconds. Not currently used in drift checks (the §9 invariants are categorical, not numeric), but reserved for future per-event timing comparisons. |

The L2 tolerance is intentionally tight: IEEE-754 double-precision
arithmetic makes the per-component rounding error on a 128-dim
vector with entries in `{-1, +1}` two orders of magnitude below
`1e-9`, so a real drift at this threshold indicates a JSON
transcription error or a bug in the projection pipeline — not
floating-point noise.

## Why stdlib only

The auditor imports nothing beyond `json`, `math`, `sys`, and
`pathlib`. There is no `numpy`, no `scipy`, no `requests`, no
network. The rationale is **reproducibility under audit**:

- **No supply-chain surface**: a reviewer running `pip install` on
  this repo pulls zero new dependencies. Bit-rot in upstream
  libraries cannot change a PASS into a FAIL across releases.
- **Cross-version bit-identity**: `python3.11` and `python3.13`
  agree on the order of summation for the vectors here because the
  math is small (128-dim, ±1 entries). A reviewer re-running the
  auditor on a different machine gets the same answer.
- **No network egress**: the auditor never reaches out. It can be
  run on an air-gapped reviewer's laptop with no observable side
  effects.

The same rationale is documented in
`math_runtime_drift.py:14-18`.

## What this folder does NOT cover

The auditor is intentionally narrow. The following claims from the
companion paper are out of scope:

- **Paper §5 (Formalization: Seven Theorems)** — Theorems 1-7 are
  analytical results. There is no per-vector regression that would
  meaningfully exercise them; numerical sampling would conflate
  Monte-Carlo noise with mathematical drift.
- **Paper Appendix A.1 (Rust DSVH pseudocode)** — A reference
  implementation, not under test. The Rust crate is in the
  companion production stack (`loust.pro/dsvh`); it is verified by
  the production benchmark suite, not here.
- **Paper Appendix A.2 (Go APG pseudocode)** — Same as A.1. The Go
  module is verified by the production integration tests.
- **Paper §8 (Bayesian backoff)** — Covered as of v0.2.0 by
  `audit_bayesian_backoff` in `math_runtime_drift.py` against
  `tests/bayesian_backoff_golden.json`. Recomputes the Weibull CDF
  and the asymmetric-EMA `tau_n_ms` branch.
- **Paper §4 (Lamport happens-before, Marzullo intersection)** —
  Covered as of v0.2.0 by `audit_clock_drift` against
  `tests/clock_drift_vectors.json`. Recomputes the Marzullo
  intersection, the Lamport strict-less comparisons, and the
  bounded-drift bound.
- **Paper §12 (Adversarial: When NOT to Use DET)** — Negative
  guidance. A "negative vector" could be staged for v0.2; see
  `MISSING-TESTS.md`.

## Running the auditor

From the suite root:

```bash
python3 auditors/math_runtime_drift.py
```

The script prints to stdout and exits `0` (PASS) or `1` (FAIL).
There are no flags and no environment variables.

## Cross-references

- Companion paper:
  [LOUST-PRO/deterministic-sovereign-rag](https://github.com/LOUST-PRO/deterministic-sovereign-rag)
- Bidirectional claim-to-test map:
  [`../TRACEABILITY.md`](../TRACEABILITY.md)
- Golden files consumed:
  [`../tests/`](../tests/)
- Proposed gaps:
  [`../MISSING-TESTS.md`](../MISSING-TESTS.md)
