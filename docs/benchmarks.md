# Measured results and scope

[← README](../README.md) · [Primary data CSV](assets/primary-results.csv)

These are **historical measurements of the manuscript's native C++17 implementation**, copied from the final primary analysis. They do not measure the Python implementation or the cleaned release driver. No timing experiment was rerun to prepare this repository.

## What was measured

The primary workload includes 126 previously selected participants: 16 from BIG IDEAs, 12 Shanghai T1DM, and 98 Shanghai T2DM. Each of the 6,804 planned cells per mode has 96 observations, one of six primitive glucose predicates, a whole-record/night/day mask, and integer offset radius 15, 30, or 120. Each cell requests budget 1, 4, 16, 64 separately and the bank `(0, 1, 4, 16, 64)`.

C and D are separate recorded campaigns over the same identities. Across four methods and five modes, 272,160 primary method requests were saved. C has 136,072 completed responses and eight timeouts; D has 136,080 completed responses. Every available completed comparison agrees on exact output. Most paired comparisons include 6,804 complete pairs; affected C comparisons include 6,803. Timeouts remain missing without imputed runtimes.

The prepared-operator clock starts before the input scan and fresh plan preparation, and ends with ordered answer vectors. It excludes source decoding, predicate compilation, native serialization and correctness checks. No representation is reused between measured calls or shared across report cells. Each request has one warmup and three measured repetitions; its time is the mean of those repetitions.

The historical environment used g++ 13.3.0 with `-std=c++17 -O3 -DNDEBUG -Wall -Wextra -pedantic`, CPU affinity 0 on an Intel Xeon Platinum 8573C under Linux, and a one-second native-request wall limit. Source orchestration used Python 3.12.14, openpyxl 3.1.5 and xlrd 2.0.1. The host was not exclusive.

## Two estimators, different workload weights

The **primary participant summary** first takes the geometric mean of paired LocalWindows/baseline time ratios within each participant, then takes the median across participants. Its 95% intervals use 2,000 participant bootstrap resamples, preserving correlated cells within each person, with seed 2026107405.

The separate **summed-time ratio**, $T$, divides summed paired per-case mean times. It weights cases differently. The participant intervals do not apply to $T$. Intervals describe this selected case mix; they do not establish unseen-person or clinical generalization.

All ratios below one favor LocalWindows. Campaign ranges in the README are the minimum and maximum of C/D point estimates, **not confidence intervals**.

## Primary comparisons

The machine-readable CSV retains the exact source decimals, source campaign fields, denominators and mismatch counts. Its display field identifies the paper's C/D campaign labels. `GlobalBudgetBank` is named **SparseGlobal** in the paper, and `RunTailFullGThenGather` is named **RunTailFullG**.

