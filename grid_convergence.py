"""Estimate spatial discretization error from a three-grid refinement study."""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

SAFETY_FACTOR = 1.25
RATIO_TOLERANCE = 1e-3


def read_grids(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream, strict=True)
        if rows.fieldnames != ["spacing", "value"]:
            raise ValueError("expected the CSV header spacing,value")
        grids = []
        for row in rows:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"line {rows.line_num}: expected two columns")
            try:
                grids.append((float(row["spacing"]), float(row["value"])))
            except ValueError as exc:
                raise ValueError(f"line {rows.line_num}: expected two numbers") from exc
    return grids


def analyze(grids):
    """Return Richardson and GCI estimates for nearly uniform refinement ratios."""
    if len(grids) != 3:
        raise ValueError("exactly three grid results are required")
    if any(not (math.isfinite(h) and h > 0 and math.isfinite(q)) for h, q in grids):
        raise ValueError("spacings must be positive and all inputs must be finite")

    (h_f, q_f), (h_m, q_m), (h_c, q_c) = sorted(grids)
    if not h_f < h_m < h_c:
        raise ValueError("grid spacings must be distinct")
    r_f, r_c = h_m / h_f, h_c / h_m
    if min(r_f, r_c) <= 1 or not math.isfinite(max(r_f, r_c)):
        raise ValueError("refinement ratios must be finite and greater than 1")
    if not math.isclose(r_f, r_c, rel_tol=RATIO_TOLERANCE):
        raise ValueError(f"refinement ratios {r_f:.8g} and {r_c:.8g} differ by more than 0.1%")

    delta_f, delta_c = q_m - q_f, q_c - q_m
    if not all(map(math.isfinite, (delta_f, delta_c))):
        raise ValueError("differences overflowed; rescale the quantity before analysis")

    result = {
        "status": "converging",
        "fine_value": q_f,
        "fine_refinement_ratio": r_f,
        "coarse_refinement_ratio": r_c,
        "observed_order": None,
        "extrapolated_value": None,
        "fine_gci_absolute": None,
        "fine_gci_percent": None,
    }
    if delta_f == 0 or delta_c == 0:
        result["status"] = "repeated-values"
    elif (delta_f > 0) != (delta_c > 0):
        result["status"] = "oscillatory"
    elif abs(delta_c) <= abs(delta_f):
        result["status"] = "differences-not-shrinking"

    if result["status"] != "converging":
        return result

    # Using the difference of magnitudes avoids subtracting 1 from a rounded ratio.
    gap = abs(delta_c) - abs(delta_f)
    step = gap / abs(delta_f)
    log_growth = (
        math.log1p(step)
        if math.isfinite(step)
        else math.log(abs(delta_c)) - math.log(abs(delta_f))
    )
    order = log_growth / math.log(r_f)
    correction = (abs(delta_f) / gap) * delta_f if math.isfinite(step) else delta_f / step
    extrapolated = q_f - correction
    gci = SAFETY_FACTOR * abs(correction)
    gci_percent = (gci / abs(q_f)) * 100 if q_f != 0 else None
    if not all(math.isfinite(v) for v in (order, extrapolated, gci)):
        raise ValueError("estimates overflowed; inspect the grid differences or rescale the quantity")
    if gci_percent is not None and not math.isfinite(gci_percent):
        gci_percent = None
    result.update(
        observed_order=order,
        extrapolated_value=extrapolated,
        fine_gci_absolute=gci,
        fine_gci_percent=gci_percent,
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="three rows with spacing,value columns")
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    args = parser.parse_args(argv)
    try:
        result = analyze(read_grids(args.csv))
    except (OSError, csv.Error, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    if args.json:
        print(json.dumps(result, indent=2, allow_nan=False))
    else:
        for key, value in result.items():
            display = "n/a" if value is None else f"{value:.8g}" if isinstance(value, float) else value
            print(f"{key:>26}  {display}")
    return 0 if result["status"] == "converging" else 1


if __name__ == "__main__":
    sys.exit(main())
