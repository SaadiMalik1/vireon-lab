#!/usr/bin/env python3
"""
VIREON NL-005 Lab 002 - Loop Attack Benchmarks

Comprehensive benchmark suite for closed-loop neural stimulation system security.
Tests attack detection, response, and resilience across 8 benchmark categories.

Each benchmark runs 10 test variations scoring:
  - 4 pts: attack_effect  (measurable impact vs baseline)
  - 3 pts: detected       (monitor raises relevant alerts)
  - 3 pts: responded      (system enters SAFE_MODE or reduces stimulation)
"""

import sys
import os
import json
import argparse
from datetime import datetime

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "lab-001-closed-loop-simulator",
    ),
)
from closed_loop_simulator import ClosedLoopSystem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_grade(total_score: int) -> str:
    """Return letter grade based on total score out of 800."""
    if total_score >= 720:
        return "A"
    if total_score >= 640:
        return "B"
    if total_score >= 560:
        return "C"
    if total_score >= 480:
        return "D"
    return "F"


def _run_baseline(seed: int, num_cycles: int, vulnerable: bool) -> dict:
    """Run a clean simulation with no attacks for comparison."""
    sys = ClosedLoopSystem(seed=seed, vulnerable=vulnerable, num_cycles=num_cycles)
    return sys.run()


def _significant_change(val, baseline, threshold_pct: float = 0.05, min_abs: float = 0.1) -> bool:
    """Check if *val* differs from *baseline* by more than threshold."""
    if baseline == 0:
        return abs(val) > min_abs
    pct_change = abs(val - baseline) / abs(baseline)
    return pct_change > threshold_pct or abs(val - baseline) > min_abs


def _check_detection(results: dict) -> bool:
    """Return True if the monitor raised at least one alert."""
    monitor = results.get("monitor", {})
    total = monitor.get("total_alerts", 0)
    if total > 0:
        return True
    counts = monitor.get("alert_counts", {})
    if counts:
        return sum(counts.values()) > 0
    return False


def _check_response(results: dict) -> bool:
    """Return True if the system entered SAFE_MODE, reduced stimulation, or escalated."""
    security = results.get("security_events", [])
    for evt in security:
        evt_str = evt.get("event", "")
        resp_str = evt.get("response", "")
        # Check for SAFE_MODE entry via monitor_triggered events
        if evt_str == "monitor_triggered" and resp_str in (
            "SWITCH_OPEN_LOOP", "REDUCE_STIMULATION",
            "DISABLE_STIMULATION", "EMERGENCY_SHUTDOWN"
        ):
            return True
        if "SAFE_MODE" in evt_str or "safe_mode" in evt_str:
            return True
    # Check cycle log for SAFE_MODE state
    for entry in results.get("cycle_log_sample", []):
        if entry.get("state") == "SAFE_MODE":
            return True
    # Check final system state
    if results.get("final_state") == "SAFE_MODE":
        return True
    # Fallback: check if stim dropped significantly vs a reasonable threshold
    stats = results.get("statistics", {})
    stim_mean = stats.get("stim_mean_ma", 0)
    if stim_mean < 0.01:
        return True
    return False


