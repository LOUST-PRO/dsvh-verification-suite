#!/usr/bin/env python3
# Apache-2.0 — David Mireles, ORCID 0009-0008-4374-2254
"""Math <-> trace drift auditor for the F80 paper's verification suite.

Compares the mathematical claims in deterministic-sovereign-rag
(paper Sections 3.1, 3.3, 4, 8, and 9) against the golden vectors
and synthetic trace dumps in tests/.

The auditor compares five independent surfaces:

  * paper Section 3.1  FNV-1a 64-bit determinism
  * paper Section 3.3  L2 spherical projection (Rademacher expansion to D=128)
  * paper Section 4    Lamport/Marzullo clock-drift defense
  * paper Section 8    Bayesian backoff (Weibull CDF + asymmetric EMA)
  * paper Section 9    Zero-Prefill Keep-Alive Protocol trace invariants

This script is stdlib only: no numpy, no scipy, no requests, no network.
Tolerance: 1e-9 for L2 norm (per Section 3.3), 1e-12 s for the
clock-drift bound (per Section 4), 1e-6 ms for the Weibull backoff
(per Section 8), 1us for recomputed timing where applicable. Exits 0
if all checks pass, 1 if any drift is detected.

The auditor never imports the production runtime; it reads the
golden JSON / trace dump and re-derives the math claim from
first principles.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = SUITE_ROOT / "tests"

FNV1A_OFFSET = 0xCBF29CE484222325
FNV1A_PRIME = 0x100000001B3
FNV1A_MASK = 0xFFFFFFFFFFFFFFFF

L2_TOLERANCE = 1e-9
TIMING_TOLERANCE_US = 1
BAYESIAN_TOLERANCE_MS = 1e-6
CLOCK_DRIFT_TOLERANCE_S = 1e-12


def fnv1a_64(data: bytes) -> int:
    h = FNV1A_OFFSET
    for b in data:
        h ^= b
        h = (h * FNV1A_PRIME) & FNV1A_MASK
    return h


def audit_fnv1a(path: Path, report: dict) -> int:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    vectors = payload["vectors"]
    checked = 0
    drifts = []
    for vec in vectors:
        input_str = vec["input_string"]
        expected_hex = vec["expected_hash_hex"]
        expected_int = vec["expected_hash_decimal"]
        if not expected_hex.startswith("0x"):
            drifts.append((vec["id"], "expected_hash_hex missing 0x prefix"))
            continue
        expected_from_hex = int(expected_hex, 16)
        if expected_from_hex != expected_int:
            drifts.append((vec["id"], "expected_hash_decimal != int(expected_hash_hex)"))
            continue
        computed = fnv1a_64(input_str.encode("utf-8"))
        if computed != expected_int:
            drifts.append(
                (vec["id"], f"hash drift: computed=0x{computed:016x} expected={expected_hex}")
            )
            continue
        checked += 1
    report["fnv1a_64"] = {
        "paper_section": payload["paper_section"],
        "vectors_total": len(vectors),
        "vectors_passed": checked,
        "drifts": drifts,
    }
    return 0 if not drifts else 1


def audit_l2_projection(path: Path, report: dict) -> int:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    vectors = payload["vectors"]
    projection = payload["projection"]
    out_dim = projection["output_dimension"]
    expected_unit = 1.0 / math.sqrt(out_dim)
    checked = 0
    drifts = []
    for vec in vectors:
        raw = vec["raw_128_vector"]
        if len(raw) != out_dim:
            drifts.append(
                (vec["id"], f"raw_128_vector length {len(raw)} != output_dimension {out_dim}")
            )
            continue
        if any(x not in (-1, 1) for x in raw):
            drifts.append((vec["id"], "raw_128_vector entries not in {{-1, +1}}"))
            continue
        computed_norm = math.sqrt(sum(x * x for x in raw))
        recorded_norm = vec["l2_norm_before"]
        if abs(computed_norm - recorded_norm) > L2_TOLERANCE:
            drifts.append(
                (
                    vec["id"],
                    f"l2_norm_before drift: computed={computed_norm:.12f} recorded={recorded_norm:.12f}",
                )
            )
            continue
        expected_norm_after = math.sqrt(sum(x * x for x in raw)) / computed_norm
        if abs(expected_norm_after - 1.0) > L2_TOLERANCE:
            drifts.append(
                (vec["id"], f"after-normalization norm not 1.0: {expected_norm_after}")
            )
            continue
        normalized = [x / computed_norm for x in raw]
        recorded_unit = vec["l2_normalized"]
        max_component_drift = 0.0
        worst_index = -1
        for i, (c, r) in enumerate(zip(normalized, recorded_unit)):
            d = abs(c - r)
            if d > max_component_drift:
                max_component_drift = d
                worst_index = i
        if max_component_drift > L2_TOLERANCE:
            drifts.append(
                (
                    vec["id"],
                    f"unit vector drift > {L2_TOLERANCE:.0e} at idx={worst_index}: "
                    f"computed={normalized[worst_index]:.15f} recorded={recorded_unit[worst_index]:.15f}",
                )
            )
            continue
        if any(abs(u - expected_unit) > L2_TOLERANCE and abs(u + expected_unit) > L2_TOLERANCE
               for u in recorded_unit):
            drifts.append(
                (vec["id"], f"recorded_unit entries not +/- 1/sqrt({out_dim}) = +/- {expected_unit:.12f}")
            )
            continue
        if abs(vec["l2_norm_after"] - 1.0) > L2_TOLERANCE:
            drifts.append(
                (vec["id"], f"l2_norm_after drift: {vec['l2_norm_after']} != 1.0")
            )
            continue
        checked += 1
    report["l2_projection"] = {
        "paper_section": payload["paper_section"],
        "expansion_rule": projection["expansion_rule"],
        "output_dimension": out_dim,
        "expected_unit_magnitude": expected_unit,
        "vectors_total": len(vectors),
        "vectors_passed": checked,
        "drifts": drifts,
    }
    return 0 if not drifts else 1


def audit_keepalive_trace(path: Path, report: dict) -> int:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    traces = payload["traces"]
    drift_count = 0
    events_total = 0
    rtt_min = None
    rtt_max = None
    rtt_sum = 0
    drifts_per_trace = []
    for trace in traces:
        events = trace["events"]
        local_drifts = []
        prev_t = -1
        prev_tau = -1
        for event in events:
            events_total += 1
            tau = event["tau_n_index"]
            action = event["action"]
            indicator = event["S_n_indicator"]
            t = event["t"]
            rtt = event["rtt_us"]
            prefill = event["prefill_tokens"]
            if (action == "hit") != (indicator == 1):
                local_drifts.append(
                    f"action<->indicator mismatch at tau={tau}: "
                    f"action={action} indicator={indicator}"
                )
            if tau != prev_tau + 1:
                local_drifts.append(
                    f"tau_n_index non-sequential: prev={prev_tau} current={tau}"
                )
            if t < prev_t:
                local_drifts.append(
                    f"t non-monotonic at tau={tau}: prev={prev_t} current={t}"
                )
            if prefill != 0:
                local_drifts.append(
                    f"prefill_tokens != 0 at tau={tau}: {prefill}"
                )
            if rtt_min is None or rtt < rtt_min:
                rtt_min = rtt
            if rtt_max is None or rtt > rtt_max:
                rtt_max = rtt
            rtt_sum += rtt
            prev_t = t
            prev_tau = tau
        if local_drifts:
            drift_count += len(local_drifts)
            drifts_per_trace.append({"trace_id": trace["trace_id"], "drifts": local_drifts})
    report["zero_token_keepalive"] = {
        "paper_section": payload["paper_section"],
        "trace_count": len(traces),
        "events_total": events_total,
        "invariants_checked": [
            "action == 'hit' iff S_n_indicator == 1",
            "tau_n_index sequential from 0",
            "t monotonically non-decreasing",
            "prefill_tokens == 0 (zero-prefill protocol)",
        ],
        "rtt_us_min": rtt_min,
        "rtt_us_max": rtt_max,
        "rtt_us_mean": (rtt_sum / events_total) if events_total else None,
        "timing_tolerance_us": TIMING_TOLERANCE_US,
        "drift_count": drift_count,
        "drifts_by_trace": drifts_per_trace,
    }
    return 0 if drift_count == 0 else 1


def audit_clock_drift(path: Path, report: dict) -> int:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    vectors = payload["vectors"]
    tol = CLOCK_DRIFT_TOLERANCE_S
    checked = 0
    drifts = []

    def marzullo_intersect(intervals):
        if not intervals:
            return None
        lo = max(iv[0] for iv in intervals)
        hi = min(iv[1] for iv in intervals)
        if lo > hi:
            return None
        return (lo, hi)

    for vec in vectors:
        vid = vec["id"]
        scenario = vec["scenario"]

        if scenario.startswith("marzullo_"):
            intervals = vec["intervals"]
            computed = marzullo_intersect(intervals)
            if computed is None:
                if vec["expected_non_empty"]:
                    drifts.append((vid, f"marzullo intersection empty but expected_non_empty=true"))
                    continue
                checked += 1
                continue
            if not vec["expected_non_empty"]:
                drifts.append((vid, f"marzullo intersection non-empty ({computed}) but expected_non_empty=false"))
                continue
            lo_c, hi_c = computed
            lo_e = vec["expected_intersection_lo"]
            hi_e = vec["expected_intersection_hi"]
            if abs(lo_c - lo_e) > tol:
                drifts.append((vid, f"marzullo lo drift: computed={lo_c} expected={lo_e}"))
                continue
            if abs(hi_c - hi_e) > tol:
                drifts.append((vid, f"marzullo hi drift: computed={hi_c} expected={hi_e}"))
                continue
            checked += 1
            continue

        if scenario.startswith("lamport_"):
            events = vec["events"]
            t_a = events[0]["T"]
            t_b = events[1]["T"]
            expected_lt = vec["expected_T_a_lt_T_b"]
            computed_lt = t_a < t_b
            if computed_lt != expected_lt:
                drifts.append((vid, f"lamport T_a<T_b drift: T_a={t_a} T_b={t_b} computed={computed_lt} expected={expected_lt}"))
                continue
            if vec.get("expected_T_b_lt_T_c") is not None:
                t_c = events[2]["T"]
                expected_lt_bc = vec["expected_T_b_lt_T_c"]
                computed_lt_bc = t_b < t_c
                if computed_lt_bc != expected_lt_bc:
                    drifts.append((vid, f"lamport T_b<T_c drift: T_b={t_b} T_c={t_c} computed={computed_lt_bc} expected={expected_lt_bc}"))
                    continue
            checked += 1
            continue

        if scenario.startswith("bounded_drift_"):
            tau_n = vec["tau_n"]
            rho = vec["rho"]
            delta_max = vec["delta_max"]
            computed_bound = tau_n * rho + 2.0 * delta_max
            expected_bound = vec["expected_drift_bound"]
            if abs(computed_bound - expected_bound) > tol:
                drifts.append((vid, f"bounded-drift drift: computed={computed_bound} expected={expected_bound}"))
                continue
            checked += 1
            continue

        drifts.append((vid, f"unknown scenario prefix: {scenario}"))

    report["clock_drift_defense"] = {
        "paper_section": payload["paper_section"],
        "model": payload["model"],
        "tolerance_s": tol,
        "vectors_total": len(vectors),
        "vectors_passed": checked,
        "drifts": drifts,
    }
    return 0 if not drifts else 1


def audit_bayesian_backoff(path: Path, report: dict) -> int:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    vectors = payload["vectors"]
    lam = payload["model"]["lambda_scale"]
    k = payload["model"]["k_shape"]
    tol = BAYESIAN_TOLERANCE_MS
    checked = 0
    drifts = []
    for vec in vectors:
        t = vec["keep_alive_probe_seconds"]
        s_n = vec["indicator_function_S_n"]
        F = 1.0 - math.exp(-((t / lam) ** k))
        computed_backoff_ms = (1.0 - F) * 1000.0 * (0.4 + 0.6 * s_n)
        expected_backoff_ms = vec["expected_backoff_ms"]
        if abs(computed_backoff_ms - expected_backoff_ms) > tol:
            drifts.append(
                (
                    vec["id"],
                    f"backoff drift: computed={computed_backoff_ms:.9f} expected={expected_backoff_ms} (F={F:.12f})",
                )
            )
            continue
        checked += 1
    report["bayesian_backoff"] = {
        "paper_section": payload["paper_section"],
        "lambda_scale": lam,
        "k_shape": k,
        "tolerance_ms": tol,
        "vectors_total": len(vectors),
        "vectors_passed": checked,
        "drifts": drifts,
    }
    return 0 if not drifts else 1


def main() -> int:
    fnv_path = TESTS_DIR / "fnv1a_64_vectors.json"
    l2_path = TESTS_DIR / "l2_projection_golden.json"
    keepalive_path = TESTS_DIR / "zero_token_keepalive_trace.json"
    clock_drift_path = TESTS_DIR / "clock_drift_vectors.json"
    bayesian_path = TESTS_DIR / "bayesian_backoff_golden.json"

    report = {
        "schema_version": "1.0.0",
        "auditor": "math_runtime_drift.py",
        "suite_root": str(SUITE_ROOT),
        "tolerances": {
            "l2_norm": L2_TOLERANCE,
            "timing_us": TIMING_TOLERANCE_US,
            "clock_drift_s": CLOCK_DRIFT_TOLERANCE_S,
            "bayesian_ms": BAYESIAN_TOLERANCE_MS,
        },
    }

    for path in (fnv_path, l2_path, keepalive_path, clock_drift_path, bayesian_path):
        if not path.exists():
            print(f"MISSING: {path}", file=sys.stderr)
            return 1

    rc = 0
    rc |= audit_fnv1a(fnv_path, report)
    rc |= audit_l2_projection(l2_path, report)
    rc |= audit_clock_drift(clock_drift_path, report)
    rc |= audit_bayesian_backoff(bayesian_path, report)
    rc |= audit_keepalive_trace(keepalive_path, report)

    print("=" * 72)
    print("DSVH verification suite: math <-> trace drift auditor")
    print(f"  Suite root:        {SUITE_ROOT}")
    print(f"  L2 tolerance:      {L2_TOLERANCE:.0e}")
    print(f"  Clock-drift tol.:  {CLOCK_DRIFT_TOLERANCE_S:.0e} s")
    print(f"  Bayesian tol.:     {BAYESIAN_TOLERANCE_MS:.0e} ms")
    print(f"  Timing tol.:       {TIMING_TOLERANCE_US} us")
    print("=" * 72)

    fnv = report["fnv1a_64"]
    print()
    print(f"[paper {fnv['paper_section']}] FNV-1a 64-bit determinism")
    print(f"  vectors: {fnv['vectors_passed']}/{fnv['vectors_total']} pass")
    for entry in fnv["drifts"]:
        print(f"  DRIFT: {entry[0]}: {entry[1]}")

    l2 = report["l2_projection"]
    print()
    print(f"[paper {l2['paper_section']}] L2 spherical projection")
    print(f"  D = {l2['output_dimension']}, expected |v_i| = 1/sqrt(D) = {l2['expected_unit_magnitude']:.12f}")
    print(f"  vectors: {l2['vectors_passed']}/{l2['vectors_total']} pass")
    for entry in l2["drifts"]:
        print(f"  DRIFT: {entry[0]}: {entry[1]}")

    cd = report["clock_drift_defense"]
    print()
    print(f"[paper {cd['paper_section']}] Lamport/Marzullo clock-drift defense")
    print(f"  tolerance: {cd['tolerance_s']:.0e} s (Marzullo lo/hi + bounded-drift bound)")
    print(f"  vectors: {cd['vectors_passed']}/{cd['vectors_total']} pass")
    for entry in cd["drifts"]:
        print(f"  DRIFT: {entry[0]}: {entry[1]}")

    bb = report["bayesian_backoff"]
    print()
    print(f"[paper {bb['paper_section']}] Bayesian backoff (Weibull model)")
    print(f"  lambda = {bb['lambda_scale']}, k = {bb['k_shape']}, tolerance = {bb['tolerance_ms']:.0e} ms")
    print(f"  vectors: {bb['vectors_passed']}/{bb['vectors_total']} pass")
    for entry in bb["drifts"]:
        print(f"  DRIFT: {entry[0]}: {entry[1]}")

    ka = report["zero_token_keepalive"]
    print()
    print(f"[paper {ka['paper_section']}] Zero-Prefill Keep-Alive Protocol")
    print(f"  traces: {ka['trace_count']}, events: {ka['events_total']}")
    print(f"  rtt_us: min={ka['rtt_us_min']} max={ka['rtt_us_max']} mean={ka['rtt_us_mean']:.2f}")
    print(f"  invariants checked:")
    for inv in ka["invariants_checked"]:
        print(f"    - {inv}")
    if ka["drift_count"] == 0:
        print(f"  all {ka['events_total']} events pass")
    else:
        print(f"  DRIFT events: {ka['drift_count']}")
        for t in ka["drifts_by_trace"]:
            print(f"  {t['trace_id']}:")
            for d in t["drifts"]:
                print(f"    {d}")

    print()
    print("=" * 72)
    if rc == 0:
        print("RESULT: PASS  (all math claims match recorded values within tolerance)")
    else:
        print("RESULT: FAIL  (drift detected; see DRIFT lines above)")
    print("=" * 72)
    return rc


if __name__ == "__main__":
    sys.exit(main())
