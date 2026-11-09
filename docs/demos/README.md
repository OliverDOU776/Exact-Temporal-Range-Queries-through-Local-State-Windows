# Demonstrations

The [working browser demo](../demo.md) accepts your own sequence and computes exact answers. These supporting clips each have an H.264 video, a looping GIF with the same sequence, and a still PNG. They illustrate exact count or score bounds; they do not measure processing speed. All clips are silent and use text labels.

| Clip | Video | GIF | Still | Duration |
| --- | --- | --- | --- | ---: |
| Two readings and a shared movement budget | [MP4](shared-budget.mp4) | [GIF](shared-budget.gif) | [PNG](shared-budget.png) | 12 s |
| Five budgets on a fixed BIG001 window | [MP4](big001-budget.mp4) | [GIF](big001-budget.gif) | [PNG](big001-budget.png) | 12.5 s |
| Why local windows overlap | [MP4](local-window.mp4) | [GIF](local-window.gif) | [PNG](local-window.png) | 11 s |

## Two readings

For the invented readings `(70, 141)` mg/dL, subtract a separate offset of 0 or 1 from each value. Count corrected readings in the closed band `[70, 140]`. Total variation (TV) is the absolute difference between the two offsets. Both temporal endpoints are free.

| Offsets | Corrected readings | TV | Count |
| --- | --- | ---: | ---: |
| (0, 0) | (70, 141) | 0 | 1 |
| (0, 1) | (70, 140) | 1 | 2 |
| (1, 0) | (69, 141) | 1 | 0 |
| (1, 1) | (69, 140) | 0 | 1 |

The opening six seconds show the two constant paths: at budget 0 both produce a count of 1. At budget 1 all four paths are feasible. The clip then traces the two paths attaining the new minimum of 0 and maximum of 2. Markers are the discrete offset choices; connecting lines show row order.

## Public BIG001 window

The left panel plots the same 96 original EGV observations in every frame. Points use actual elapsed time, span 28,499 seconds and are joined in order without smoothing. No observations within this window were excluded. The shaded area is the closed `[70, 140]` mg/dL target band. No corrected trajectory is plotted. The right panel highlights a different total-variation budget every 2.5 seconds. Integer offsets range from −30 to +30 mg/dL. Each exact endpoint counts observations out of 96; an endpoint pair does not establish that every intermediate count is attainable.

| Budget | Minimum | Maximum |
| ---: | ---: | ---: |
| 0 | 63 | 91 |
| 1 | 63 | 91 |
| 4 | 63 | 92 |
| 16 | 63 | 96 |
| 64 | 51 | 96 |

**Source and attribution.** The BIG001 animation, poster and GIF are derived from Peter Cho, Juseong Kim, Brinnae Bent, and Jessilyn Dunn, *BIG IDEAs Lab Glycemic Variability and Wearable Device Data*, version 1.1.3, PhysioNet, [DOI: 10.13026/aw6y-fc44](https://doi.org/10.13026/aw6y-fc44), made available under the [Open Data Commons Attribution License (ODC-By)](../assets/BIG_IDEAs_ODC-By.txt). The source is `001/Dexcom_001.csv`, original CSV lines **14–109** inclusive (line 1 is the header), SHA-256 `6333b21185f23834ab929e5d8bf9045bbed6268cdfd5030adab3c7d5ef689ef5`. The generator reads that file locally. The repository ships the derived media and the attributed 96-reading extract in `big001-input.json`, while the full original patient CSV is not bundled. See the separate [fixed-case verification script](../../examples/verify_big001.py).

## Overlapping local windows

The [synthetic weighted query](../../examples/synthetic.json) has offset domain `0..23`, budget 4, and four intervals `(lower, upper, weight)`: `(2,6,2)`, `(7,13,1)`, `(4,19,3)`, `(10,17,2)`. Six disjoint blocks each contain four states. The witness path `(6,7,7,10)` spans two blocks, `[4,7]` and `[8,11]`, so neither block contains it alone. Their union `[4,11]` contains the entire path. The three movements are `1 + 0 + 3 = 4`. Each row earns its full weight, giving the exact maximum `2 + 1 + 3 + 2 = 8`. More generally, a path with total movement at most 4 spans at most four offset units; merging each pair of neighboring blocks covers such paths. See [query contract and method](../method.md).

## Regenerate

Run from the repository root. Rendering uses Python 3.10+, Pillow (10 or newer), the DejaVu Sans / DejaVu Sans Mono fonts, and FFmpeg with the `libx264` encoder. The generator imports the solver from this checkout; no installed solver package, web request or GPU is required.

```bash
python -m pip install 'Pillow>=10'
python tools/build_project_demos.py --source-csv /path/to/001/Dexcom_001.csv
```

Without `--source-csv`, the default command builds the two synthetic clips and leaves the public example untouched. `--demo shared-budget`, `--demo big001-budget` and `--demo local-window` select one clip. `--out-dir DIRECTORY` sends the outputs elsewhere; the default is `docs/demos/`.

Before building the public clip, the generator checks the source hash, window identity and cadence, and recomputes the expected counts with the local, global and gap plans. It independently enumerates the four paths for the two-reading example and checks the method witness against the solver. All outputs use a 1200 × 672 canvas. MP4s use 12 frames per second, H.264 with 4:2:0 color and fast-start metadata; GIFs combine identical frames into timed holds.
