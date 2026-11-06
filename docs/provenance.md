# Implementation provenance

The author of this project and its accompanying manuscript, **Exact Temporal Range Queries through Local State Windows**, is **Zijia Wang**. This repository makes the query operator runnable independently of the manuscript-production and experiment-campaign directories. It does not assign a new code license; see [NOTICE](../NOTICE).

## Original native algorithm

`native/lsw_range.cpp` retains the solver body of the supplied D011 source, from `using namespace std` through `solve`, byte for byte. Its surrounding includes and single-query command-line driver are new. The solver body includes the original weighted-run preprocessing, critical support, shared-budget metric closure, overlapping local windows, gap components, budget-one prefix specialization, unit-count tail baseline, and original full-count reference. Internal timing fields remain in the original body; the new driver does not report timing measurements or run repetitions.

| Supplied source | SHA-256 |
| --- | --- |
| `new_evidence/experiments/code/operators.cpp` in `ICDE_Glucose_D011_Reproducibility` | `edcae9138a53ceb1df800c48bb496269391527f0495b65dd2aeb30a21594b43a` |
| Its declared origin, `frozen/experiments/D005/code/operators.cpp` | `133b7b4c512e4359c802fbbf9683f0a0d8903a8cc5bf56efce7649a60fd3b3c7` |

The supplied source describes D005 as a reconstructed implementation recovered on 2026-10-22, rather than an independently retrieved upstream software release. This provenance is retained here without bundling recovery conversations or audit records. No separate third-party solver license was present in those sources.

The historical D011 driver restricted requests to its specific campaign shape (`n <= 1152`, `V <= 16`, `Q <= 3`). These are runner restrictions, not mathematical restrictions of the retained solver functions. The new driver removes that campaign shape and uses explicit integer-safety/input limits documented in [native.md](native.md); its default sample and correctness tests use no timing campaign. The earlier D005 solver supplied the larger-budget historical comparisons. This cleaned executable is usable code, not a claim of a new benchmark replication or a byte-identical historical executable.

## Portable Python adaptation

`src/lsw_range/core.py` follows that native algorithm and the final manuscript's positive-weight interval formulation. It supplies a normal Python API, exact endpoint compilation, JSON input, arbitrary-precision integer coordinates, and exact rational weights. Unlike the original external native interface, it accepts arbitrary nonnegative row weights: zero rows are deleted and every retained sensitive run has positive weight. Negative weights are rejected because the run-contraction proof requires positivity.

Differences that matter when comparing implementations:

- Python defaults to exact **local critical support**. The paper permits either local critical support or all local integers; the historical native local operator uses all local integers. Set `local_support=False` or CLI `--all-local-states` to choose that same local state set in Python.
- Both use physical state gaps, overlapping windows, fixed-score recovery, and a maximum-budget bank shared by all requested budgets. Both retain ordered duplicate requests.
- Python deduplicates budgets using a set and sorts only the distinct requests. Its budget handling has `O(Q log Q)` worst-case comparison-sort overhead, including fixed/empty cases with `r=0`, because it runs before the fast-path return. Hash operations have their usual expected-time interpretation. For nontrivial local queries, there are at most `V+1` distinct budgets and their sorting is absorbed by the local recurrence bound; the degenerate `r=0` wrapper does not implement the paper's special `O(n+Q)` gather-only shortcut.
- Python's independent `reference` plan keeps original rows, all domain states, and explicitly enumerates predecessor states. It does not reuse the optimized preparation, support, metric-closure, or window routines. It is a small-case oracle and has explicit resource guards.
- Python does not implement the native unit-count `RunTailFullGThenGather` plan: its count-indexed unit-row completion is a different contract from arbitrary rational weights. That original baseline remains available through the native executable.

For `r` sensitive runs and maximum budget `V >= 1`, the **paper's local physical operator** has `O(n + r log(r+1) + r V(V+1) + Q)` arithmetic time and `O(r + V(V+1))` auxiliary storage, excluding input/output. A run appears in at most four local lists, windows are solved sequentially, and local state count is at most `2V`. At `V=1`, the prefix specialization removes the budget recurrence. These are the paper's operator bounds, not a universal runtime claim for the Python wrapper. A conservative whole-wrapper bound adds the budget-sort overhead above: `O(n + r log(r+1) + r V(V+1) + Q log(Q+1))` time and `O(Q + r + V(V+1))` space, counting its copied requests and lookup tables. Python object overhead and integer/rational bit costs are additional to arithmetic-operation counts. Global DP instead uses `O(r m(V+1))` recurrence work and `O(m(V+1))` rolling storage on at most `m <= 4r+2` critical states.

The benchmark tables in this repository describe the paper's previously recorded **native C++** campaigns. They are not performance measurements of this Python adaptation or the cleaned native driver. No fresh timing campaign was run to prepare this repository.

## Examples and data

The bundled interval and glucose examples are explicitly synthetic. The optional [BIG001 verifier](../examples/verify_big001.py) requires a user-supplied official CSV and distributes no patient readings. Its target comes from the final manuscript's accepted fixed-case count projection: BIG001, 96 samples, offsets `[-30,30]`, closed TITR band `[70,140]`, budgets `[0,1,4,16,64]`. Expected extrema are `[(63,91),(63,91),(63,92),(63,96),(51,96)]`. The SHA-256 check pins the exact source CSV used for that projection. See [api.md](api.md) for the command and source attribution.
