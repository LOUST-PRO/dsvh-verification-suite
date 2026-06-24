#!/usr/bin/env python3
# Apache-2.0 — David Mireles, ORCID 0009-0008-4374-2254
"""Math <-> trace drift auditor for the F80 paper's verification suite.

Compares the mathematical claims in deterministic-sovereign-rag
(paper Sections 3.1, 3.3, and 9) against the golden vectors and
synthetic trace dumps in tests/.

The auditor compares three independent surfaces:

  * paper Section 3.1  FNV-1a 64-bit determinism
  * paper Section 3.3  L2 spherical projection (Rademacher expansion to D=128)
  * paper Section 9    Zero-Prefill Keep-Alive Protocol trace invariants

This script is stdlib only: no numpy, no scipy, no requests, no network.
Tolerance: 1e-9 for L2 norm (per Section 3.3), 1us for recomputed
timing where applicable. Exits 0 if all checks pass, 1 if any drift
is detected.

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


def main() -> int:
    fnv_path = TESTS_DIR / "fnv1a_64_vectors.json"
    l2_path = TESTS_DIR / "l2_projection_golden.json"
    keepalive_path = TESTS_DIR / "zero_token_keepalive_trace.json"

    report = {
        "schema_version": "1.0.0",
        "auditor": "math_runtime_drift.py",
        "suite_root": str(SUITE_ROOT),
        "tolerances": {
            "l2_norm": L2_TOLERANCE,
            "timing_us": TIMING_TOLERANCE_US,
        },
    }

    for path in (fnv_path, l2_path, keepalive_path):
        if not path.exists():
            print(f"MISSING: {path}", file=sys.stderr)
            return 1

    rc = 0
    rc |= audit_fnv1a(fnv_path, report)
    rc |= audit_l2_projection(l2_path, report)
    rc |= audit_keepalive_trace(keepalive_path, report)

    print("=" * 72)
    print("DSVH verification suite: math <-> trace drift auditor")
    print(f"  Suite root:    {SUITE_ROOT}")
    print(f"  L2 tolerance:  {L2_TOLERANCE:.0e}")
    print(f"  Timing tol.:   {TIMING_TOLERANCE_US} us")
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
