# Query contract and method

[← README](../README.md)

For ordered rows $i=1,\ldots,n$, choose offsets $x_i$ from a nonempty consecutive integer domain $D=\{a,\ldots,b\}$. Each row supplies an interval $I_i\subseteq D$ and fixed nonnegative weight $\omega_i$. The requested answers are

$$
\operatorname{lo}(v)=\min_{x:\operatorname{TV}(x)\le v}\sum_i\omega_i\mathbf{1}\{x_i\in I_i\},\qquad
\operatorname{hi}(v)=\max_{x:\operatorname{TV}(x)\le v}\sum_i\omega_i\mathbf{1}\{x_i\in I_i\},
$$

where $\operatorname{TV}(x)=\sum_{i=2}^{n}|x_i-x_{i-1}|$. Both temporal endpoints are free. Budgets are nonnegative integers, supplied in request order; duplicate requests are valid. Budget zero permits every constant offset in $D$.

For glucose observations $g_i$ and a range predicate $J$, the corrected value is **$g_i-x_i$** and $I_i=\{x\in D:g_i-x\in J\}$. Finite open/closed endpoints compile to integer bounds through exact floor/ceiling operations. Fractional observations do not need to be rounded to integers.

## Why the representation preserves extrema

Zero-reward rows can be deleted because absolute distance obeys the triangle inequality; their states can be restored without increasing variation. Rows whose predicate is constant contribute a fixed score. Consecutive equal sensitive predicates merge into a positive-weight run. These operations preserve minimum and maximum scores, but do **not** preserve every attainable intermediate score.

Let $r$ be the resulting sensitive-run count. For the largest requested budget $V\ge1$, partition the domain into blocks of $V$ integer states and use every pair of neighboring blocks as an overlapping window. Each window has at most $2V$ states. A feasible path spans at most $V$ units, so at least one window contains it.

An interval run has at most two boundary edges. Each edge belongs to at most two windows; therefore the entire cover has at most $4r$ sensitive run-window incidences. Only active windows need local temporal solves. A static weighted sweep restores each active window's constant contribution and represents inactive windows. Reducing all local lower and upper endpoints gives the exact global extrema.

This yields arithmetic time $O(n+r\log(r+1)+rV^2+Q)$ and auxiliary memory $O(r+V^2)$ for $Q$ ordered requests. At $V=1$, a boundary-prefix formula removes the recurrence. The complexity is pseudopolynomial in $V$ and counts arithmetic operations; arbitrary numeric encodings can affect bit complexity.

## Report semantics

| Item | Meaning |
|:--|:--|
| Temporal mask | A fixed row weight, usually zero or one; excluded rows do not split the shared budget |
| Time order | Timestamps select masks and sequence order; elapsed time does not weight transitions |
| Count extrema | The exact minimum and maximum, without asserting that all interior scores are attainable |
| Percentage denominator | A fixed selected-sample count, independent of the offset path; it is not interpolated elapsed time |
| Empty mask | Count pair `[0, 0]`; a percentage with zero denominator is unavailable |
| Multiple report cells | Separate marginal queries; extrema need not share one attaining path |
| Offset radius and budget | Analyst-specified sensitivity parameters, without fitted sensor-drift or clinical interpretation |

The source report bank contains six primitive bands and three masks: whole-record, night before 08:00, and day from 08:00. Its primitive glucose predicates are:

| Cell | Corrected glucose $z$ in mg/dL |
|:--|:--|
| TIR | $70\le z\le180$ |
| TITR | $70\le z\le140$ |
| TBR1 | $54\le z<70$ |
| TBR2 | $z<54$ |
| TAR1 | $180<z\le250$ |
| TAR2 | $z>250$ |

These endpoints and mask boundaries are grounded in the pinned [QoCGM implementation](https://github.com/simcich/QoCGM/tree/b0bac0f5dbcc97bcdcf3ef85c2789594f3dfece3). Other source metrics or preprocessing are outside this query contract. Summing separately optimized primitive cells can produce unattainable combined bounds.

## Where the guarantee stops

The proof assumes free endpoints, consecutive integer states, nonnegative original weights with positive retained runs, and unweighted absolute-distance transitions. Anchors, elapsed-time transition penalties, rate limits, or opposite-signed run weights require different reasoning. The operator returns extrema, not a full count spectrum or one path realizing every requested metric.

Large budgets, small critical support, and static saturation can favor global or gap-pruned plans. The release has no validated charged automatic selector. [The measured crossover](benchmarks.md) is part of the evidence, not an exception to it.
