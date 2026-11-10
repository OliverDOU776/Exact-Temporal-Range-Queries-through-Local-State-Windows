#!/usr/bin/env python3
"""Check the public BIG001 count example without bundling readings.

Requires the official BIG IDEAs Lab version 1.1.3 001/Dexcom_001.csv.
See docs/api.md for dataset attribution, DOI, access, and license context.
"""

import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path

from lsw_range import solve_glucose


SOURCE_SHA256 = "6333b21185f23834ab929e5d8bf9045bbed6268cdfd5030adab3c7d5ef689ef5"
BUDGETS = [0, 1, 4, 16, 64]
EXPECTED = ((63, 91), (63, 91), (63, 92), (63, 96), (51, 96))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="official unmodified 001/Dexcom_001.csv")
    args = parser.parse_args()
    try:
        if hashlib.sha256(args.csv.read_bytes()).hexdigest() != SOURCE_SHA256:
            raise ValueError("CSV does not match the pinned original version 1.1.3 source")
        glucose, times = [], []
        with args.csv.open(newline="", encoding="utf-8-sig") as handle:
            for line, row in enumerate(csv.DictReader(handle), start=2):
                if 14 <= line <= 109:
                    if row["Event Type"] != "EGV":
                        raise ValueError("fixed source window contains a non-EGV row")
                    glucose.append(row["Glucose Value (mg/dL)"].strip())
                    times.append(datetime.fromisoformat(row["Timestamp (YYYY-MM-DDThh:mm:ss)"].strip()))
        if len(glucose) != 96 or (times[-1] - times[0]).total_seconds() != 28499:
            raise ValueError("fixed source window identity does not match")
        if any(not 270 <= (right - left).total_seconds() <= 330 for left, right in zip(times, times[1:])):
            raise ValueError("fixed source window fails the original cadence rule")
        for method in ("local", "global", "gap"):
            result = solve_glucose(glucose, lower=70, upper=140, domain=(-30, 30), budgets=BUDGETS, method=method)
            if result.bounds != EXPECTED:
                raise ValueError(f"{method} disagrees with the accepted fixed-case count endpoints")
        print(json.dumps({"example": "BIG001, 96 samples, closed TITR [70,140]",
                          "domain": [-30, 30], "budgets": BUDGETS,
                          "bounds": EXPECTED, "methods_checked": ["local", "global", "gap"]}, indent=2))
    except (OSError, KeyError, ValueError) as exc:
        parser.exit(2, f"verify_big001: {exc}\n")


if __name__ == "__main__":
    main()