def _build_test_result(
    test_id: int,
    params: dict,
    results: dict,
    baseline: dict,
    vulnerable: bool,
    full: bool,
    extra_score_logic=None,
) -> dict:
    """Build a single test result dict with scoring."""
    stats = results.get("statistics", {})
    b_stats = baseline.get("statistics", {})

    stim_mean = stats.get("stim_mean_ma", 0)
    b_stim_mean = b_stats.get("stim_mean_ma", 0)
    beta_mean = stats.get("beta_mean_db", 0)
    b_beta_mean = b_stats.get("beta_mean_db", 0)

    attack_effect = _significant_change(stim_mean, b_stim_mean) or _significant_change(
        beta_mean, b_beta_mean
    )

    if vulnerable:
        detected = _check_detection(results)
        responded = _check_response(results)
        # In vulnerable mode detection is expected to be weaker
        det_score = 3 if detected else 0
    else:
        detected = _check_detection(results)
        responded = _check_response(results)
        det_score = 3 if detected else 0

    # Scoring measures DEFENSE quality:
    #   4 pts if attack had NO effect (good defense)
    #   3 pts if system detected the attack (good defense)
    #   3 pts if system responded (good defense)
    eff_score = 4 if not attack_effect else 0
    resp_score = 3 if responded else 0

    if extra_score_logic:
        override = extra_score_logic(results, baseline, vulnerable)
        if isinstance(override, dict):
            if "attack_effect" in override:
                eff_score = 4 if not override["attack_effect"] else 0
                attack_effect = override["attack_effect"]
            if "detected" in override:
                det_score = 3 if override["detected"] else 0
                detected = override["detected"]
            if "responded" in override:
                resp_score = 3 if override["responded"] else 0
                responded = override["responded"]

    score = eff_score + det_score + resp_score

    details_parts = []
    if attack_effect:
        details_parts.append(
            f"stim {b_stim_mean:.4f}->{stim_mean:.4f}mA, "
            f"beta {b_beta_mean:.2f}->{beta_mean:.2f}dB"
        )
    else:
        details_parts.append("No significant effect vs baseline")
    details_parts.append(f"alerts={results.get('monitor', {}).get('total_alerts', 0)}")
    if full:
        details_parts.append(
            f"security_events={len(results.get('security_events', []))}"
        )
        details_parts.append(
            f"energy={results.get('energy', {}).get('battery_percent', 'N/A')}%"
        )
    details = "; ".join(details_parts)

    return {
        "test_id": test_id,
        "params": params,
        "attack_effect": attack_effect,
        "detected": detected,
        "responded": responded,
        "score": score,
        "details": details,
    }


def _make_benchmark(
    benchmark_id: str,
    tests: list,
    vulnerable: bool,
    seed: int,
    num_cycles: int,
    full: bool,
) -> dict:
    """Package test results into a benchmark summary."""
    total_score = sum(t["score"] for t in tests)
    max_score = len(tests) * 10
    return {
        "benchmark": benchmark_id,
        "tests": tests,
        "total_score": total_score,
        "max_score": max_score,
        "grade": get_grade(total_score * 8),
    }


def _save_json(data: dict, output_dir: str | None) -> None:
    """Save results to JSON file."""
    if output_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "attack_benchmark.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Results saved to {path}")


# ---------------------------------------------------------------------------
# CL-001: Sensor Spoofing Detection
# ---------------------------------------------------------------------------

def run_cl001(num_cycles: int = 1000, seed: int = 42, vulnerable: bool = False, full: bool = False) -> dict:
    """CL-001: Instantaneous sensor spoofing at various offsets."""
    offsets = [5, 10, 15, -5, -10, -15, 20, -20, 8, -8]
    baseline = _run_baseline(seed, num_cycles, vulnerable)
    tests = []

    for i, offset in enumerate(offsets):
        params = {"attack_type": "sensor_spoof", "offset_db": offset, "gradual": False}
        cls = ClosedLoopSystem(seed=seed, vulnerable=vulnerable, num_cycles=num_cycles)
        cls.set_attack("sensor_spoof", 200, 500, offset_db=offset, gradual=False)
        results = cls.run()
        tests.append(
            _build_test_result(i + 1, params, results, baseline, vulnerable, full)
        )

    return _make_benchmark("CL-001", tests, vulnerable, seed, num_cycles, full)


# ---------------------------------------------------------------------------
# CL-002: Adversarial Perturbation Resilience
# ---------------------------------------------------------------------------

def run_cl002(num_cycles: int = 1000, seed: int = 42, vulnerable: bool = False, full: bool = False) -> dict:
    """CL-002: Gradual sensor spoofing — adversarial perturbation."""
    offsets = [3, 5, 8, -3, -5, -8, 10, -10, 6, -6]
    baseline = _run_baseline(seed, num_cycles, vulnerable)
    tests = []

    for i, offset in enumerate(offsets):
        params = {"attack_type": "sensor_spoof", "offset_db": offset, "gradual": True}
        cls = ClosedLoopSystem(seed=seed, vulnerable=vulnerable, num_cycles=num_cycles)
        cls.set_attack("sensor_spoof", 200, 500, offset_db=offset, gradual=True)
        results = cls.run()
        tests.append(
            _build_test_result(i + 1, params, results, baseline, vulnerable, full)
        )

    return _make_benchmark("CL-002", tests, vulnerable, seed, num_cycles, full)


