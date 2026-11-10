# Implementation provenance

The authors of this project and of the accompanying paper, **Exact Range-Count Envelopes Over Ordered Time Series Under Total-Variation Drift Budgets** ([PDF](assets/paper.pdf)), are **Zijia Wang and Christofer Toumazou**. This repository makes the LocalWindows operator runnable on its own. It does not assign a new code license; see [NOTICE](../NOTICE).

## Native algorithm

`native/lsw_range.cpp` retains the solver body of the authors' C++ research implementation, from `using namespace std` through `solve`, byte for byte. Its surrounding includes and single-query command-line driver are new. The solver body includes the weighted-run preprocessing, critical support, shared-budget metric closure, overlapping local windows, gap components, the budget-one prefix specialization, the unit-count tail baseline, and a full-count reference. The paper's operators map to the native method names as follows: LocalWindows → `LocalWindows`, Generic ablation → `LocalWindowsGeneric`, SparseGlobal → `GlobalBudgetBank`, GapComponents → `GapComponents`, RunTailFullG → `RunTailFullGThenGather`. Internal timing fields remain in the original body; the new driver does not report timing measurements or run repetitions.

| Source of the retained solver body | SHA-256 |
| --- | --- |
| Authors' C++ operator source file | `edcae9138a53ceb1df800c48bb496269391527f0495b65dd2aeb30a21594b43a` |

The new driver accepts general request shapes within explicit integer-safety and input limits documented in [native.md](native.md), and compiles as C++17. Its sample and correctness tests run no timing experiment. It is usable code, not a replication of the paper's measurements, which used C++20 implementations compiled with `g++ -O3`.

## Portable Python adaptation

`src/lsw_range/core.py` follows that native algorithm and the paper's positive-weight run formulation. It supplies a normal Python API, exact endpoint compilation, JSON input, arbitrary-precision integer coordinates, and exact rational weights. Unlike the native interface, it accepts arbitrary nonnegative row weights: zero rows are deleted and every retained sensitive run has positive weight. Negative weights are rejected because the run-contraction proof requires positivity. It tests the reading minus the offset, $g_i-x_i$; on the paper's symmetric domains this gives the same envelopes as the paper's $g_i+\delta_i$.

Differences that matter when comparing implementations:

- Python and the browser port partition the domain into blocks of $V$ states, so each overlapping window has at most $2V$ states. The paper's Lemma 2 states the cover with blocks of at most $V+1$ states; both are exact covers.
- Python defaults to exact **local critical support** inside each window. The native local operator uses all local integers. Set `local_support=False` or CLI `--all-local-states` to choose that same local state set in Python.
- Both use physical state gaps, overlapping windows, fixed-score recovery, and a maximum-budget bank shared by all requested budgets. Both retain ordered duplicate requests.
- Python deduplicates budgets using a set and sorts only the distinct requests. Its budget handling has `O(Q log Q)` worst-case comparison-sort overhead, including fixed/empty cases with `r=0`, because it runs before the fast-path return. Hash operations have their usual expected-time interpretation. For nontrivial local queries, there are at most `V+1` distinct budgets and their sorting is absorbed by the local recurrence bound; the degenerate `r=0` wrapper does not implement a special `O(n+Q)` gather-only shortcut.
- Python's independent `reference` plan keeps original rows, all domain states, and explicitly enumerates predecessor states. It does not reuse the optimized preparation, support, metric-closure, or window routines. It is a small-case oracle and has explicit resource guards.
- Python does not implement the native unit-count `RunTailFullGThenGather` plan: its count-indexed unit-row completion is a different contract from arbitrary rational weights. That baseline remains available through the native executable.

The paper's complexity statement (Theorem 2) is given in [method.md](method.md#exactness-and-complexity-theorem-2). For this repository's local plan, with `r` sensitive runs and maximum budget `V >= 1`, arithmetic time is `O(n + r log(r+1) + r V(V+1) + Q)` and auxiliary storage `O(r + V(V+1))`, excluding input/output: a run appears in at most four local lists, windows are solved sequentially, and local state count is at most `2V`. At `V=1`, the prefix specialization removes the budget recurrence. A conservative whole-wrapper bound adds the budget-sort overhead above: `O(n + r log(r+1) + r V(V+1) + Q log(Q+1))` time and `O(Q + r + V(V+1))` space, counting copied requests and lookup tables. Python object overhead and integer/rational bit costs are additional to arithmetic-operation counts. The global plan instead uses `O(r m(V+1))` recurrence work and `O(m(V+1))` rolling storage on at most `m <= 4r+2` critical states.

The [results](benchmarks.md) in this repository are the paper's measurements of its C++ implementations. They are not performance measurements of this Python adaptation or of the native single-solve driver.

## Examples and data

The interval and glucose examples under `examples/` are explicitly synthetic. The [browser demo](demo.md) additionally includes a [96-reading public BIG001 extract](demos/big001-input.json), with source identity, elapsed seconds and ODC-By attribution. It supplies observations, not precomputed answers: the browser's JavaScript port runs LocalWindows on these values. The full source CSV is not bundled. The optional [BIG001 verifier](../examples/verify_big001.py) requires that official CSV to independently check the fixed case: BIG001, 96 samples, offsets `[-30,30]`, closed TITR band `[70,140]`, budgets `[0,1,4,16,64]`. Expected extrema are `[(63,91),(63,91),(63,92),(63,96),(51,96)]`. The SHA-256 check pins the exact source CSV used for that projection. See [api.md](api.md) for the command and source attribution.
