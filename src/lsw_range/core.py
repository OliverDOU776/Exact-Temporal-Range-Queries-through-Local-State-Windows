"""Exact extrema for interval rewards under a shared integer TV budget.

The local/global/gap plans are a readable Python adaptation of the paper's
D011 native operator (see docs/provenance.md), with exact rational weights.
No endpoints of the offset path are pinned.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from fractions import Fraction
import math
from numbers import Integral
from typing import Any, Iterable, Sequence


Score = int | Fraction
Bounds = tuple[Score, Score]


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    return int(value)


def _exact(value: Any, name: str) -> Score:
    """Treat decimal strings and floats as their printed decimal values."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a finite number")
    try:
        if isinstance(value, Integral):
            return int(value)
        number = value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    return number.numerator if number.denominator == 1 else number


def _domain(domain: Sequence[int]) -> tuple[int, int]:
    if len(domain) != 2:
        raise ValueError("domain must contain exactly two integer endpoints")
    a, b = (_integer(domain[0], "domain lower"), _integer(domain[1], "domain upper"))
    if a > b:
        raise ValueError("domain must be nonempty")
    return a, b


@dataclass(frozen=True)
class Interval:
    """Inclusive integer hit interval and a nonnegative exact row weight.

    An inverted interval is empty. Zero-weight rows may represent temporal masks.
    Nonconstant rows retained by the solver always have strictly positive weight.
    """

    lower: int
    upper: int
    weight: Score = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "lower", _integer(self.lower, "interval lower"))
        object.__setattr__(self, "upper", _integer(self.upper, "interval upper"))
        weight = _exact(self.weight, "weight")
        if weight < 0:
            raise ValueError("weights must be nonnegative")
        object.__setattr__(self, "weight", weight)

    def hit(self, state: int) -> bool:
        return self.lower <= state <= self.upper


@dataclass(frozen=True)
class Result:
    """One extremal pair for each requested budget, including duplicates."""

    bounds: tuple[Bounds, ...]
    budgets: tuple[int, ...]
    domain: tuple[int, int]
    method: str
    diagnostics: dict[str, Any]


@dataclass
class _Prepared:
    a: int
    b: int
    runs: list[Interval] = field(default_factory=list)
    fixed: Score = 0
    total: Score = 0
    n: int = 0
    active_rows: int = 0
    events: list[tuple[int, Score]] = field(default_factory=list)
    static: Bounds = (0, 0)


def _as_interval(row: Any) -> Interval:
    if isinstance(row, Interval):
        return row
    if isinstance(row, (tuple, list)) and len(row) in (2, 3):
        return Interval(*row)
    raise TypeError("each row must be an Interval or a (lower, upper[, weight]) sequence")


def _prepare(rows: Iterable[Interval], a: int, b: int) -> _Prepared:
    p = _Prepared(a, b)
    for raw in rows:
        row = _as_interval(raw)
        p.n += 1
        lo, hi = max(a, row.lower), min(b, row.upper)
        if row.weight == 0 or lo > hi:
            continue
        if lo == a and hi == b:
            p.fixed += row.weight
            continue
        p.active_rows += 1
        p.total += row.weight
        if p.runs and (p.runs[-1].lower, p.runs[-1].upper) == (lo, hi):
            p.runs[-1] = Interval(lo, hi, p.runs[-1].weight + row.weight)
        else:
            p.runs.append(Interval(lo, hi, row.weight))
    events: dict[int, Score] = {a: 0}
    for row in p.runs:
        events[row.lower] = events.get(row.lower, 0) + row.weight
        if row.upper < b:
            end = row.upper + 1
            events[end] = events.get(end, 0) - row.weight
    p.events = sorted(events.items())
    count = p.fixed
    low = high = None
    for _, change in p.events:
        count += change
        low = count if low is None else min(low, count)
        high = count if high is None else max(high, count)
    p.static = (low, high)
    return p


def _support(rows: Sequence[Interval], a: int, b: int) -> list[int]:
    states = {a, b}
    for row in rows:
        lo, hi = max(a, row.lower), min(b, row.upper)
        if lo > hi:
            continue
        for state in (lo - 1, lo, hi, hi + 1):
            if a <= state <= b:
                states.add(state)
    return sorted(states)


