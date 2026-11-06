# Python API and JSON requests

Install with Python 3.10 or newer:

```bash
python -m pip install -e .
python -m lsw_range examples/synthetic.json
lsw-range examples/glucose_synthetic.json --diagnostics
python -m unittest discover -s tests -v
```

The package uses only the Python standard library. Installation needs setuptools; a checkout can also be run with `PYTHONPATH=src` without installation.

## Interval queries

```python
from fractions import Fraction
from lsw_range import Interval, solve_intervals

answer = solve_intervals(
    [Interval(0, 0, Fraction(1, 3)), Interval(1, 1, 2)],
    domain=(0, 1), budgets=[0, 1, 0],
)
assert answer.bounds == ((Fraction(1, 3), 2), (0, Fraction(7, 3)), (Fraction(1, 3), 2))
```

Rows may be `Interval(lower, upper, weight=1)` objects or `(lower, upper[, weight])` sequences. Bounds and states must be integers. Inverted intervals are empty. Weights are nonnegative finite exact numbers; zero weights mask rows. Integer and `Fraction` weights are exact; `Decimal`, decimal strings, and finite floats are interpreted through their decimal string value. For original binary floating-point semantics, pass `Fraction.from_float(value)` explicitly. Negative weights are rejected.

`Result.bounds` is a tuple containing `(minimum, maximum)` for every budget, in its original order. `Result.budgets`, `.domain`, `.method`, and `.diagnostics` describe the request and structural work. Each budget is a nonnegative integer; the request must contain at least one budget. At zero, every constant offset in the domain is feasible, rather than only offset zero. Both temporal endpoints are free. Zero-reward gaps do not reset the shared budget. The extrema do not assert that every score between them is attainable, or that different predicates' extrema share one attaining path.

## Glucose bands

```python
from lsw_range import solve_glucose

result = solve_glucose(
    ["69.5", "70", "138", "141", "142.5", "71"],
    lower=70, upper=140, lower_closed=True, upper_closed=True,
    domain=(-3, 3), budgets=[0, 1, 4, 1],
    weights=[1, 1, 0, 1, 1, 1],
)
```

The corrected value is **glucose minus offset**. `compile_interval(value, lower, upper, domain, ...)` exposes the exact endpoint compilation separately. Use `None` for an unbounded endpoint; set either closed flag to `False` for an open endpoint. Decimal glucose observations retain their fractional value. Missing or nonfinite observations are rejected, so the caller selects valid samples and their temporal order explicitly. Timestamps do not change transition weights or impose rate constraints.

For a selected unit-count mask with fixed denominator `N > 0`, percentage extrema are `100 * minimum / N` and `100 * maximum / N`. This counts samples, not interpolated elapsed time. An empty mask returns `(0,0)` counts; its percentage is unavailable. No clinical calibration of the offset domain or budget is implied.

## Physical plans

| `method` | State processing |
| --- | --- |
| `local` (default) | Sparse overlapping state windows; weighted prefix formula when maximum budget is one |
| `global` | Shared-budget recurrence on global critical support |
| `gap` | Components of global critical support split at physical gaps exceeding the maximum budget |
| `reference` | Literal original-row/all-state/all-predecessor DP for small validation cases |

For `local`, `specialize_v1=False` disables the prefix specialization. `local_support=False` uses all local integers instead of critical support. Both switches retain exact results. No automatic performance selector is supplied; larger budgets can favor the global/gap plans. The native historical local state choice was all local integers, so Python defaults are not a claim of identical implementation timing.

The literal reference takes `O(n |D|²(V+1))` work and `O(|D|(V+1))` memory before a conservative saturation cap. It is guarded to at most 2,000 states, 2,000,000 state/budget cells, and an upper work estimate of 50,000,000 operations. Larger requests raise `ValueError` before dense allocation. Empty input returns zero without state enumeration. Optimized plans do not enumerate the raw domain; the local all-integer option enumerates only its active windows.

## JSON command line

An interval request contains `domain`, `budgets`, and `intervals`, as shown in [synthetic.json](../examples/synthetic.json). A glucose request contains `domain`, `budgets`, `glucose`, optional `weights`, and optional `band`, as shown in [glucose_synthetic.json](../examples/glucose_synthetic.json). `band` fields are `lower`, `upper`, `lower_closed`, and `upper_closed`; JSON `null` denotes an unbounded endpoint. The default band is closed `[70,140]`.

```bash
python -m lsw_range examples/synthetic.json --method global
python -m lsw_range examples/synthetic.json --all-local-states --no-v1
python -m lsw_range - < examples/glucose_synthetic.json
```

Output contains `method`, `domain`, `budgets`, and `bounds`. Add `--diagnostics` for structural counters; no timing claims are emitted. Integer scores remain JSON integers. Nonintegral exact rational scores are JSON strings such as `"7/3"`. Decimal JSON tokens are read exactly through `Decimal`. Invalid requests exit with status 2. There is no interactive network call.

## Optional fixed BIG001 example

No patient readings are bundled. To check the manuscript's 96-sample example, obtain **BIG IDEAs Lab Glycemic Variability and Wearable Device Data**, PhysioNet version 1.1.3, by Peter Cho, Juseong Kim, Brinnae Bent, and Jessilyn Dunn: [dataset DOI](https://doi.org/10.13026/aw6y-fc44). Follow the dataset's access, attribution, and [ODC Attribution License (ODC-By) requirements](assets/BIG_IDEAs_ODC-By.txt). Dataset terms apply independently of this repository's code permissions.

With the original `001/Dexcom_001.csv` available locally:

```bash
python examples/verify_big001.py /path/to/001/Dexcom_001.csv
```

The verifier pins the source CSV SHA-256, reads original file lines 14–109, validates EGV rows and timestamp cadence, and compares the three optimized Python plans. It prints only count extrema. Closed TITR `[70,140]`, domain `[-30,30]`, budgets `[0,1,4,16,64]` must return `[[63,91],[63,91],[63,92],[63,96],[51,96]]`; specifically budget four returns **[63,92]**. This is a count check, not a timing experiment.