# ---------------------------------------------------------------------------
# CL-003: Controller Parameter Integrity
# ---------------------------------------------------------------------------

def run_cl003(num_cycles: int = 1000, seed: int = 42, vulnerable: bool = False, full: bool = False) -> dict:
    """CL-003: PI controller gain modification attacks."""
    pairs = [(2, 1), (5, 1), (10, 1), (1, 2), (1, 5), (1, 10), (3, 3), (5, 5), (2, 2), (0.5, 0.5)]
    baseline = _run_baseline(seed, num_cycles, vulnerable)
    tests = []

    for i, (kp_m, ki_m) in enumerate(pairs):
        params = {"attack_type": "gain_modify", "kp_mult": kp_m, "ki_mult": ki_m, "gradual": False}
        cls = ClosedLoopSystem(seed=seed, vulnerable=vulnerable, num_cycles=num_cycles)
        cls.set_attack("gain_modify", 200, 500, kp_mult=kp_m, ki_mult=ki_m, gradual=False)
        results = cls.run()

        def score_logic(res, bas, vuln, _kp=kp_m, _ki=ki_m):
            has_tamper = any(
                e.get("event") == "parameter_tamper"
                for e in res.get("security_events", [])
            )
            stim = res.get("statistics", {}).get("stim_mean_ma", 0)
            b_stim = bas.get("statistics", {}).get("stim_mean_ma", 0)
            eff = _significant_change(stim, b_stim) or has_tamper
            return {"attack_effect": eff, "detected": has_tamper}

        tests.append(
            _build_test_result(
                i + 1, params, results, baseline, vulnerable, full, score_logic
            )
        )

    return _make_benchmark("CL-003", tests, vulnerable, seed, num_cycles, full)


# ---------------------------------------------------------------------------
# CL-004: Setpoint Integrity
# ---------------------------------------------------------------------------

def run_cl004(num_cycles: int = 1000, seed: int = 42, vulnerable: bool = False, full: bool = False) -> dict:
    """CL-004: Setpoint modification attacks."""
    setpoints = [5, -5, 10, -10, 15, -15, 3, -3, 8, -8]
    baseline = _run_baseline(seed, num_cycles, vulnerable)
    tests = []

    for i, sp in enumerate(setpoints):
        params = {"attack_type": "setpoint_modify", "setpoint_db": sp, "gradual": False}
        cls = ClosedLoopSystem(seed=seed, vulnerable=vulnerable, num_cycles=num_cycles)
        cls.set_attack("setpoint_modify", 200, 500, setpoint_db=sp, gradual=False)
        results = cls.run()

        def score_logic(res, bas, vuln, _sp=sp):
            has_tamper = any(
                e.get("event") == "parameter_tamper"
                for e in res.get("security_events", [])
            )
            stim = res.get("statistics", {}).get("stim_mean_ma", 0)
            b_stim = bas.get("statistics", {}).get("stim_mean_ma", 0)
            eff = _significant_change(stim, b_stim) or has_tamper
            return {"attack_effect": eff, "detected": has_tamper}

        tests.append(
            _build_test_result(
                i + 1, params, results, baseline, vulnerable, full, score_logic
            )
        )

    return _make_benchmark("CL-004", tests, vulnerable, seed, num_cycles, full)


# ---------------------------------------------------------------------------
# CL-005: Energy Depletion Detection
# ---------------------------------------------------------------------------

def run_cl005(num_cycles: int = 1000, seed: int = 42, vulnerable: bool = False, full: bool = False) -> dict:
    """CL-005: Energy flood attacks of varying durations."""
    durations = [100, 200, 300, 400, 500, 600, 150, 250, 350, 450]
    baseline = _run_baseline(seed, num_cycles, vulnerable)
    b_energy = baseline.get("energy", {})
    b_power = b_energy.get("avg_power_uw", 0)
    b_battery = b_energy.get("battery_percent", 100)
    tests = []

    for i, dur in enumerate(durations):
        start = 200
        end = min(start + dur, num_cycles)
        params = {"attack_type": "energy_flood", "start_cycle": start, "end_cycle": end}
        cls = ClosedLoopSystem(seed=seed, vulnerable=vulnerable, num_cycles=num_cycles)
        cls.set_attack("energy_flood", start, end)
        results = cls.run()

        def score_logic(res, bas, vuln, _bp=b_power, _bb=b_battery):
            eng = res.get("energy", {})
            power = eng.get("avg_power_uw", 0)
            battery = eng.get("battery_percent", 100)
            power_rise = _bp > 0 and (power - _bp) / _bp > 0.1
            battery_drop = battery < _bb - 1
            return {"attack_effect": power_rise or battery_drop}

        tests.append(
            _build_test_result(
                i + 1, params, results, baseline, vulnerable, full, score_logic
            )
        )

    return _make_benchmark("CL-005", tests, vulnerable, seed, num_cycles, full)


