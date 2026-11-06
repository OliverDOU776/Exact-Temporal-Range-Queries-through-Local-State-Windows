# Original figures and attribution

[← README](../README.md)

The README uses the manuscript's original rendered figures. Their editable native SVG sources are included alongside the PNG exports, and all three original figures remain unchanged. The project page adds a compact rendering of the same fixed BIG001 observations for its opening teaser, described below. No new experimental measurements were made. PNGs preserve the original typography when the reader does not have Calibri installed; the SVG files retain live text without bundling font files.

| Figure | Rendered artwork | Native source | Content |
|:--|:--|:--|:--|
| 1 | [PNG](assets/local-state-windows.png) | [SVG](assets/local-state-windows.svg) | Exact mathematical localization example |
| 2 | [PNG](assets/big001-exact-counts.png) | [SVG](assets/big001-exact-counts.svg) | Original BIG001 observations and exact count extrema |
| 3 | [PNG](assets/primary-results.png) | [SVG](assets/primary-results.svg) | Primary prepared-operator comparisons and absolute costs |

## Figure 1: exact localization

The four-run mathematical example uses $D=\{0,\ldots,23\}$ and $V=4$. Its hit intervals are `[2,6]`, `[7,13]`, `[4,19]`, and `[10,17]`, with weights 2, 1, 3, and 2. The witness `(6,7,7,10)` has variation four and score eight. The five overlapping windows have at most eight states, and twelve sensitive run-window incidences satisfy $12\le4r=16$.

For window `[8,15]`, static depth gives the fixed contribution three; restoring it changes the local pair `[1,3]` to `[4,6]`. Reduction over the static and local extrema gives the global pair `[0,8]`. This is a mathematical example, not measured glucose. Every local solve retains temporal order, free endpoints and one shared variation budget.

## Figure 2: fixed BIG001 example

The figure uses the original earliest qualifying 96-row window for BIG participant 001 and integer offsets from −30 through 30. The horizontal axis follows actual elapsed timestamps; connectors require adjacent gaps of 270–330 seconds. TIR and TITR are closed glucose bands. The selected samples illustrate exact hit-offset intervals; all 96 offsets share one budget.

| Budget | Exact TIR count pair | Exact TITR count pair |
|--:|:--|:--|
| 0 | [66, 96] | [63, 91] |
| 1 | [66, 96] | [63, 91] |
| 4 | [66, 96] | [63, 92] |
| 16 | [66, 96] | [63, 96] |
| 64 | [66, 96] | [51, 96] |

The bounds are copied from the fixed original count payload and agree with the primary campaigns' available case checks. Segments connect extrema at discrete budgets. They are not confidence intervals and do not assert attainability of every interior count. Different metrics may require different attaining paths. Historical timing of this source payload is not used as performance evidence.

The observations are from **Peter Cho, Juseong Kim, Brinnae Bent, and Jessilyn Dunn, _BIG IDEAs Lab Glycemic Variability and Wearable Device Data_, PhysioNet, version 1.1.3**, [doi:10.13026/aw6y-fc44](https://doi.org/10.13026/aw6y-fc44). The associated study is **Brinnae Bent et al., _Engineering Digital Biomarkers of Interstitial Glucose from Noninvasive Smartwatches_, npj Digital Medicine 4, 89 (2021)**, [doi:10.1038/s41746-021-00465-w](https://doi.org/10.1038/s41746-021-00465-w). Retain the supplied [ODC Attribution license notice](assets/BIG_IDEAs_ODC-By.txt).

### Project-page teaser

The [opening input plot](project/big001-teaser.svg) renders the same 96 original BIG001 readings against their original elapsed timestamps, spanning 28,499 seconds. It uses the pinned official `001/Dexcom_001.csv`, original file lines 14–109. The pale band marks the closed TITR interval `[70,140]` mg/dL. The plot shows observed glucose only; it does not display a fitted or corrected trajectory. Adjacent count bounds on the project page are the fixed exact pairs listed above. This derived SVG is editable and uses standard fonts. The dataset attribution and ODC-By notice above also apply to this rendering.

## Figure 3: native prepared-operator costs

Filled circles show median participant geometric-mean paired LocalWindows/comparator time ratios. Bars show 95% participant-bootstrap intervals from 2,000 resamples. Open diamonds show the separate ratio of summed per-case mean times, $T$, without applying the circles' intervals to that estimator. Axes use a common logarithmic ratio scale; below one favors LocalWindows. The lower panels show completed-response medians and descriptive 95th-percentile caps.

C/D are separate recorded campaigns. Comparisons require matching exact outputs; C's eight timeouts remain missing, without imputed runtimes. [The copied primary CSV](assets/primary-results.csv) supplies the table values. [Benchmark scope and caveats](benchmarks.md) accompany the figure.

The evaluation summaries also use **Qinpei Zhao, Jinhao Zhu, Congrong Wang, and Weixiong Rao, _diabetes_datasets.zip_, Figshare version 5**, [doi:10.6084/m9.figshare.21600933.v5](https://doi.org/10.6084/m9.figshare.21600933.v5), with the study **Qinpei Zhao et al., _Chinese diabetes datasets for data-driven machine learning_, Scientific Data 10 (2023)**. The README's individual-record plot is BIG001; it is not a Shanghai record. Original data and software remain subject to their own attribution and license terms.
