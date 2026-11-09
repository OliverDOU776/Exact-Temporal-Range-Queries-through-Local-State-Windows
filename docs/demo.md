# Run an exact range count in your browser

[Open the live solver](https://oliverdou776.github.io/Exact-Temporal-Range-Queries-through-Local-State-Windows/demo/) · [Download the 96-reading BIG001 input](demos/big001-input.json) · [Query contract](method.md)

Paste two readings, `70, 141`, set the closed band to `[70, 140]`, set the offset domain to `[0, 1]`, and request budgets `0, 1`. Choose **Compute exact bounds**. The answer changes from **[1, 1]** to **[0, 2]**: the paths (0, 1) and (1, 0) can score two and zero respectively, and both cost one unit of movement. Change 141 to 140 and run again; the answers change to **[1, 2]** at both budgets.

The page accepts pasted readings, CSV with a value column and optional 0/1 weight column, and local files. For example:

```csv
value,weight
70,1
100,0
141,1
```

Rows stay in input order. A zero masks the middle reading without giving the last reading a fresh budget. Change the endpoints, domain or budgets and compute again. Use **Download query + results** to keep the inputs and exact answers together. Imported readings are processed locally in a browser worker; the computation does not send them to a server.

## Reading the output

For input value `g` and offset `x`, the predicate tests `g − x`. The offset path can start and end anywhere in the domain. The sum of the absolute changes between successive offsets cannot exceed the requested budget. At budget zero, the path can use **any constant offset** in the domain.

| Output | What it means |
|---|---|
| Exact bounds | Minimum and maximum selected hits over feasible paths. Each endpoint is attainable; the pair does not imply every count between them is possible. |
| Nominal count | Selected hits in the uncorrected observations, equivalent to offset zero. If the domain excludes zero this reference need not be feasible. |
| Denominator | Number of selected observations, i.e. the sum of weights. With no selected observations the counts are zero and percentages are undefined. |
| Independent bounds | Minimum and maximum if each row chooses its offset freely from the domain, without a shared movement constraint. These can be wider than the exact bounds for a given budget. |

The fixed BIG001 preset contains the 96 observations and elapsed seconds, not a table of answers. For the supplied band and domain the nominal count is 84/96. The shared-budget bounds at budgets 0, 1, 4, 16 and 64 are [63, 91], [63, 91], [63, 92], [63, 96] and [51, 96]. Elapsed time describes the observations; it does not weight transitions. This subset is from Peter Cho, Juseong Kim, Brinnae Bent and Jessilyn Dunn, [BIG IDEAs Lab Glycemic Variability and Wearable Device Data v1.1.3](https://doi.org/10.13026/aw6y-fc44), PhysioNet, made available under [ODC-By 1.0](assets/BIG_IDEAs_ODC-By.txt). The JSON contains the original file identity, selected lines and transformation.

## What executes

[solver.js](project/solver.js) ports the local plan from [the Python implementation](../src/lsw_range/core.py). It compiles each band to an inclusive integer hit interval, removes constant rewards, and merges repeated sensitive predicates into weighted runs. A sweep computes constant-offset bounds. For a nontrivial positive maximum budget, overlapping windows retain the runs sensitive to each window. The solver restores fixed scores from the sweep and uses the real distances between retained offsets in its dynamic program. At maximum budget one, a prefix calculation replaces that recurrence. The minimum and maximum across windows give the returned endpoints. The diagnostics count active windows, run-window incidences, retained states, DP cells and prefix steps. A static answer can require zero active windows and zero DP cells.

The browser handles unit weights and binary masks. Limits are 2,000 rows, 401 consecutive offset states, offset endpoints from −1,000,000 to 1,000,000, 16 requested budgets from 0 to 64, and 40 million DP cells. A query that exceeds a limit returns an error. See the [Python API](api.md) for rational weights and additional exact plans. The manuscript's benchmark timings apply to the recorded native operator; the browser demo does not replicate those measurements.

### JavaScript input and output

Load `project/solver.js` and call `LSWDemo.solve(query)`. From the repository root, Node can run the same calculation without dependencies:

```js
const { solve } = require("./docs/project/solver.js");
const query = require("./docs/demos/big001-input.json");
console.log(solve(query).bounds);
```

A minimal query is `{values: ["70", "141"], band: ["70", "140"], domain: [0, 1], budgets: [1, 0, 1]}`. The result contains `bounds` in request order (including duplicate budgets), `budgets`, `domain`, `nominalCount`, `denominator`, `independentBounds`, `diagnostics` and `method: "local"`. Optional `weights` must contain one integer 0 or 1 per row. The optional booleans `lowerClosed` and `upperClosed` default to true. At the solver API, `null` represents an unbounded band endpoint.

Decimal strings are compiled exactly, including signed scientific notation. The solver uses integer arithmetic for comparisons and floor/ceiling at open or closed band endpoints. A numeric JSON or JavaScript value has already passed through the host's number parser; the solver uses its printed decimal value. For more digits than JavaScript preserves, supply **quoted decimal strings**. Decimal encodings are limited to 128 characters and explicit exponents from −400 to 400.

To serve the page locally from the repository root, run `python -m http.server 8000 --directory docs`, then open [localhost:8000/#try-demo](http://localhost:8000/#try-demo). A local HTTP origin allows the browser to load the worker and included preset.