# ---------------------------------------------------------------------------
# CL-006: Safety Monitor Evasion Detection
# ---------------------------------------------------------------------------

def run_cl006(num_cycles: int = 1000, seed: int = 42, vulnerable: bool = False, full: bool = False) -> dict:
    """CL-006: Compare detection with and without monitor evasion.

    Tests 1-5: attack + monitor_evasion
    Tests 6-10: same attack without evasion (control)
    """
    attack_configs = [
        ("sensor_spoof", {"offset_db": 10, "gradual": False}),
        ("gain_modify", {"kp_mult": 5, "ki_mult": 1, "gradual": False}),
        ("setpoint_modify", {"setpoint_db": 10, "gradual": False}),
        ("energy_flood", {}),
        ("delay_inject", {"delay_cycles": 10}),
    ]
    baseline = _run_baseline(seed, num_cycles, vulnerable)
    tests = []

    # Tests 1-5: attacks WITH evasion
    for i, (atk_type, atk_params) in enumerate(attack_configs):
        params = {"attack_type": atk_type, "with_evasion": True, **atk_params}
        cls = ClosedLoopSystem(seed=seed, vulnerable=vulnerable, num_cycles=num_cycles)
        cls.set_attack(atk_type, 200, 500, **atk_params)
        cls.set_attack("monitor_evasion", 200, 500)
        results = cls.run()

        def score_logic(res, bas, vuln):
            det = _check_detection(res)
            if not vuln:
                # Secure mode: evasion should reduce/eliminate detection
                # If still detected despite evasion, that is good for security
                pass
            return {}

        tests.append(
            _build_test_result(
                i + 1, params, results, baseline, vulnerable, full, score_logic
            )
        )

    # Tests 6-10: same attacks WITHOUT evasion (control)
    for i, (atk_type, atk_params) in enumerate(attack_configs):
        params = {"attack_type": atk_type, "with_evasion": False, **atk_params}
        cls = ClosedLoopSystem(seed=seed, vulnerable=vulnerable, num_cycles=num_cycles)
        cls.set_attack(atk_type, 200, 500, **atk_params)
        results = cls.run()
        tests.append(
            _build_test_result(i + 6, params, results, baseline, vulnerable, full)
        )

    # Post-hoc comparison scoring adjustment
    if len(tests) == 10:
        for i in range(5):
            evaded = tests[i]
            plain = tests[i + 5]
            if not vulnerable:
                # Secure mode: if plain attack detected but evaded one is not, evasion worked
                # Both should ideally be detected, but evasion makes it harder
                if plain["detected"] and not evaded["detected"]:
                    # Evasion successfully hid the attack — lower detection score for evaded
                    evaded["detected"] = False
                    evaded["score"] = (4 if not evaded["attack_effect"] else 0) + 0 + (
                        3 if evaded["responded"] else 0
                    )
                elif plain["detected"] and evaded["detected"]:
                    # Both detected — secure monitor is robust
                    pass

    return _make_benchmark("CL-006", tests, vulnerable, seed, num_cycles, full)


# ---------------------------------------------------------------------------
# CL-007: Protocol-Loop Interaction Security
# ---------------------------------------------------------------------------