| Campaign | Budget | Baseline | Participant median [95% interval] | Summed-time ratio $T$ | Complete pairs |
|:--|:--|:--|--:|--:|--:|
| C | 1 | SparseGlobal | 0.838 [0.828, 0.856] | 0.565 | 6,804 |
| C | 1 | GapComponents | 0.867 [0.854, 0.883] | 0.679 | 6,803 |
| C | 1 | RunTailFullG | 0.499 [0.452, 0.523] | 0.054 | 6,804 |
| C | 4 | SparseGlobal | 0.861 [0.846, 0.884] | 0.471 | 6,804 |
| C | 4 | GapComponents | 0.889 [0.875, 0.898] | 0.543 | 6,804 |
| C | 4 | RunTailFullG | 0.620 [0.592, 0.648] | 0.092 | 6,804 |
| C | 16 | SparseGlobal | 1.069 [1.048, 1.094] | 0.880 | 6,804 |
| C | 16 | GapComponents | 1.058 [1.041, 1.074] | 0.981 | 6,803 |
| C | 16 | RunTailFullG | 0.898 [0.876, 0.929] | 0.309 | 6,803 |
| C | 64 | SparseGlobal | 1.291 [1.265, 1.327] | 2.194 | 6,804 |
| C | 64 | GapComponents | 1.276 [1.251, 1.307] | 2.169 | 6,803 |
| C | 64 | RunTailFullG | 1.411 [1.361, 1.445] | 1.387 | 6,803 |
| C | bank | SparseGlobal | 1.305 [1.269, 1.328] | 2.095 | 6,803 |
| C | bank | GapComponents | 1.275 [1.241, 1.308] | 2.102 | 6,803 |
| C | bank | RunTailFullG | 1.381 [1.331, 1.428] | 1.298 | 6,803 |
| D | 1 | SparseGlobal | 0.846 [0.818, 0.858] | 0.562 | 6,804 |
| D | 1 | GapComponents | 0.882 [0.862, 0.891] | 0.686 | 6,804 |
| D | 1 | RunTailFullG | 0.488 [0.451, 0.521] | 0.062 | 6,804 |
| D | 4 | SparseGlobal | 0.856 [0.850, 0.877] | 0.456 | 6,804 |
| D | 4 | GapComponents | 0.880 [0.864, 0.904] | 0.557 | 6,804 |
| D | 4 | RunTailFullG | 0.614 [0.576, 0.635] | 0.104 | 6,804 |
| D | 16 | SparseGlobal | 1.086 [1.060, 1.109] | 0.830 | 6,804 |
| D | 16 | GapComponents | 1.040 [1.022, 1.059] | 0.883 | 6,804 |
| D | 16 | RunTailFullG | 0.890 [0.867, 0.911] | 0.298 | 6,804 |
| D | 64 | SparseGlobal | 1.293 [1.257, 1.328] | 2.256 | 6,804 |
| D | 64 | GapComponents | 1.283 [1.256, 1.313] | 2.203 | 6,804 |
| D | 64 | RunTailFullG | 1.416 [1.375, 1.450] | 1.574 | 6,804 |
| D | bank | SparseGlobal | 1.319 [1.288, 1.352] | 2.185 | 6,804 |
| D | bank | GapComponents | 1.269 [1.251, 1.301] | 2.118 | 6,804 |
| D | bank | RunTailFullG | 1.424 [1.371, 1.478] | 1.604 | 6,804 |

At budgets **1 and 4**, the primary summary favors LocalWindows over both SparseGlobal and GapComponents, with all corresponding intervals below one. GapComponents already prunes disconnected state components and contracts locally fixed rows.

At budget **16**, participant ratios exceed one against both budget-DP controls (1.040–1.086), while $T$ remains below one (0.830–0.981). At **64 and the maximum-64 bank**, both estimators favor those controls: participant ratios 1.269–1.319 and $T$ 2.095–2.256. The largest budget determines the shared bank's local cover and recurrence layers.

RunTailFullG computes a stronger full-curve output before gathering requested answers. Its low-budget ratios are lower, but the stronger output cost makes it a different comparison from the two budget-DP controls emphasized in the headline.

The gains occur at microsecond-scale operator costs. At budget 1, LocalWindows totals 69.33/70.56 ms across C/D's 6,804 cells, versus 122.71/125.61 ms for SparseGlobal. C's unpaired LocalWindows median and p95 are 1.81/42.01 μs; the separate SparseGlobal median is slightly lower at 1.76 μs. Marginal method medians and paired participant ratios summarize different quantities.

## Complete source-to-report cost

Complete-report campaigns A/B fix twelve participants, 96 rows, offset radius 30, all eighteen primitive cells, and four singleton budgets. Together they contain 384 complete reports. The clock charges hashing, decoding, row validation, mask and predicate compilation, native queries, percentage formatting, transport and JSON serialization. Correctness checks and durable evidence writing are excluded; native startup is separate. Processes may persist and operating-system caching may remain.

For budgets 1 and 4, every interval against SparseGlobal and GapComponents contains one. Against SparseGlobal, A/B summed-time ratios are **1.198 / 0.971 at budget 1** and **1.181 / 1.655 at budget 4**. Whole-report LocalWindows means range from **31.79 to 76.56 ms**. The complete source-to-report task establishes **no consistent end-to-end gain**.

These report intervals resample twelve paired participants for the total-cost ratio; they differ from the primary prepared-operator participant-median intervals.

## Interpretation limits

The final paper also reports longer-input and 241-state public diagnostic workloads separately. They are not pooled with the primary campaigns or the complete-report tier. The targeted diagnostic retains summed-time savings without the budget-one specialization, but its selected windows change across lengths and do not establish a controlled scaling law.

The results support a conditional physical plan for small budgets. A validated charged automatic selector, full fresh timing replication, second-host portability, held-out generalization, measured process RSS, and clinical calibration are not established. Correctness proofs and finite reference checks complement each other; neither a saved timing table nor a few examples certify arbitrary software inputs.