def _static_at(p: _Prepared, starts: Sequence[int]) -> list[Score]:
    result = []
    index, count = 0, p.fixed
    for start in starts:
        while index < len(p.events) and p.events[index][0] <= start:
            count += p.events[index][1]
            index += 1
        result.append(count)
    return result


def _budget_kernel(
    rows: Sequence[Interval], states: Sequence[int], fixed: Score,
    queries: Sequence[int], diagnostics: dict[str, Any],
) -> list[Bounds]:
    # Every run-state path costs at most (r-1)*span. Above this conservative
    # cap, reuse the terminal layer; no target-cost oracle is assumed free.
    cap = max(0, len(rows) - 1) * (states[-1] - states[0])
    maximum = min(queries[-1], cap)
    width = maximum + 1
    low = [[0] * width for _ in states]
    high = [[0] * width for _ in states]
    diagnostics["max_local_states"] = max(diagnostics["max_local_states"], len(states))
    for row in rows:
        # In-place left and right metric closures. Physical integer gaps, not
        # compressed state indices, consume the shared at-most budget.
        for j in range(1, len(states)):
            gap = states[j] - states[j - 1]
            for v in range(gap, width):
                low[j][v] = min(low[j][v], low[j - 1][v - gap])
                high[j][v] = max(high[j][v], high[j - 1][v - gap])
        for j in range(len(states) - 2, -1, -1):
            gap = states[j + 1] - states[j]
            for v in range(gap, width):
                low[j][v] = min(low[j][v], low[j + 1][v - gap])
                high[j][v] = max(high[j][v], high[j + 1][v - gap])
        for j, state in enumerate(states):
            if row.hit(state):
                for v in range(width):
                    low[j][v] += row.weight
                    high[j][v] += row.weight
        diagnostics["dp_cells"] += len(states) * width
    return [
        (fixed + min(layer[min(v, maximum)] for layer in low),
         fixed + max(layer[min(v, maximum)] for layer in high))
        for v in queries
    ]


@dataclass
class _Local:
    start: int
    end: int
    rows: list[Interval] = field(default_factory=list)
    # Only the gap baseline retains component states; local cover states are
    # created and released one window at a time.
    states: list[int] | None = None


def _local_bank(
    p: _Prepared, queries: Sequence[int], diagnostics: dict[str, Any],
    *, gaps: bool, specialize_v1: bool, local_support: bool,
) -> list[Bounds]:
    maximum = queries[-1]
    result = list(p.static for _ in queries)
    blocks = (p.b - p.a + maximum) // maximum
    locals_: dict[int, _Local] = {}
    states: list[int] = []
    component: list[int] = []
    starts: list[int] = []
    ends: list[int] = []
    if gaps:
        states = _support(p.runs, p.a, p.b)
        diagnostics["global_states"] = len(states)
        starts = [0]
        for j, state in enumerate(states):
            if j and state - states[j - 1] > maximum:
                ends.append(j - 1)
                starts.append(j)
            component.append(len(starts) - 1)
        ends.append(len(states) - 1)
    for row in p.runs:
        ids: set[int] = set()
        if not gaps and blocks == 1:
            ids.add(0)
        else:
            for edge in (row.lower, row.upper + 1):
                if not p.a < edge <= p.b:
                    continue
                if gaps:
                    j = bisect_left(states, edge)
                    # An interval boundary retains edge-1 and edge, hence is
                    # never separated by a >V gap for V>=1.
                    ids.add(component[j])
                else:
                    block = (edge - p.a) // maximum
                    for identifier in (block - 1, block):
                        if 0 <= identifier < blocks - 1:
                            start = p.a + identifier * maximum
                            end = min(p.b, p.a + (identifier + 2) * maximum - 1)
                            if start <= edge - 1 and edge <= end:
                                ids.add(identifier)
        for identifier in sorted(ids):
            if identifier not in locals_:
                if gaps:
                    section = states[starts[identifier]:ends[identifier] + 1]
                    locals_[identifier] = _Local(section[0], section[-1], states=section)
                else:
                    start = p.a if blocks == 1 else p.a + identifier * maximum
                    end = p.b if blocks == 1 else min(p.b, p.a + (identifier + 2) * maximum - 1)
                    locals_[identifier] = _Local(start, end)
            locals_[identifier].rows.append(row)
            diagnostics["run_incidences"] += 1
    ordered = [locals_[key] for key in sorted(locals_)]
    bases = _static_at(p, [local.start for local in ordered])
    for local, base in zip(ordered, bases):
        fixed = base - sum(row.weight for row in local.rows if row.hit(local.start))
        if not gaps and specialize_v1 and maximum == 1 and local.end == local.start + 1:
            total: Score = 0
            minimum_prefix: Score = 0
            maximum_prefix: Score = 0
            for row in local.rows:
                total += row.weight * (int(row.hit(local.end)) - int(row.hit(local.start)))
                minimum_prefix = min(minimum_prefix, total)
                maximum_prefix = max(maximum_prefix, total)
                diagnostics["prefix_steps"] += 1
            answers = [
                (base + min(0, total), base + max(0, total)) if v == 0 else
                (base + min(minimum_prefix, total - maximum_prefix),
                 base + max(maximum_prefix, total - minimum_prefix))
                for v in queries
            ]
            diagnostics["max_local_states"] = max(diagnostics["max_local_states"], 2)
        else:
            local_states = local.states
            if local_states is None:
                local_states = (_support(local.rows, local.start, local.end) if local_support
                                else list(range(local.start, local.end + 1)))
            answers = _budget_kernel(local.rows, local_states, fixed, queries, diagnostics)
        result = [(min(old[0], new[0]), max(old[1], new[1]))
                  for old, new in zip(result, answers)]
    diagnostics["active_windows"] = len(ordered)
    return result


