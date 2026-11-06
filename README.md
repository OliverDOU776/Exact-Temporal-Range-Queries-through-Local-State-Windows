<div align="center">

# Local State Windows

### Exact Temporal Range Queries<br>Without Full-Domain Enumeration

**Zijia Wang · Imperial College London**

Exact range extrema under one shared temporal variation budget.

[Quick start](#quick-start) · [How it works](#why-local-windows-work) · [Results](#measured-results-and-the-crossover) · [Query contract](docs/method.md) · [Figure sources](docs/figures.md)

</div>

<table>
<tr>
<td align="center" width="33%"><strong>At most 2V states</strong><br>per window, for V ≥ 1</td>
<td align="center" width="33%"><strong>At most 4r incidences</strong><br>across all sensitive runs</td>
<td align="center" width="33%"><strong>0.84–0.89× operator time</strong><br>small-budget participant summary</td>
</tr>
</table>

<p align="center">
<img src="docs/assets/local-state-windows.png" width="100%" alt="Exact mathematical example: four weighted interval runs, overlapping state windows, twelve sensitive run-window incidences, fixed-score recovery, and global count extrema zero and eight.">
</p>

**Small budgets make exact localization useful.** In two native C++ campaigns, budgets 1 and 4 took 0.84–0.89× the time of global-budget and gap-pruned controls under the primary participant summary. **The crossover matters:** budget 16 favored those controls under that summary; budget 64 and the maximum-64 bank favored them under both reported estimators. Complete source-to-report timings showed no consistent gain. [See the measured scope and full table.](docs/benchmarks.md)

## What this solves

For ordered observations, each row has an interval of offset states that make a predicate true. Choose an integer offset at every row, subject to one shared budget:

$$
\sum_{i=2}^{n}|x_i-x_{i-1}|\le v,\qquad x_i\in D.
$$

Local State Windows computes the **exact minimum and maximum weighted hit counts** at each requested budget. It keeps temporal dependence, respects open and closed range endpoints, and returns answers in request order. Applications include range-aggregate sensitivity analysis on time-series reports.

This repository provides a portable Python implementation, global and gap-pruned baselines, and a small literal-state oracle. The figures and benchmark summaries below describe the paper's recorded native C++ campaigns; they are not fresh timings of this release or Python speed measurements.

## Quick start

Python 3.10+; the Python package uses the standard library.

```bash
python -m pip install -e .
python -m lsw_range examples/synthetic.json
```

```python
from lsw_range import solve_intervals

# The four weighted runs in Figure 1: (lower, upper, weight).
answer = solve_intervals(
    [(2, 6, 2), (7, 13, 1), (4, 19, 3), (10, 17, 2)],
    domain=(0, 23),
    budgets=[4],
)
print(answer.bounds)  # ((0, 8),)
```

For measured observations, `solve_glucose` compiles a glucose band to exact hit-offset intervals before solving.

The native C++17 path accepts unit-count rows. This synthetic example expands Figure 1's integer weights into repeated unit rows:

```bash
mkdir -p build
c++ -std=c++17 -O3 native/lsw_range.cpp -o build/lsw-native
build/lsw-native < examples/synthetic_native.txt
```

The JSON CLI demo and native demo return bounds `[[0,6], [0,6], [0,8]]` for budgets `[0,1,4]`. [Implementation provenance](docs/provenance.md) describes the native input protocol and the Python translation.

Use `method="global"` or `method="gap"` to compare exact physical plans, and `method="reference"` as a small-case literal-state correctness oracle. The local plan is intended for small maximum budgets; this release does not provide a validated automatic plan selector.

## Why local windows work

A path with total variation at most $V$ spans at most $V$ offset units. Overlapping windows of at most $2V$ consecutive states therefore cover every feasible path. An interval has at most two boundary edges, so each sensitive run appears in at most four windows. A weighted sweep restores fixed contributions and accounts for inactive windows without enumerating the whole domain.

For $V\ge1$, the complete operator has arithmetic bounds

$$
\text{time }O\!\left(n+r\log(r+1)+rV^2+Q\right),\qquad
\text{auxiliary space }O(r+V^2).
$$

Here $n$ is the number of input rows, $r$ the sensitive-run count, $V$ the largest requested budget, and $Q$ the number of requests. Budget one has a boundary-prefix specialization that removes the budget recurrence. These are pseudopolynomial bounds in $V$; they assume free endpoints, consecutive integer states, positive retained weights, and unweighted absolute-distance transitions. [Read the full contract and limitations.](docs/method.md)

## Measured results and the crossover

<p align="center">
<img src="docs/assets/primary-results.png" width="100%" alt="Original primary benchmark figure: paired participant time ratios with bootstrap intervals, separate summed-time ratios, and absolute prepared-operator costs; small-budget gains cross over to losses at larger budgets.">
</p>

**126 participants · 6,804 planned report cells per campaign · two separately recorded campaigns.** Each primary cell used 96 rows, one of six primitive glucose bands, one of three temporal masks, and offset radius 15, 30, or 120.

| Requested budget | Local / SparseGlobal | Local / GapComponents | Interpretation |
|:--|--:|--:|:--|
| 1 | 0.838–0.846 | 0.867–0.882 | Both campaigns favor local windows |
| 4 | 0.856–0.861 | 0.880–0.889 | Both campaigns favor local windows |
| 16 | 1.069–1.086 | 1.040–1.058 | Participant summary favors controls |
| 64 | 1.291–1.293 | 1.276–1.283 | Both estimators favor controls |
| Bank: 0, 1, 4, 16, 64 | 1.305–1.319 | 1.269–1.275 | Largest budget governs localization |

Entries are **ranges across campaigns C/D of median participant geometric-mean paired time ratios**, not confidence intervals. Below one favors local windows. The original figure shows the 95% participant-bootstrap intervals and the separate ratio of summed per-case times, $T$. At budget 16, $T$ still favors local windows even though the primary participant summary does not. C has eight timeouts, retained as missing paired timings; complete comparisons have matching exact outputs.

The measured costs are small: at budget 1, LocalWindows totals **69.33 / 70.56 ms across 6,804 cells** in C/D. Complete reports include decoding, compilation and serialization and show **no consistent end-to-end improvement**. Historical timings are not a portability guarantee; a full fresh timing replication remains untested. [Full results, estimators and environment →](docs/benchmarks.md)

## A real query, with exact answers

<p align="center">
<img src="docs/assets/big001-exact-counts.png" width="100%" alt="Original BIG001 observations and exact count bounds under offsets from minus thirty to thirty; TITR bounds widen as the shared variation budget increases while TIR stays fixed.">
</p>

For the fixed public **BIG001** example, $n=96$, $D=\{-30,\ldots,30\}$, and the closed TITR band is $[70,140]$ mg/dL. At budget $v=4$, the exact minimum and maximum counts are **[63, 92] out of 96**. These are extrema over admissible offset paths, **not confidence limits**. At budget zero, every constant offset in the domain is allowed. Separate metrics may attain their extrema on different paths.

The offsets and budgets define an analyst-specified sensitivity scenario. They do not estimate calibrated sensor error or clinical effects. The plotted data are from BIG IDEAs Lab Glycemic Variability and Wearable Device Data, version 1.1.3; [attribution and figure details](docs/figures.md) accompany the artwork.

## Paper and attribution

**Zijia Wang. _Exact Temporal Range Queries through Local State Windows._ Imperial College London.**

The evaluation uses [BIG IDEAs Lab data v1.1.3](https://doi.org/10.13026/aw6y-fc44) and [Shanghai diabetes datasets v5](https://doi.org/10.6084/m9.figshare.21600933.v5). Report predicates and masks are grounded in [QoCGM's pinned author implementation](https://github.com/simcich/QoCGM/tree/b0bac0f5dbcc97bcdcf3ef85c2789594f3dfece3). Retain the third-party attribution and applicable licenses when reusing data or derived figures. See [figure provenance](docs/figures.md) and the [third-party notices](NOTICE).
