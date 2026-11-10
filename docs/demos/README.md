# Using the LocalWindows browser tool

These screen recordings show the [browser application](https://oliverdou776.github.io/Exact-Temporal-Range-Queries-through-Local-State-Windows/demo/) in use. Each session enters or loads data, computes exact range counts and downloads the query with its results. The MP4, looping GIF and poster show the same application session. Recordings use actual browser captures. Idle pauses are trimmed and reading holds are added; the interface and computed results are not recreated. They are silent with on-screen captions and demonstrate workflows, not processing speed.

| Task | Video | GIF | Poster | Input |
| --- | --- | --- | --- | --- |
| Paste data, compute and export | [MP4](csv-session.mp4) | [GIF](csv-session.gif) | [PNG](csv-session.png) | [Two readings · CSV](two-readings.csv) |
| Check a public glucose report | [MP4](public-session.mp4) | [GIF](public-session.gif) | [PNG](public-session.png) | [BIG001 · JSON](big001-input.json) |
| Report selected readings | [MP4](masked-session.mp4) | [GIF](masked-session.gif) | [PNG](masked-session.png) | [Masked period · CSV](masked-period.csv) |

## Paste data, compute and export

1. Paste the two-reading CSV with readings `70,141`, both weighted 1.
2. Set the closed range to `[70,140]`, integer offsets to `0..1`, and shared movement budgets to `0,1`.
3. Compute the exact bounds: `[1,1]` at budget 0 and `[0,2]` at budget 1.
4. Edit the second reading from `141` to `140` and recompute. Both requested budgets now give `[1,2]`.
5. Download the JSON containing the revised query and computed results.

The example is synthetic. The edit demonstrates why an existing result must be recomputed when input data changes.

## Check a public glucose report

1. Load the public BIG001 example: 96 readings in their original order.
2. Compute the closed `[70,140]` range with integer offsets `−30..30` and budgets `0,1,4,16,64`.
3. Narrow the allowed integer offsets to `−10..10` and recompute the same budgets.
4. Compare the exact bounds and download the revised query and results.

| Budget | Bounds with offsets −30…30 | Bounds with offsets −10…10 |
| ---: | ---: | ---: |
| 0 | [63,91] | [84,87] |
| 1 | [63,91] | [83,87] |
| 4 | [63,92] | [82,89] |
| 16 | [63,96] | [80,92] |
| 64 | [51,96] | [80,92] |

These envelopes are computed live by the browser solver. The nominal count at offset 0 stays **84 out of 96**. Changing the allowed offset domain changes the sensitivity scenario, while the observations and nominal count remain fixed. Counts are exact extrema under the specified model, not confidence intervals; intermediate counts need not all be attainable. The offset domain and budgets are user-specified query parameters, not fitted sensor-error estimates.

**Source and attribution.** The public example and its derived recording use Peter Cho, Juseong Kim, Brinnae Bent, and Jessilyn Dunn, *BIG IDEAs Lab Glycemic Variability and Wearable Device Data*, version 1.1.3, PhysioNet, [DOI: 10.13026/aw6y-fc44](https://doi.org/10.13026/aw6y-fc44), under the [Open Data Commons Attribution License (ODC-By)](../assets/BIG_IDEAs_ODC-By.txt). The source is `001/Dexcom_001.csv`, original CSV lines **14–109** inclusive (line 1 is the header), SHA-256 `6333b21185f23834ab929e5d8bf9045bbed6268cdfd5030adab3c7d5ef689ef5`. The repository includes the attributed 96-reading extract in `big001-input.json`; the full original patient CSV is not bundled. See the [fixed-case verification script](../../examples/verify_big001.py).

## Report selected readings

1. Import `masked-period.csv` with ordered readings `70,100,141,100,70` and weights `1,0,1,0,1`.
2. Set the closed range to `[70,140]`, integer offsets to `0..1`, and budgets to `0,1,2`.
3. Compute the exact bounds and inspect the count denominator.
4. Download the JSON query and results.

| Budget | Exact count bounds |
| ---: | ---: |
| 0 | [1,2] |
| 1 | [1,2] |
| 2 | [0,3] |

Three rows contribute to the count; the nominal count is **2 out of 3**. Weight 0 excludes a row from the count without resetting the shared movement budget or changing input order. This synthetic example illustrates selecting observations within a period while preserving temporal coupling.

The [input format and browser contract](../demo.md) describe accepted files, exact decimal predicates and interactive limits. The application runs the solver locally in the browser, and the JSON download includes the submitted query and its exact count bounds.

## Recording and export

The public BIG001 session is 25.53 seconds; the CSV edit/export session is 29.53 seconds; the masked CSV session is 26.73 seconds. Each clip uses the actual local build of the published browser workspace. Input edits, computation, file import and JSON export were performed through the interface. Exported JSON was independently recomputed with the Python solver. These timings describe edited clip lengths, not query runtimes.

The only added image area is a caption strip below the browser viewport. Every UI frame is captured from the running application. Idle pauses between operations are removed and reading holds are added.

To encode your own captured sessions (Python, Pillow, FFmpeg and DejaVu Sans):

```bash
python tools/build_usage_recordings.py --capture-root /path/to/browser-captures --output-dir docs/demos
```

The input folder must contain the three session directories, each with its ordered browser PNGs and a `capture.json` listing `file`, `stage` and `timeMs` for every frame. The script encodes captures; it does not simulate the interface or substitute computed results. Raw recording frames and execution logs are not part of this repository.
