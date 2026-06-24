# tests/ — Deterministic test vectors and trace dumps

This folder holds the **executable inputs** for the verification
surface. Every JSON file is a self-describing golden file: it
declares which paper section it backs, what schema it follows, and
which recomputation the auditor (`auditors/math_runtime_drift.py`)
must perform against it.

There is **no Python in this folder**. Vectors are static JSON so
that downstream consumers (the auditor, third-party reimplementers,
reproducibility audits) can consume them with any language. Schema
fields are stable across versions; a `schema_version` is declared at
the top of every file.

## Inventory

| File | Vectors / events | Paper section | What it pins down |
| --- | --- | --- | --- |
| `fnv1a_64_vectors.json` | 24 | §3.1 (FNV-1a 64-bit hashing) | Byte-exact hash values for canonical test strings |
| `l2_projection_golden.json` | 12 | §3.3 (L2 spherical projection) | Rademacher expansion to D=128 + unit-norm normalization |
| `clock_drift_vectors.json` | 12 | §4 (Asynchronous Network and Bounded Clock Drift) | Marzullo intersection, Lamport happens-before, bounded-drift lemma |
| `bayesian_backoff_golden.json` | 16 | §8 (Stochastic State Synchronization) | Weibull CDF + asymmetric EMA backoff ms |
| `zero_token_keepalive_trace.json` | 6 traces / 360 events | §9 (Zero-Prefill Keep-Alive) | Probe/hit/miss sequence with timing and prefill invariant |

Total: **424 vectors/events** across the five files. Every entry is
checked by `auditors/math_runtime_drift.py` (exit 0 = PASS, 1 =
FAIL).

## Per-file summary

### `fnv1a_64_vectors.json` — paper §3.1

24 canonical input strings (empty string, ASCII, multi-byte UTF-8,
emoji, whitespace, long repetitive) paired with their expected
FNV-1a 64-bit hashes in both hex (`0x…`) and decimal. The auditor
recomputes the hash from the input string and asserts byte equality
against both representations. Each vector also implicitly exercises
§3.1's offset basis `0xcbf29ce484222325` and prime `0x100000001b3`
(see `auditors/math_runtime_drift.py:34-36`).

### `l2_projection_golden.json` — paper §3.3

12 source hashes (drawn from the FNV-1a set) expanded to D=128 via
the paper's Rademacher bit-flipping rule (declared in the
`projection.expansion_rule` field). Each vector carries the raw
±1 sequence, the L2 norm before normalization, the unit vector after
normalization, and the L2 norm after normalization (which must equal
1.0 within tolerance). The auditor recomputes the norm from the raw
±1 sequence and verifies against the recorded values.

### `clock_drift_vectors.json` — paper §4

12 vectors covering the three ingredients of the asynchronous-network
defense: 5 Marzullo intersections (including a disjoint-set empty
case, a singleton endpoint, and a wide-envelope full-overlap case), 3
Lamport happens-before relations (strict chain, send→receive, and a
concurrent-pair non-chain), and 4 bounded-drift bound computations
covering NTP-synchronized, free-running TCXO, pathological quartz,
and sub-millisecond probe regimes. The auditor recomputes the
Marzullo lo/hi, the Lamport strict-less comparisons, and the
`tau_n * rho + 2 * delta_max` bound within `1e-12` s.

### `bayesian_backoff_golden.json` — paper §8

16 scenario-tagged inputs to the Bayesian backoff computation
(`cache_hit_after_miss`, `eviction_event`, `long_idle_then_hit`,
etc.). Each vector carries the keep-alive probe interval, the
posterior gamma pair `(gamma_hit, gamma_miss)`, the cache indicator
`S_n`, and the expected backoff in milliseconds computed via the
paper's Weibull CDF formula. The auditor recomputes
`F(t) = 1 - exp(-(t/lambda)^k)` and
`tau_n = (1 - F(t)) * 1000 * (0.4 + 0.6 * S_n)` for every vector
within `1e-6` ms.

### `zero_token_keepalive_trace.json` — paper §9

6 traces of 60 events each (360 total). Each event carries a
monotonic timestamp `t`, a `tau_n_index` (probe sequence number),
an action (`probe` / `hit` / `miss`), the indicator `S_n_indicator`,
the round-trip time `rtt_us`, and `prefill_tokens` (always 0 in the
zero-prefill protocol). The auditor checks four invariants per
event: action-indicand coherence, sequential `tau_n_index`,
monotonic `t`, and zero prefill.

## JSON schema contract

Every file declares:

```json
{
  "schema_version": "1.0.0",
  "generated_at": "<YYYY-MM-DD>",
  "description": "<short prose>",
  "paper_section": "<verbatim paper §>",
  "...": "<file-specific fields>"
}
```

