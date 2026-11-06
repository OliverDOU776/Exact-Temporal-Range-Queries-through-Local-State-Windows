# Native C++17 solver

This path retains the paper's native unit-count solver algorithms. For arbitrary exact positive weights and direct glucose-band compilation, use the [Python API](api.md).

## Build and run

From the repository root with a C++17 compiler:

```bash
mkdir -p build
c++ -std=c++17 -O3 native/lsw_range.cpp -o build/lsw-native
build/lsw-native < examples/synthetic_native.txt
```

Expected result:

```json
{"method":"LocalWindows","budgets":[0,1,4],"bounds":[[0,6],[0,6],[0,8]]}
```

The sample expands the conceptual weighted example into eight repeated unit rows. This is valid for these extrema by the positive-run lemma. It is a synthetic interval query, not human glucose data.

## Input protocol

Supply whitespace-delimited requests on standard input. Each request has:

```text
METHOD N DOMAIN_LO DOMAIN_HI Q
budget_1 ... budget_Q
interval_1_lower interval_1_upper
...
interval_N_lower interval_N_upper
```

Every interval is inclusive; inverted intervals are empty. The executable clips intervals to the state domain. Every original row has weight one; no third weight column is accepted. `N=0` is valid. Both temporal endpoints are free, and adjacent rows share the one total-variation budget. One JSON line is returned per request, preserving budget order and duplicates. On malformed input, the executable prints a concise error to standard error and exits with status 2.

| Method | Meaning |
| --- | --- |
| `LocalWindows` | Overlapping local windows with budget-one prefix specialization |
| `LocalWindowsGeneric` | Same plan with the generic budget recurrence at one |
| `GlobalBudgetBank` | Shared-budget DP on global critical support |
| `GapComponents` | Split global critical support at physical gaps exceeding the maximum budget |
| `RunTailFullGThenGather` | Original unit-count tail/count-axis baseline |
| `ReferenceFullCount` | Uncontracted original-row, all-integer-state count-axis reference |

Input limits guard the original fixed-width integer implementation: `0 <= N <= 1,000,000`, `1 <= Q <= 1,000,000`, `-1,000,000 <= DOMAIN_LO <= DOMAIN_HI <= 1,000,000`, budgets in `[0,10000]`, and input interval endpoints in `[-1,000,000,000,1,000,000,000]`. These are validation limits, not promises that every request near those limits fits available memory. The full-count reference additionally permits at most 2,000,000 count/state cells. The algorithms remain pseudopolynomial in budget; use small budgets for the local plan.

For glucose records, the Python `compile_interval` function can supply these exact inclusive integer interval endpoints. Do not round the original glucose reading before compilation.

## Correctness checks

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

When a `c++` compiler is available, the test suite builds the native executable in a temporary directory and checks all six plans against independent original-path enumeration on small cases, including empty rows, shared budgets, free endpoints, physical state gaps, and duplicate requests. No benchmark driver, repetition logs, or prebuilt binaries are included. [Provenance](provenance.md) identifies the original solver body and release changes.