def _literal_reference(
    rows: Sequence[Interval], a: int, b: int, queries: Sequence[int],
    diagnostics: dict[str, Any],
) -> list[Bounds]:
    """Uncontracted all-state/all-predecessor DP, for small validation cases."""
    if not rows:
        return [(0, 0)] * len(queries)
    maximum = min(queries[-1], max(0, len(rows) - 1) * (b - a))
    size = b - a + 1
    if size > 2000 or size * (maximum + 1) > 2_000_000 or len(rows) * size * size * (maximum + 1) > 50_000_000:
        raise ValueError("reference is a small-case oracle; use local, global, or gap for this request")
    states = list(range(a, b + 1))
    low = [[0] * (maximum + 1) for _ in states]
    high = [[0] * (maximum + 1) for _ in states]
    for row in rows:
        next_low, next_high = [], []
        for x in states:
            add = row.weight if row.hit(x) else 0
            lx, hx = [], []
            for v in range(maximum + 1):
                candidates = range(max(a, x - v), min(b, x + v) + 1)
                lx.append(add + min(low[y - a][v - abs(x - y)] for y in candidates))
                hx.append(add + max(high[y - a][v - abs(x - y)] for y in candidates))
            next_low.append(lx)
            next_high.append(hx)
        low, high = next_low, next_high
        diagnostics["dp_cells"] += len(states) * (maximum + 1)
    diagnostics["global_states"] = len(states)
    return [(min(layer[min(v, maximum)] for layer in low),
             max(layer[min(v, maximum)] for layer in high)) for v in queries]