`fnv1a_64_vectors.json` adds:

- `algorithm` — `{name, offset_basis, prime, reference}`
- `vectors[]` — `[{id, input_string, expected_hash_hex, expected_hash_decimal}]`

`l2_projection_golden.json` adds:

- `projection` — `{input_dimension, output_dimension, method, epsilon_jl, expansion_rule}`
- `vectors[]` — `[{id, source_fnv1a_id, input_hash_hex, raw_128_vector, l2_norm_before, l2_normalized, l2_norm_after}]`

`clock_drift_vectors.json` adds:

- `model` — `{marzullo_formula, marzullo_intersection_law, lamport_law, bounded_drift_lemma, tolerance, tolerance_units}`
- `vectors[]` — `[{id, scenario, ...}]` where `scenario` starts with `marzullo_`, `lamport_`, or `bounded_drift_` and the per-scenario fields follow

`bayesian_backoff_golden.json` adds:

- `model` — `{type, lambda_scale, k_shape, evidence, cdf_formula, backoff_formula}`
- `vectors[]` — `[{id, scenario, keep_alive_probe_seconds, gamma_hit, gamma_miss, expected_backoff_ms, indicator_function_S_n}]`

`zero_token_keepalive_trace.json` adds:

- `trace_format` — field-by-field prose description
- `model.rng` — LCG parameters used to synthesize the trace deterministically
- `traces[]` — `[{trace_id, events: [{t, action, rtt_us, prefill_tokens, tau_n_index, S_n_indicator}]}]`

## How to add a new vector

1. Pick the file that matches the paper section of the new claim.
2. Append a new entry to the `vectors[]` (or `traces[]`) array. The
   `id` field MUST be unique and use the file's prefix (`fnv1a_`,
   `l2_`, `backoff_`, `zt_`).
3. For `fnv1a_*`: compute the hash with `python3 -c "import
   sys; h=0xcbf29ce484222325;
   [((h:=((h^b)*0x100000001b3)&0xffffffffffffffff)) for b in
   sys.argv[1].encode()]; print(hex(h), h)" "<input>"` and add
   both the hex and decimal fields.
4. For `l2_*`: derive the raw ±1 sequence from the source hash
   using the declared `expansion_rule`, then normalize.
5. For `backoff_*`: compute `tau_n = (1 - F(t)) * 1000 * (0.4 + 0.6 *
   S_n)` with `F(t) = 1 - exp(-(t/lambda)^k)`.
6. For `cd_*` (clock-drift): compute the Marzullo intersection
   `([max(lo), min(hi)])`, the Lamport strict-less `T_a < T_b`, or
   the bounded-drift bound `tau_n * rho + 2 * delta_max` from the
   scenario-prefixed fields.
7. For `zt_*`: extend one of the existing traces (preferred, to keep
   per-trace event counts aligned) and assert `prefill_tokens == 0`
   on the new event.
8. Run `python3 auditors/math_runtime_drift.py` from the suite
   root. A PASS exit code confirms the new vector was ingested and
   recomputed correctly.

## What this folder does NOT cover

The verification surface is intentionally narrow. The following
sections of the paper are **not pinned down by a JSON file in this
folder**:

- **§4** (Asynchronous Network and Bounded Clock Drift) — now
  covered by `tests/clock_drift_vectors.json` and
  `audit_clock_drift` in the auditor (added in v0.2.0). The
  Marzullo intersection, Lamport happens-before, and bounded-drift
  lemma are each pinned down by deterministic JSON vectors.
- **§5** (the seven-theorem formalization block in the companion
  paper's main `.tex`) — Theorems 1-7 are mathematical proofs; no
  per-vector regression is meaningful.
- **§7** (Production Polyglot Stack) — describes the DSVH Rust
  crate and the APG Go module. Reference implementations live in
  Appendices A.1 and A.2; they are not under test here.
- **§11** (operational bound on throughput) — pure analytical
  bound; no testable artifact.
- **§12** (Adversarial: When NOT to Use DET) — negative guidance,
  not a positive invariant. A "negative vector" could be proposed;
  see `MISSING-TESTS.md`.

## Cross-references

- Auditor that recomputes from these files:
  `../auditors/math_runtime_drift.py`
- Companion paper source of truth:
  [LOUST-PRO/deterministic-sovereign-rag](https://github.com/LOUST-PRO/deterministic-sovereign-rag)
- Bidirectional claim-to-test map:
  [`../TRACEABILITY.md`](../TRACEABILITY.md)
- Proposed gaps:
  [`../MISSING-TESTS.md`](../MISSING-TESTS.md)
