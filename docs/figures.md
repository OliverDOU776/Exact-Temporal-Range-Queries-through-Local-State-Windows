# Figures and attribution

[← README](../README.md)

The README and project page show one figure from the paper and two repository illustrations. The repository illustrations come with their editable SVG sources next to the PNG exports; PNGs preserve the original typography when the reader does not have Calibri installed, and the SVG files keep live text without bundling font files.

| Figure | Rendered artwork | Source | Content |
|:--|:--|:--|:--|
| Paper Figure 3 | [PNG](assets/paper-fig3.png) | [Paper PDF](assets/paper.pdf), page 9 | Primary prepared-operator runtime ratios and absolute latency |
| Mechanism example | [PNG](assets/local-state-windows.png) | [SVG](assets/local-state-windows.svg) | Exact mathematical localization example |
| BIG001 example | [PNG](assets/big001-exact-counts.png) | [SVG](assets/big001-exact-counts.svg) | BIG001 observations and exact count envelopes |

## Paper Figure 3: primary prepared-operator runtime

`assets/paper-fig3.png` is a raster rendering of Figure 3 of [the paper](assets/paper.pdf), cropped without its caption. Panels (a)–(c) show paired LocalWindows/baseline runtime ratios against SparseGlobal, GapComponents and RunTailFullG for budgets $V\in\{1,4,16,64\}$ and the ordered bank $\{0,1,4,16,64\}$ in replications R1 and R2, on a common logarithmic axis; values below 1 favor LocalWindows. Filled circles are participant-level median geometric-mean ratios with 95% bootstrap intervals (2,000 resamples); open diamonds are summed-time ratios $T$. Teal marks intervals wholly below 1 (or $T<1$) and rose marks intervals wholly above 1 (or $T>1$). Panels (d)–(e) show absolute prepared-operator latency (µs, logarithmic) with median markers and 95th-percentile caps. The plotted values are listed in [Table II](benchmarks.md#primary-prepared-operator-runtime-table-ii).

## Mechanism example

The four-run mathematical example uses $D=\{0,\ldots,23\}$ and $V=4$. Its hit intervals are `[2,6]`, `[7,13]`, `[4,19]`, and `[10,17]`, with weights 2, 1, 3, and 2. The witness `(6,7,7,10)` has variation four and score eight. Following this repository's solver, the domain is split into blocks of $V$ states, so the five overlapping windows have at most $2V=8$ states, and twelve active run–window incidences satisfy $12\le4r=16$ (Lemma 3 of the paper).

For window `[8,15]`, the static depth gives the covered-run baseline three; restoring it changes the local envelope `[1,3]` to `[4,6]`. Reduction over the static and local extrema gives the global envelope `[0,8]`, which `solve_intervals` returns for this input ([Quick start](../README.md#quick-start)). This is a mathematical example, not measured glucose. Every local solve keeps temporal order, free endpoints and one shared variation budget.

## BIG001 example

The figure uses the earliest qualifying 96-row window for BIG participant 001 (the same readings as [the browser preset](demos/big001-input.json)) and integer offsets from −30 through 30. The horizontal axis follows actual elapsed timestamps; connectors require adjacent gaps of 270–330 seconds. TIR and TITR are closed glucose bands. The figure is drawn in the repository's reading-minus-offset form, $g_i-x_i$; on this symmetric domain the envelopes are the same as for the paper's $g_i+\delta_i$. The selected samples illustrate exact hit-offset intervals; all 96 offsets share one budget.

| Budget | Exact TIR envelope | Exact TITR envelope |
|--:|:--|:--|
| 0 | [66, 96] | [63, 91] |
| 1 | [66, 96] | [63, 91] |
| 4 | [66, 96] | [63, 92] |
| 16 | [66, 96] | [63, 96] |
| 64 | [66, 96] | [51, 96] |

These envelopes are returned by this repository's local, global, gap and literal reference plans and by the browser solver for the same readings; `examples/verify_big001.py` checks the TITR column against the official source CSV. Segments connect extrema at discrete budgets. They are not confidence intervals and do not assert attainability of every interior count. Different metrics may require different attaining paths.

The observations are from **Peter Cho, Juseong Kim, Brinnae Bent, and Jessilyn Dunn, _BIG IDEAs Lab Glycemic Variability and Wearable Device Data_, PhysioNet, version 1.1.3**, [doi:10.13026/aw6y-fc44](https://doi.org/10.13026/aw6y-fc44). The associated study is **Brinnae Bent et al., _Engineering Digital Biomarkers of Interstitial Glucose from Noninvasive Smartwatches_, npj Digital Medicine 4, 89 (2021)**, [doi:10.1038/s41746-021-00465-w](https://doi.org/10.1038/s41746-021-00465-w). Retain the supplied [ODC Attribution license notice](assets/BIG_IDEAs_ODC-By.txt).

### Project-page opening film

The [opening film](project/opening-film.mp4) ([GIF](project/opening-film.gif), [poster](project/opening-film.png), [manifest](project/opening-film.json)) is a 20-second silent loop built by `tools/build_opening_film.py`. It has two layers:

- **Schematic artwork** (`tools/opening_film_art.html`): the skin cross-section, the sensor, the glucose molecules, the 96-well plate, headings and captions. These are illustrations drawn from a written brief by a generative model (Gemini 4 Argon); they are not microscopy, not a device rendering and not a plate assay. The plate is a visual index of the 96 readings in time order (A1 → H12).
- **Data layer** (generated by the script): the same 96 BIG001 readings as the BIG001 example, the closed TITR band `[70,140]` mg/dL, the offset-corrected trace `g_i − x_i`, the offset path and the counter. Every frame of this layer shows one admissible offset path in `[−30,30]` with total variation at most 4 and its true count: offset 0 (84), constant offsets down to −12 (91), a path that stays at −12 and then moves one unit per reading to −8 (92, the exact maximum), and constant offsets down to −30 (63, the exact minimum). The script recomputes the exact envelopes `[63,91]` at budget 0 and `[63,92]` at budget 4 by dynamic programming and stops if they differ.

The film shows a query scenario; offset radius and budget are user-specified parameters, and animation pacing is not execution time. The dataset attribution and ODC-By notice above also apply to this rendering. Rebuild with `python tools/build_opening_film.py` (Playwright with Chromium, and FFmpeg).

The earlier static [input plot](project/big001-teaser.svg) of the same readings remains in the repository; it shows observed glucose only.

### Shanghai data

The paper's evaluation also uses **Qinpei Zhao, Jinhao Zhu, Congrong Wang, and Weixiong Rao, _Shanghai diabetes continuous glucose monitoring datasets_, Figshare version 5**, [doi:10.6084/m9.figshare.21600933.v5](https://doi.org/10.6084/m9.figshare.21600933.v5), with the study **Qinpei Zhao et al., _Chinese diabetes datasets for data-driven machine learning_, Scientific Data 10 (2023)**. The BIG001 plots are a BIG IDEAs record, not a Shanghai record. Original data and software remain subject to their own attribution and license terms.
