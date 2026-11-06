"""JSON command line interface for the exact range-query operator."""

from __future__ import annotations

import argparse
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
import sys

from . import __version__, solve_glucose, solve_intervals


def _json_number(value):
    if isinstance(value, Fraction):
        return value.numerator if value.denominator == 1 else str(value)
    raise TypeError(f"cannot encode {type(value).__name__}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exact range extrema under a shared integer total-variation budget.")
    parser.add_argument("input", help="JSON request file, or - for standard input")
    parser.add_argument("--method", choices=("local", "global", "gap", "reference"), default="local")
    parser.add_argument("--diagnostics", action="store_true", help="include structural counters (no timings)")
    parser.add_argument("--no-v1", action="store_true", help="use generic DP instead of the budget-one prefix formula")
    parser.add_argument("--all-local-states", action="store_true", help="use every local integer instead of local critical support")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    try:
        if args.input == "-":
            request = json.load(sys.stdin, parse_float=Decimal)
        else:
            with Path(args.input).open(encoding="utf-8") as handle:
                request = json.load(handle, parse_float=Decimal)
        if not isinstance(request, dict):
            raise ValueError("request must be a JSON object")
        allowed = {"domain", "budgets", "intervals", "glucose", "band", "weights", "description"}
        extra = set(request) - allowed
        if extra:
            raise ValueError(f"unknown request fields: {', '.join(sorted(extra))}")
        if "domain" not in request or "budgets" not in request:
            raise ValueError("request requires domain and budgets")
        if ("intervals" in request) == ("glucose" in request):
            raise ValueError("request requires exactly one of intervals or glucose")
        options = dict(domain=request["domain"], budgets=request["budgets"], method=args.method,
                       specialize_v1=not args.no_v1, local_support=not args.all_local_states)
        if "intervals" in request:
            if "weights" in request or "band" in request:
                raise ValueError("interval weights belong in each interval; band applies only to glucose")
            result = solve_intervals(request["intervals"], **options)
        else:
            band = request.get("band", {"lower": 70, "upper": 140})
            if not isinstance(band, dict) or set(band) - {"lower", "upper", "lower_closed", "upper_closed"}:
                raise ValueError("band permits lower, upper, lower_closed, and upper_closed")
            result = solve_glucose(request["glucose"], weights=request.get("weights"), **band, **options)
        output = {"method": result.method, "domain": result.domain,
                  "budgets": result.budgets, "bounds": result.bounds}
        if args.diagnostics:
            output["diagnostics"] = result.diagnostics
        print(json.dumps(output, default=_json_number, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"lsw-range: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