def run_cl007(num_cycles: int = 1000, seed: int = 42, vulnerable: bool = False, full: bool = False) -> dict:
    """CL-007: Delay injection attacks at various magnitudes."""
    delays = [2, 3, 5, 8, 10, 15, 20, 3, 5, 7]
    baseline = _run_baseline(seed, num_cycles, vulnerable)
    tests = []

    for i, delay in enumerate(delays):
        params = {"attack_type": "delay_inject", "delay_cycles": delay}
        cls = ClosedLoopSystem(seed=seed, vulnerable=vulnerable, num_cycles=num_cycles)
        cls.set_attack("delay_inject", 200, 500, delay_cycles=delay)
        results = cls.run()

        def score_logic(res, bas, vuln):
            # Delay attacks should cause instability — check stim variance
            stats = res.get("statistics", {})
            b_stats = bas.get("statistics", {})
            stim = stats.get("stim_mean_ma", 0)
            b_stim = b_stats.get("stim_mean_ma", 0)
            stim_max = stats.get("stim_max_ma", 0)
            b_max = b_stats.get("stim_max_ma", 0)
            effect = _significant_change(stim, b_stim) or _significant_change(
                stim_max, b_max, threshold_pct=0.05, min_abs=0.01
            )
            return {"attack_effect": effect}

        tests.append(
            _build_test_result(
                i + 1, params, results, baseline, vulnerable, full, score_logic
            )
        )

    return _make_benchmark("CL-007", tests, vulnerable, seed, num_cycles, full)


# ---------------------------------------------------------------------------
# CL-008: Forensic Analysis Capability
# ---------------------------------------------------------------------------

def run_cl008(num_cycles: int = 1000, seed: int = 42, vulnerable: bool = False, full: bool = False) -> dict:
    """CL-008: Verify security_events are populated for various attacks."""
    attack_configs = [
        ("sensor_spoof", {"offset_db": 10, "gradual": False}),
        ("sensor_spoof", {"offset_db": 5, "gradual": True}),
        ("gain_modify", {"kp_mult": 5, "ki_mult": 1, "gradual": False}),
        ("setpoint_modify", {"setpoint_db": 10, "gradual": False}),
        ("energy_flood", {}),
        ("delay_inject", {"delay_cycles": 10}),
        ("feedback_bypass", {}),
        ("monitor_evasion", {}),
        ("sensor_spoof", {"offset_db": -15, "gradual": False}),
        ("gain_modify", {"kp_mult": 0.5, "ki_mult": 0.5, "gradual": True}),
    ]
    baseline = _run_baseline(seed, num_cycles, vulnerable)
    tests = []

    for i, (atk_type, atk_params) in enumerate(attack_configs):
        params = {"attack_type": atk_type, **atk_params}
        cls = ClosedLoopSystem(seed=seed, vulnerable=vulnerable, num_cycles=num_cycles)
        cls.set_attack(atk_type, 200, 500, **atk_params)
        results = cls.run()

        def score_logic(res, bas, vuln, _atk=atk_type):
            events = res.get("security_events", [])
            has_events = len(events) >= 1
            # CL-008 (forensics): detected = has forensic events
            # attack_effect: use default stim/beta comparison (not forensic presence)
            return {"detected": has_events}

        tests.append(
            _build_test_result(
                i + 1, params, results, baseline, vulnerable, full, score_logic
            )
        )

    return _make_benchmark("CL-008", tests, vulnerable, seed, num_cycles, full)


# ---------------------------------------------------------------------------
# Aggregators
# ---------------------------------------------------------------------------

BENCHMARK_FUNCS = {
    "CL-001": run_cl001,
    "CL-002": run_cl002,
    "CL-003": run_cl003,
    "CL-004": run_cl004,
    "CL-005": run_cl005,
    "CL-006": run_cl006,
    "CL-007": run_cl007,
    "CL-008": run_cl008,
}


