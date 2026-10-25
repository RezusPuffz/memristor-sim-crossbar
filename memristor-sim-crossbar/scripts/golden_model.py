#!/usr/bin/env python3
"""Golden model: ideal crossbar outputs, and pass/fail against simulation.

Ideal output only:
    python3 golden_model.py --weights "2,-2;-1,3" --vin "0,0.1"

Check results, either a CSV of 'vin1,...,out1,...' rows (volts, amps) or
one psfascii DC operating point from Spectre (inputs given with --vin):
    python3 golden_model.py --weights "2,-2;-1,3" --check tests/tb_array2x2_v4_postlayout.csv
    python3 golden_model.py --weights "2,-2;-1,3" --vin "0,0.1" --check raw/dcop.dc
"""
import argparse
import csv
import re
import sys

from crossbar import ideal_outputs, parse_weights

TOL = 0.5e-9  # amps; ~1 sigma of Monte Carlo mismatch (0.43 nA)


def read_csv(path, rows, cols):
    cases = []
    with open(path) as f:
        for rec in csv.DictReader(f):
            vin = [float(rec[f"vin{i + 1}"]) for i in range(rows)]
            out = [float(rec[f"out{c + 1}"]) for c in range(cols)]
            cases.append((vin, out))
    return cases


def read_psfascii(path, vin, cols):
    """One DC operating point from 'spectre -format psfascii' (inputs from --vin)."""
    vals = dict(re.findall(r'"([^"]+)"\s+([-+0-9.eE]+)', open(path).read()))
    out = [float(vals[f"VOUT{c + 1}:p"]) for c in range(cols)]
    return [(vin, out)]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--vin", help="cell voltage per row in volts")
    ap.add_argument("--check", help="CSV or psfascii result file to compare")
    ap.add_argument("--tol", type=float, default=TOL, help="pass limit in amps")
    a = ap.parse_args()

    weights = parse_weights(a.weights)
    rows, cols = len(weights), len(weights[0])

    if not a.check:
        vin = [float(v) for v in a.vin.split(",")]
        for c, i in enumerate(ideal_outputs(weights, vin)):
            print(f"out{c + 1}: {i * 1e9:+.3f} nA")
        return

    if a.check.endswith(".csv"):
        cases = read_csv(a.check, rows, cols)
    else:
        cases = read_psfascii(a.check, [float(v) for v in a.vin.split(",")], cols)
    failures = 0
    for vin, sim in cases:
        ideal = ideal_outputs(weights, vin)
        for c, (s, g) in enumerate(zip(sim, ideal)):
            err = s - g
            ok = abs(err) <= a.tol
            failures += not ok
            print(f"vin={vin} out{c + 1}: sim {s * 1e9:+8.3f} nA  ideal {g * 1e9:+8.3f} nA  "
                  f"error {err * 1e12:+7.1f} pA  {'PASS' if ok else 'FAIL'}")
    print("ALL PASS" if failures == 0 else f"{failures} FAIL")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
