# Results reported in the paper

[← README](../README.md) · [Paper (PDF)](assets/paper.pdf) · [Formulation and method](method.md)

Every number on this page is transcribed from Section IV of the paper. These are measurements of the paper's C++ implementations; they are not timings of this repository's Python package, its native single-solve driver or the browser tool, and no timing experiment is shipped with the repository.

## Setup

**Data.** 211 public continuous glucose monitoring series from two clinical cohorts: the PhysioNet BIG IDEAs Lab Glycemic Variability and Wearable Device Data cohort (**BIG**, 16 participants) and the Shanghai diabetes clinical CGM cohort (**SH**, 195 patient series). Longer contiguous records of $n\in\{96,288,576,1{,}152\}$ samples are used for horizon scaling.

**Primary workload.** Each series is evaluated on standardized $n=96$-sample windows for all six consensus predicates (TIR, TITR, TBR70, TBR54, TAR180, TAR250; see [Table I](method.md#clinical-predicates-table-i)) and three offset radii $R\in\{15,30,120\}$ mg/dL ($m\in\{31,61,241\}$ states). This gives **6,804 query cells per request mode** across five modes: single-budget queries $V\in\{1,4,16,64\}$ and the five-budget ordered bank $\mathcal{V}=\{0,1,4,16,64\}$.

**Compared exact operators.** All share the same Stage 1 run contraction and $O(r+m)$ static $V=0$ sweep.

| Operator | What it does | Native method name in this repository |
|:--|:--|:--|
| **LocalWindows** | Overlapping $2V$-state windows, boundary-run nomination, two-pass local sweeps, $V=1$ boundary-prefix fast path | `LocalWindows` |
| **SparseGlobal** | Run-compressed budget DP over the global active state support with the two-pass sweep, reusing DP tables across ordered budget banks | `GlobalBudgetBank` |
| **GapComponents** | Splits the offset domain into independent components only where a state gap exceeds $V$, then runs exact component-level DP | `GapComponents` |
| **RunTailFullG** | Full tail dynamic program over the global state grid before gathering the requested budget extrema | `RunTailFullGThenGather` |
| Generic (ablation) | LocalWindows with only the $V=1$ boundary-prefix branch disabled | `LocalWindowsGeneric` |

**Protocol.** All four operators are implemented in C++20, compiled with `g++ -O3`, and share parsing, interval compilation and 64-bit integer arithmetic. Every benchmark suite runs in two independent replications, **R1** and **R2**. Paired runtime comparisons report (i) the participant-level median of geometric-mean LocalWindows/baseline runtime ratios with 95% participant-level bootstrap confidence intervals (2,000 resamples) and paired Wilcoxon signed-rank $p$-values across the $N=211$ series, and (ii) the descriptive ratio of summed per-case mean execution times $T=\sum_c t_\text{local}(c)/\sum_c t_\text{base}(c)$. Ratios below one favor LocalWindows. The two estimators weight the workload differently: many predicates exit early during Stage 1, and $T$ weights the non-trivial queries by their actual execution time.

## Exactness

Across all 6,804 primary query cells, all five request modes, all longer-horizon runs ($n\le1{,}152$) and both replications, LocalWindows, SparseGlobal, GapComponents and RunTailFullG produce **zero output mismatches (0/68,040 primary cell comparisons)**: every minimum count, maximum count and percentage interval agrees bit for bit.

## Primary prepared-operator runtime (Table II)

Each cell gives the participant-level median geometric-mean LocalWindows/baseline ratio [95% participant-bootstrap CI]; $T$.

| Rep. | $V$ | LocalWindows total (ms) | vs SparseGlobal | vs GapComponents | vs RunTailFullG |
|:--|:--|--:|:--|:--|:--|
| R1 | 1 | 69.33 | 0.838 [0.828, 0.856]; 0.565 | 0.867 [0.854, 0.883]; 0.679 | 0.499 [0.452, 0.523]; 0.054 |
| R1 | 4 | 121.55 | 0.861 [0.846, 0.884]; 0.471 | 0.889 [0.875, 0.898]; 0.543 | 0.620 [0.592, 0.648]; 0.092 |
| R1 | 16 | 359.86 | 1.069 [1.048, 1.094]; 0.880 | 1.058 [1.041, 1.074]; 0.981 | 0.898 [0.876, 0.929]; 0.309 |
| R1 | 64 | 1820.83 | 1.291 [1.265, 1.327]; 2.194 | 1.276 [1.251, 1.307]; 2.169 | 1.411 [1.361, 1.445]; 1.387 |
| R1 | Bank | 1751.28 | 1.305 [1.269, 1.328]; 2.095 | 1.275 [1.241, 1.308]; 2.102 | 1.381 [1.331, 1.428]; 1.298 |
| R2 | 1 | 70.56 | 0.846 [0.818, 0.858]; 0.562 | 0.882 [0.862, 0.891]; 0.686 | 0.488 [0.451, 0.521]; 0.062 |
| R2 | 4 | 123.41 | 0.856 [0.850, 0.877]; 0.456 | 0.880 [0.864, 0.904]; 0.557 | 0.614 [0.576, 0.635]; 0.104 |
| R2 | 16 | 339.00 | 1.086 [1.060, 1.109]; 0.830 | 1.040 [1.022, 1.059]; 0.883 | 0.890 [0.867, 0.911]; 0.298 |
| R2 | 64 | 1827.10 | 1.293 [1.257, 1.328]; 2.256 | 1.283 [1.256, 1.313]; 2.203 | 1.416 [1.375, 1.450]; 1.574 |
| R2 | Bank | 1831.01 | 1.319 [1.288, 1.352]; 2.185 | 1.269 [1.251, 1.301]; 2.118 | 1.424 [1.371, 1.478]; 1.604 |

[Figure 3 of the paper](assets/paper-fig3.png) plots these ratios together with absolute prepared-operator latency medians and 95th percentiles. Three regimes emerge:

- **Unit drift ($V=1$).** LocalWindows outperforms every baseline in both replications, with 95% CIs strictly below 1.0 ($p\le5.7\times10^{-37}$). Summed-time ratios are $T=0.562$–$0.565$ (1.78× speedup) against SparseGlobal, $0.679$–$0.686$ (1.47×) against GapComponents and $0.054$–$0.062$ (16.1×–18.5×) against RunTailFullG.
- **Moderate drift ($V=4$).** Windows of $|W_j|\le9$ states win against all baselines ($p\le3.2\times10^{-36}$): participant medians 0.856–0.861 ($T=0.456$–$0.471$, 2.12×–2.19×) against SparseGlobal, 0.880–0.889 ($T=0.543$–$0.557$, 1.80×–1.84×) against GapComponents and 0.614–0.620 ($T=0.092$–$0.104$, 9.6×–10.9×) against RunTailFullG.
- **Transition ($V=16$) and dense ($V=64$, bank) budgets.** At $V=16$ the participant medians slightly favor SparseGlobal and GapComponents (1.040–1.086), while $T$ still favors LocalWindows ($0.830$–$0.880$ and $0.883$–$0.981$): the window width $2V+1=33$ covers most of $m=31$ or $m=61$ on short $R\in\{15,30\}$ queries, whereas on the heavy $R=120$ ($m=241$) queries that dominate $T$ it remains highly localized. At $V=64$ and on the max-64 bank, where $2V+1=129$ spans the domain, global DP is faster by 1.27×–1.32× in median ratio ($T\approx2.1\times$), as the crossover bound predicts.

## Structural mechanism (Table III)

Medians over the 3,798 non-static cells ($r\ge1$ after Stage 1; the other 3,006 cells have $r=0$ and exit in $O(1)$ after contraction). On these cells Stage 1 compresses $n=96$ observations to a median of $r=24$ runs (interquartile range 11–43, maximum 77).

| Budget | Active windows $\lvert\mathcal{A}\rvert$ | Incidences per run | DP work ratio $\rho$ | vs SparseGlobal | vs GapComponents |
|:--|--:|--:|--:|--:|--:|
| $V=1$ | 10 | 1.88 | 0.000 | 0.330 | 0.336 |
| $V=4$ | 4 | 2.75 | 0.340 | 0.583 | 0.601 |
| $V=16$ | 2 | 3.69 | 0.892 | 1.390 | 1.384 |
| $V=64$ | 1 | 2.00 | 1.000 | 1.281 | 1.278 |
| Bank | 1 | 2.00 | 1.000 | 1.288 | 1.281 |

- The incidences per run never exceed the Lemma 3 ceiling of 4.00 in any cell (0/3,798 violations).
- At $V=1$ the boundary-prefix fast path performs **zero DP state updates** (a median of 47 prefix boundary steps), for a median runtime ratio of **0.330 (3.03× speedup)** against SparseGlobal and 0.336 (2.98×) against GapComponents across the 211 series ($p<10^{-36}$, 100% participant win rate).
- At $V=4$ a median of four active windows reduces inner-loop DP updates to $\rho(4)=0.340$ (66.0% work reduction), for a median ratio of **0.583 (1.72× speedup)** against SparseGlobal and 0.601 (1.66×) against GapComponents.

## Sensitivity by radius and predicate (Table V)

Active queries ($n=96$, $r\ge1$): median runs, median DP work ratio $\rho(4)$, and median runtime ratio LocalWindows/SparseGlobal.

| Stratum | Median $r$ | $\rho(4)$ | $V=1$ | $V=4$ | $V=16$ |
|:--|--:|--:|--:|--:|--:|
| Radius $R=15$ ($m=31$) | 18 | 0.612 | 0.412 | 0.935 | 1.540 |
| Radius $R=30$ ($m=61$) | 24 | 0.340 | 0.330 | 0.583 | 1.390 |
| Radius $R=120$ ($m=241$) | 31 | 0.118 | 0.248 | 0.442 | 0.718 |
| Normoglycemic (TIR/TITR) | 52 | 0.334 | 0.308 | 0.546 | 1.342 |
| Hyperglycemic (TAR180/250) | 22 | 0.345 | 0.339 | 0.594 | 1.402 |
| Hypoglycemic (TBR70/54) | 9 | 0.351 | 0.362 | 0.628 | 1.418 |

Widening the offset grid amplifies the $V=4$ speedup over SparseGlobal from 1.07× ($R=15$) to 1.72× ($R=30$) and 2.26× ($R=120$). At $R=120$, even $V=16$ prunes 68.5% of global DP updates ($\rho(16)=0.315$) and runs 1.39× faster (0.718). Two-sided normoglycemic bands produce the most active runs, and the gains are consistent across the BIG and SH cohorts.

## Horizon scaling and ablations (Table IV, Part A)

Summed-time ratios, R1 / R2. Generic disables only the $V=1$ boundary-prefix fast path. Column labels give record length, days and number of cells.

| Ratio | $n=96$ (1 d, 72 cells) | $n=288$ (3 d, 72 cells) | $n=576$ (6 d, 66 cells) | $n=1{,}152$ (12 d, 30 cells) |
|:--|--:|--:|--:|--:|
| LocalWindows / Generic ($V=1$ prefix ablation) | 0.858 / 0.849 | 0.830 / 0.835 | 0.840 / 0.909 | 0.820 / 0.803 |
| Generic / SparseGlobal ($V=1$ window-only) | 0.362 / 0.374 | 0.208 / 0.209 | 0.155 / 0.144 | 0.123 / 0.119 |
| LocalWindows / SparseGlobal, $V=1$ | 0.310 / 0.317 | 0.172 / 0.175 | 0.130 / 0.131 | 0.101 / 0.096 |
| LocalWindows / GapComponents, $V=1$ | 0.580 / 0.571 | 0.235 / 0.237 | 0.139 / 0.135 | 0.106 / 0.102 |
| LocalWindows / SparseGlobal, $V=4$ | 0.332 / 0.340 | 0.203 / 0.224 | 0.181 / 0.180 | 0.163 / 0.177 |
| LocalWindows / GapComponents, $V=4$ | 0.376 / 0.400 | 0.208 / 0.219 | 0.177 / 0.180 | 0.168 / 0.179 |
| LocalWindows / SparseGlobal, $V=16$ | 0.827 / 0.804 | 0.626 / 0.622 | 0.586 / 0.583 | 0.546 / 0.574 |
| LocalWindows / GapComponents, $V=16$ | 0.826 / 0.824 | 0.610 / 0.617 | 0.571 / 0.575 | 0.528 / 0.547 |

- At $V=1$ the summed-time speedup over SparseGlobal grows from 3.19× ($n=96$) to 5.76× ($n=288$), 7.66× ($n=576$) and **10.15×** ($n=1{,}152$); against GapComponents it climbs from 1.74× to 9.62×.
- At $V=4$ it grows from 2.98× to 4.68×, 5.54× and 5.88×.
- At $V=16$ the ratio against SparseGlobal drops from 0.804–0.827 (1.23×) to 0.546–0.574 (1.79×), and the share of cells where LocalWindows is slower than SparseGlobal falls from 35.4% at $n=96$ to 18.8%, 17.4% and 10.0% (3/30 cells) at $n=1{,}152$.
- On the combined long-horizon participant suite ($n\in\{288,1{,}152\}$), LocalWindows reaches participant-median ratios of 0.548–0.569 at $V\in\{1,4\}$ and 0.880–0.896 at $V=16$ against SparseGlobal/GapComponents, and beats RunTailFullG in all five modes (0.119 at $V=1$, 0.174 at $V=4$, 0.356 at $V=16$, 0.906 at $V=64$, 0.820 on the bank).
- **Ablations.** Without the prefix fast path, window localization alone (Generic) gives 2.72× ($n=96$) to 8.26× ($n=1{,}152$) speedups over SparseGlobal; the fast path adds a further 18%–23% (LocalWindows/Generic = 0.803–0.909). Recomputing each budget of the bank from scratch (ColdBank) increases prepared-bank time by 1.43×.

## Uncached source-to-report pipeline (Table IV, Part B)

A cold process reads raw spreadsheet/CSV files from disk, parses timestamps and decimal strings, and evaluates an 18-cell report (6 predicates × 3 radii). Each comparison gives the R1 median ratio [95% bootstrap CI] followed by the R2 median ratio.

| Budget | LocalWindows (ms, R1 / R2) | vs SparseGlobal | vs GapComponents | vs RunTailFullG |
|:--|--:|:--|:--|:--|
| $V=1$ | 44.98 / 39.87 | 1.20 [0.78, 1.73]; 0.97 | 1.20 [0.74, 1.84]; 1.06 | 1.41 [1.02, 1.83]; 1.28 |
| $V=4$ | 38.24 / 76.56 | 1.18 [0.94, 1.65]; 1.66 | 1.01 [0.69, 1.55]; 1.00 | 0.97 [0.73, 1.49]; 2.38 |
| $V=16$ | 31.79 / 33.61 | 0.94 [0.75, 1.10]; 0.86 | 0.98 [0.89, 1.05]; 0.86 | 0.86 [0.67, 1.01]; 0.63 |
| $V=64$ | 32.91 / 42.19 | 0.69 [0.48, 1.00]; 1.26 | 0.96 [0.85, 1.07]; 0.21 | 0.82 [0.62, 1.04]; 1.35 |

Uncached file I/O and text parsing take 30–75 ms per report, while the prepared DP operator takes 0.05–2.5 ms, so the 95% intervals on end-to-end report time span 1.0 in most cells. Where numeric streams are resident in memory (interactive analytics engines, feature stores, in-memory time-series databases), LocalWindows accelerates query execution by 1.7×–10.2× in the small- and moderate-drift regimes; in cold one-shot file-parsing scripts, I/O dominates wall-clock time unless binary caching is used.

## Data attribution

BIG: Cho, Kim, Bent and Dunn, *BIG IDEAs Lab Glycemic Variability and Wearable Device Data*, PhysioNet, version 1.1.3, [doi:10.13026/aw6y-fc44](https://doi.org/10.13026/aw6y-fc44) (ODC-By; see the [license notice](assets/BIG_IDEAs_ODC-By.txt)), with the study by Bent et al., *npj Digital Medicine* 4, 89 (2021). SH: Zhao, Zhu, Wang and Rao, *Shanghai diabetes continuous glucose monitoring datasets*, Figshare, version 5, [doi:10.6084/m9.figshare.21600933.v5](https://doi.org/10.6084/m9.figshare.21600933.v5), with Zhao et al., *Chinese diabetes datasets for data-driven machine learning*, *Scientific Data* 10, 35 (2023). The paper's longer-horizon records also cite Vosseler et al., *Scientific Reports* 10, 20466 (2020). Original data remain subject to their own terms.