def solve_intervals(
    rows: Iterable[Interval], *, domain: Sequence[int], budgets: Iterable[int],
    method: str = "local", specialize_v1: bool = True, local_support: bool = True,
) -> Result:
    """Return exact minimum/maximum weighted hits under shared TV budgets.

    A feasible path has one integer state per input row, in ``domain``, and
    ``sum(abs(x[i]-x[i-1])) <= budget``. Both endpoints are free. Methods are
    ``local`` (paper operator), ``global``, ``gap``, and ``reference`` (small
    independent literal DP). Budget order and duplicates are preserved.
    """
    if method not in {"local", "global", "gap", "reference"}:
        raise ValueError("method must be local, global, gap, or reference")
    a, b = _domain(domain)
    requests = tuple(_integer(v, "budget") for v in budgets)
    if not requests or min(requests) < 0:
        raise ValueError("budgets must be a nonempty collection of nonnegative integers")
    queries = sorted(set(requests))
    diagnostics: dict[str, Any] = {
        "input_rows": 0, "active_rows": 0, "weighted_runs": 0,
        "active_windows": 0, "run_incidences": 0, "global_states": 0,
        "max_local_states": 0, "dp_cells": 0, "prefix_steps": 0,
        "common_fast_path": False,
    }
    if method == "reference":
        original = [_as_interval(row) for row in rows]
        diagnostics["input_rows"] = len(original)
        answers = _literal_reference(original, a, b, queries, diagnostics)
    else:
        p = _prepare(rows, a, b)
        diagnostics.update(input_rows=p.n, active_rows=p.active_rows, weighted_runs=len(p.runs))
        if queries[-1] == 0 or not p.runs or p.static == (p.fixed, p.fixed + p.total):
            answers = [p.static] * len(queries)
            diagnostics["common_fast_path"] = True
        elif method == "global":
            states = _support(p.runs, a, b)
            diagnostics.update(global_states=len(states), active_windows=1, run_incidences=len(p.runs))
            answers = _budget_kernel(p.runs, states, p.fixed, queries, diagnostics)
        else:
            answers = _local_bank(p, queries, diagnostics, gaps=method == "gap",
                                  specialize_v1=specialize_v1, local_support=local_support)
    bank = dict(zip(queries, answers))
    return Result(tuple(bank[v] for v in requests), requests, (a, b), method, diagnostics)


def compile_interval(
    value: Any, lower: Any | None, upper: Any | None, domain: Sequence[int],
    lower_closed: bool = True, upper_closed: bool = True, weight: Any = 1,
) -> Interval:
    """Compile ``lower <= value - offset <= upper`` exactly on an integer domain.

    Set a closed flag to False for an open endpoint; None denotes an unbounded
    endpoint. Strings, Fraction, Decimal, and finite floats are accepted. A float
    is interpreted through its shortest decimal string, never rounded to an
    integer glucose reading.
    """
    a, b = _domain(domain)
    if not isinstance(lower_closed, bool) or not isinstance(upper_closed, bool):
        raise TypeError("endpoint closed flags must be boolean")
    g = _exact(value, "glucose value")
    left = None if lower is None else _exact(lower, "lower glucose endpoint")
    right = None if upper is None else _exact(upper, "upper glucose endpoint")
    if left is not None and right is not None and left > right:
        raise ValueError("lower glucose endpoint must not exceed upper endpoint")
    lo = a if right is None else (math.ceil(g - right) if upper_closed else math.floor(g - right) + 1)
    hi = b if left is None else (math.floor(g - left) if lower_closed else math.ceil(g - left) - 1)
    return Interval(max(a, lo), min(b, hi), weight)


def solve_glucose(
    values: Iterable[Any], *, lower: Any | None = 70, upper: Any | None = 140,
    domain: Sequence[int], budgets: Iterable[int], lower_closed: bool = True,
    upper_closed: bool = True, weights: Iterable[Any] | None = None,
    method: str = "local", specialize_v1: bool = True, local_support: bool = True,
) -> Result:
    """Compile ordered glucose values and solve their exact marginal extrema.

    Input order is temporal order. Weights of zero mask rows without resetting
    the shared budget. Missing/nonfinite values are rejected; callers choose
    their valid-sample policy explicitly before invoking this function.
    """
    def intervals() -> Iterable[Interval]:
        if weights is None:
            for value in values:
                yield compile_interval(value, lower, upper, domain, lower_closed, upper_closed)
        else:
            sentinel = object()
            from itertools import zip_longest
            for value, weight in zip_longest(values, weights, fillvalue=sentinel):
                if value is sentinel or weight is sentinel:
                    raise ValueError("weights must have one entry per glucose value")
                yield compile_interval(value, lower, upper, domain, lower_closed, upper_closed, weight)
    return solve_intervals(intervals(), domain=domain, budgets=budgets, method=method,
                           specialize_v1=specialize_v1, local_support=local_support)