def run_all_benchmarks(
    num_cycles: int = 1000,
    seed: int = 42,
    vulnerable: bool = False,
    full: bool = False,
    output_dir: str | None = None,
) -> dict:
    """Run all 8 benchmarks and return aggregated results."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "num_cycles": num_cycles,
            "seed": seed,
            "vulnerable": vulnerable,
            "full": full,
        },
        "benchmarks": [],
        "summary": {
            "total_score": 0,
            "max_score": 0,
            "grade": "F",
        },
    }

    for bm_id in sorted(BENCHMARK_FUNCS.keys()):
        print(f"Running {bm_id}...", flush=True)
        bm_result = BENCHMARK_FUNCS[bm_id](
            num_cycles=num_cycles, seed=seed, vulnerable=vulnerable, full=full
        )
        results["benchmarks"].append(bm_result)
        results["summary"]["total_score"] += bm_result["total_score"]
        results["summary"]["max_score"] += bm_result["max_score"]

    results["summary"]["grade"] = get_grade(results["summary"]["total_score"])

    _save_json(results, output_dir)

    return results


def run_vulnerable_comparison(
    num_cycles: int = 1000, seed: int = 42, output_dir: str | None = None
) -> dict:
    """Run all benchmarks in both secure and vulnerable modes for comparison."""
    print("=" * 60)
    print("Running SECURE mode benchmarks...")
    print("=" * 60)
    secure = run_all_benchmarks(
        num_cycles=num_cycles, seed=seed, vulnerable=False, output_dir=None
    )

    print("")
    print("=" * 60)
    print("Running VULNERABLE mode benchmarks...")
    print("=" * 60)
    vulnerable = run_all_benchmarks(
        num_cycles=num_cycles, seed=seed, vulnerable=True, output_dir=None
    )

    comparison = {
        "timestamp": datetime.now().isoformat(),
        "config": {"num_cycles": num_cycles, "seed": seed},
        "secure": {
            "total_score": secure["summary"]["total_score"],
            "max_score": secure["summary"]["max_score"],
            "grade": secure["summary"]["grade"],
            "benchmarks": {
                b["benchmark"]: {"score": b["total_score"], "max": b["max_score"]}
                for b in secure["benchmarks"]
            },
        },
        "vulnerable": {
            "total_score": vulnerable["summary"]["total_score"],
            "max_score": vulnerable["summary"]["max_score"],
            "grade": vulnerable["summary"]["grade"],
            "benchmarks": {
                b["benchmark"]: {"score": b["total_score"], "max": b["max_score"]}
                for b in vulnerable["benchmarks"]
            },
        },
        "delta": {},
    }

    for b in secure["benchmarks"]:
        bid = b["benchmark"]
        s_score = b["total_score"]
        v_score = vulnerable["vulnerable"]["benchmarks"][bid]["score"]
        comparison["delta"][bid] = v_score - s_score

    comparison["delta"]["total"] = (
        vulnerable["summary"]["total_score"] - secure["summary"]["total_score"]
    )

    # Save the full comparison
    if output_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "attack_benchmark.json")
    with open(path, "w") as f:
        json.dump(comparison, f, indent=2, default=str)
    print(f"Comparison saved to {path}")

    return comparison


# ---------------------------------------------------------------------------
# Pretty Printer
# ---------------------------------------------------------------------------

def print_results(results: dict) -> None:
    """Print benchmark results in a formatted table."""
    if "comparison" in results or "secure" in results:
        _print_comparison(results)
        return

    print("")
    print("=" * 72)
    print("  VIREON NL-005 — Lab 002: Loop Attack Benchmark Results")
    print("=" * 72)

    cfg = results.get("config", {})
    print(f"  Config: cycles={cfg.get('num_cycles')}, seed={cfg.get('seed')}, "
          f"vulnerable={cfg.get('vulnerable')}, full={cfg.get('full')}")
    print("")

    header = f"  {'Benchmark':<12} {'Score':>6} / {'Max':>4}   {'Grade':<4}   {'Tests':>5}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for bm in results.get("benchmarks", []):
        bid = bm["benchmark"]
        score = bm["total_score"]
        mx = bm["max_score"]
        grade = bm["grade"]
        n = len(bm["tests"])
        print(f"  {bid:<12} {score:>6} / {mx:>4}   {grade:<4}   {n:>5}")

    summary = results.get("summary", {})
    total = summary.get("total_score", 0)
    mx_total = summary.get("max_score", 0)
    grade = summary.get("grade", "F")
    print("  " + "-" * (len(header) - 2))
    print(f"  {'TOTAL':<12} {total:>6} / {mx_total:>4}   {grade:<4}")
    print("=" * 72)

    # Per-test details
    for bm in results.get("benchmarks", []):
        print(f"\n  --- {bm['benchmark']} Details ---")
        print(f"  {'ID':>3}  {'Effect':>6}  {'Detect':>6}  {'Respond':>7}  {'Score':>5}  Details")
        print(f"  {'---':>3}  {'------':>6}  {'------':>6}  {'-------':>7}  {'-----':>5}  -------")
        for t in bm["tests"]:
            eff = "YES" if t["attack_effect"] else "no"
            det = "YES" if t["detected"] else "no"
            rsp = "YES" if t["responded"] else "no"
            print(
                f"  {t['test_id']:>3}  {eff:>6}  {det:>6}  {rsp:>7}  {t['score']:>5}  {t['details']}"
            )


def _print_comparison(results: dict) -> None:
    """Print vulnerable vs secure comparison."""
    print("")
    print("=" * 72)
    print("  VIREON NL-005 — Lab 002: Secure vs Vulnerable Comparison")
    print("=" * 72)
    print("")

    header = f"  {'Benchmark':<12} {'Secure':>7}  {'Vuln':>7}  {'Delta':>7}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    sec = results["secure"]
    vul = results["vulnerable"]
    for bid in sorted(sec["benchmarks"].keys()):
        s = sec["benchmarks"][bid]["score"]
        v = vul["benchmarks"][bid]["score"]
        d = results["delta"].get(bid, 0)
        print(f"  {bid:<12} {s:>7}  {v:>7}  {d:>+7}")

    print("  " + "-" * (len(header) - 2))
    total_d = results["delta"].get("total", 0)
    print(
        f"  {'TOTAL':<12} {sec['total_score']:>7}  {vul['total_score']:>7}  {total_d:>+7}"
    )
    print(f"  Secure Grade: {sec['grade']}  |  Vulnerable Grade: {vul['grade']}")
    print("=" * 72)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="VIREON NL-005 Lab 002 — Loop Attack Benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python loop_attacks.py                        # Run all benchmarks (secure)
  python loop_attacks.py --benchmark CL-001     # Run only CL-001
  python loop_attacks.py --vulnerable            # Run in vulnerable mode
  python loop_attacks.py --full                  # Full detail output
  python loop_attacks.py --compare               # Secure vs vulnerable comparison
  python loop_attacks.py --num_cycles 500        # Shorter simulation
  python loop_attacks.py --output_dir /tmp/out   # Custom output directory

Available benchmarks: CL-001 through CL-008
""",
    )
    parser.add_argument(
        "--benchmark",
        "-b",
        choices=list(BENCHMARK_FUNCS.keys()) + ["all"],
        default="all",
        help="Benchmark to run (default: all)",
    )
    parser.add_argument(
        "--full", "-f", action="store_true", help="Include full detail in output"
    )
    parser.add_argument(
        "--vulnerable",
        "-v",
        action="store_true",
        help="Run in vulnerable mode (disables security)",
    )
    parser.add_argument(
        "--compare",
        "-c",
        action="store_true",
        help="Run secure vs vulnerable comparison",
    )
    parser.add_argument(
        "--output_dir", "-o", type=str, default=None, help="Output directory for JSON results"
    )
    parser.add_argument(
        "--num_cycles", "-n", type=int, default=1000, help="Number of simulation cycles (default: 1000)"
    )
    parser.add_argument(
        "--seed", "-s", type=int, default=42, help="Random seed (default: 42)"
    )

    args = parser.parse_args()

    if args.compare:
        results = run_vulnerable_comparison(
            num_cycles=args.num_cycles, seed=args.seed, output_dir=args.output_dir
        )
        print_results(results)
        return

    if args.benchmark == "all":
        results = run_all_benchmarks(
            num_cycles=args.num_cycles,
            seed=args.seed,
            vulnerable=args.vulnerable,
            full=args.full,
            output_dir=args.output_dir,
        )
    else:
        bm_func = BENCHMARK_FUNCS[args.benchmark]
        bm_result = bm_func(
            num_cycles=args.num_cycles,
            seed=args.seed,
            vulnerable=args.vulnerable,
            full=args.full,
        )
        results = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "num_cycles": args.num_cycles,
                "seed": args.seed,
                "vulnerable": args.vulnerable,
                "full": args.full,
            },
            "benchmarks": [bm_result],
            "summary": {
                "total_score": bm_result["total_score"],
                "max_score": bm_result["max_score"],
                "grade": bm_result["grade"],
            },
        }
        _save_json(results, args.output_dir)

    print_results(results)


if __name__ == "__main__":
    main()
