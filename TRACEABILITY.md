# TRACEABILITY — paper claims to test vectors to auditor checks

This file is the **bidirectional map** between the companion paper
*Deterministic Sovereign RAG via Signed-Hash Projection* and the
artifacts in this verification suite. Every claim that the
verification suite backs has a row; every JSON file in `tests/` has
at least one row pointing at it; every check in the auditor has a
row pointing at it.

The paper file:line references are against the source in
[LOUST-PRO/deterministic-sovereign-rag](https://github.com/LOUST-PRO/deterministic-sovereign-rag)
at `paper/deterministic-sovereign-rag.tex` (main file, 2644 lines)
and the per-section files under `paper/sections/`. If a claim does
not have a verifiable artifact in this suite, the status is **NOT
under test** with a justification in the row.

## Conventions

- **Paper source**: every citation uses the absolute path under the
  companion repo. `paper/deterministic-sovereign-rag.tex:361` means
  line 361 of the main `.tex`. `paper/sections/section-8-det.tex:150`
  means line 150 of the section-8 file.
- **Test vector anchor**: `<file>.json` path + the JSON field path
  that pins the claim (e.g. `vectors[0].expected_hash_hex`).
- **Auditor check**: `auditors/math_runtime_drift.py` + the line
  range where the recomputation lives.
- **Status**: `PASS` (auditor verifies), `NOT under test` (no
  artifact, justification in row), or `STAGED for v0.2` (golden file
  exists, auditor check pending).

## Claim-to-test map

| Paper section | Paper claim | Paper file:line | Test anchor | Auditor check | Status |
| --- | --- | --- | --- | --- | --- |
| §3.1 | FNV-1a 64-bit hash for the empty string equals the offset basis `0xcbf29ce484222325`. | `paper/deterministic-sovereign-rag.tex:365-366` (constants) and `:370` (loop) | `tests/fnv1a_64_vectors.json` → `vectors[0]` (`fnv1a_001`, `input_string=""`, `expected_hash_hex=0xcbf29ce484222325`) | `auditors/math_runtime_drift.py:50-80` (`audit_fnv1a` recomputes from `FNV1A_OFFSET` at `:34`) | PASS |
| §3.1 | FNV-1a 64-bit hash is deterministic and bit-exact across multi-byte UTF-8 input. | `paper/deterministic-sovereign-rag.tex:370-374` | `tests/fnv1a_64_vectors.json` → `vectors[16]` (`fnv1a_017`, "café résumé naïve"), `vectors[17]` (`fnv1a_018`, "日本語テスト") | `auditors/math_runtime_drift.py:50-80` | PASS |
| §3.3 | Rademacher expansion maps a 64-bit hash to a 128-dim ±1 vector using a parity-bit rule. | `paper/deterministic-sovereign-rag.tex:376-380` (sign function) | `tests/l2_projection_golden.json` → `projection.expansion_rule` (formula) and `vectors[*].raw_128_vector` (entries in `{-1,+1}`) | `auditors/math_runtime_drift.py:99-101` (`if any(x not in (-1, 1) for x in raw)`) | PASS |
| §3.3 | L2 normalization of a 128-dim ±1 vector yields `‖v‖₂ = √D = √128 ≈ 11.3137` before normalization, and `1.0` after. | `paper/deterministic-sovereign-rag.tex:412-414` (norm definition) | `tests/l2_projection_golden.json` → `vectors[*].l2_norm_before` (recorded) and `vectors[*].l2_norm_after` (must be `1.0`) | `auditors/math_runtime_drift.py:102-104` (`computed_norm = math.sqrt(sum(x*x for x in raw))`) and `:142-146` (`abs(vec["l2_norm_after"] - 1.0) > L2_TOLERANCE`) | PASS |
| §3.3 | After L2 normalization, every component equals `±1/√D = ±1/√128 ≈ ±0.0884`. | `paper/deterministic-sovereign-rag.tex:412-414` | `tests/l2_projection_golden.json` → `vectors[*].l2_normalized` | `auditors/math_runtime_drift.py:118-141` (per-component drift against the recomputed unit vector, plus `±1/sqrt(D)` check at `:136-141`) | PASS |
| §4 | Lamport happens-before partial order and Marzullo intersection defend against clock drift in the asynchronous network. | `paper/sections/section-5-clock-drift.tex:31` (section), `:128` (Lamport citation), `:77-78` (Marzullo), `:208-211` (Marzullo intersection step) | `tests/clock_drift_vectors.json` → `vectors[]` (12 vectors: 5 Marzullo + 3 Lamport + 4 bounded-drift bound) | `auditors/math_runtime_drift.py:229-323` (`audit_clock_drift` recomputes Marzullo intersection, Lamport strict-less, and bounded-drift bound within `CLOCK_DRIFT_TOLERANCE_S = 1e-12`) | PASS |
| §8 | Weibull survival identification: empirical `1_miss` events follow `Weibull(λ*, k*)` identifiable from N ≥ 100 observations via MLE. | `paper/sections/section-8-det.tex:150-180` (subsection + theorem statement), `paper/deterministic-sovereign-rag.tex:478` (notation) | `tests/bayesian_backoff_golden.json` → `model.lambda_scale`, `model.k_shape`, `model.cdf_formula`, `model.backoff_formula`, and `vectors[*].expected_backoff_ms` | `auditors/math_runtime_drift.py:326-365` (`audit_bayesian_backoff` recomputes `F(t) = 1 - exp(-(t/λ)^k)` and `tau_n = (1 - F(t)) * 1000 * (0.4 + 0.6 * S_n)` within `BAYESIAN_TOLERANCE_MS = 1e-6`) | PASS |
| §8 | The asymmetric EMA update rule uses `S_n ∈ {0,1}` with hit dominating miss (contribution `τ_n` for hit vs `α·τ_n` for miss). | `paper/sections/section-8-det.tex:43-67` (asymmetric EMA definition and update) | `tests/bayesian_backoff_golden.json` → `vectors[*].indicator_function_S_n` (drives the formula branch) | `auditors/math_runtime_drift.py:326-365` (same `audit_bayesian_backoff`; the `S_n` branch is the `(0.4 + 0.6 * S_n)` multiplier) | PASS |
| §9 | Zero-Prefill Keep-Alive Probe has `prefill_tokens == 0` by construction. | `paper/sections/section-9-zero-prefill.tex:17-37` (protocol definition), `:82-83` (idle window) | `tests/zero_token_keepalive_trace.json` → `traces[*].events[*].prefill_tokens` (always `0`) | `auditors/math_runtime_drift.py:196-199` (`if prefill != 0`) | PASS |
| §9 | The probe returns a boolean hit/miss indicator `S_n`, and the action label is `hit` iff `S_n = 1`. | `paper/sections/section-8-det.tex:65-67` (`S_n` definition), `paper/sections/section-9-zero-prefill.tex:170-205` (algorithm) | `tests/zero_token_keepalive_trace.json` → `traces[*].events[*].action` and `traces[*].events[*].S_n_indicator` | `auditors/math_runtime_drift.py:183-187` (`if (action == "hit") != (indicator == 1)`) | PASS |
| §9 | Probe index `tau_n` (here `tau_n_index`) is sequential and the local timestamp `t` is monotonically non-decreasing within a trace. | `paper/sections/section-8-det.tex:43` (update rule with `τ_n`), `paper/sections/section-9-zero-prefill.tex:205-219` (algorithm loop) | `tests/zero_token_keepalive_trace.json` → `traces[*].events[*].tau_n_index` and `traces[*].events[*].t` | `auditors/math_runtime_drift.py:188-195` (sequential and monotonic checks) | PASS |
| §9 | Round-trip times `rtt_us` are recorded in microseconds and summarized across the trace. | `paper/sections/section-9-zero-prefill.tex:405-443` (monitoring + observability) | `tests/zero_token_keepalive_trace.json` → `traces[*].events[*].rtt_us` | `auditors/math_runtime_drift.py:200-204` (min/max/mean aggregation) and `:218-222` (report) | PASS |
| §12 | "Adversarial: When NOT to Use DET" delineates failure modes (distribution shift, dense-embedder regimes, etc.). | `paper/deterministic-sovereign-rag.tex:1750-1846` (`Discussion: When NOT to Use This Primitive`) | — | — | NOT under test — negative guidance, not a positive invariant. See `MISSING-TESTS.md` for a proposed negative vector. |
| App. A.1 | Rust `DSVH` reference implementation: byte-exact FNV-1a + Little-Endian serialization for cross-architecture bit-identity. | `paper/deterministic-sovereign-rag.tex:382-395` (Little-Endian paragraph), `paper/sections/app-a1-rust-dsvh.tex` (whole file) | — | — | NOT under test — reference implementation; production stack verified by the production benchmark suite, not here. |
| App. A.2 | Go `APG` reference implementation. | `paper/sections/app-a2-go-apg.tex` (whole file) | — | — | NOT under test — same as A.1. |

## Test-file-to-paper reverse map

| Test file | Sections covered | Sections NOT covered (justified elsewhere) |
| --- | --- | --- |
| `tests/fnv1a_64_vectors.json` | §3.1 | — |
| `tests/l2_projection_golden.json` | §3.3 | — |
| `tests/clock_drift_vectors.json` | §4 (Lamport/Marzullo) | — |
| `tests/bayesian_backoff_golden.json` | §8 (Weibull CDF + asymmetric EMA) | §12 (adversarial) |
| `tests/zero_token_keepalive_trace.json` | §9 (protocol invariants) | §12 |

## Auditor-to-paper reverse map

| Auditor function | Lines | Paper section | What it recomputes |
| --- | --- | --- | --- |
| `audit_fnv1a` | `auditors/math_runtime_drift.py:50-80` | §3.1 | FNV-1a hash from first principles |
| `audit_l2_projection` | `auditors/math_runtime_drift.py:83-157` | §3.3 | L2 norm + per-component unit vector |
| `audit_clock_drift` | `auditors/math_runtime_drift.py:160-323` | §4 | Marzullo intersection (lo/hi), Lamport strict-less chain, bounded-drift bound |
| `audit_bayesian_backoff` | `auditors/math_runtime_drift.py:326-365` | §8 | Weibull CDF + asymmetric-EMA backoff in ms |
| `audit_keepalive_trace` | `auditors/math_runtime_drift.py:368-435` | §9 | Four invariants per event |

## Provenance

- Paper source revision at trace time: `paper/deterministic-sovereign-rag.tex`
  SHA recorded in the companion repo's MANIFEST (2026-06-23, public
  SHA `a1743369`).
- Verification suite revision: v0.1.1 (public SHA `1026ad0`).
- This TRACEABILITY map is regenerated against the paper source on
  each release of the verification suite. Drift between paper
  revisions and this map is documented in `MANIFEST.md`.

## Cross-references

- Companion paper:
  [LOUST-PRO/deterministic-sovereign-rag](https://github.com/LOUST-PRO/deterministic-sovereign-rag)
- Test vectors:
  [`tests/`](./tests/)
- Auditor:
  [`auditors/math_runtime_drift.py`](./auditors/math_runtime_drift.py)
- Missing tests proposal:
  [`MISSING-TESTS.md`](./MISSING-TESTS.md)
