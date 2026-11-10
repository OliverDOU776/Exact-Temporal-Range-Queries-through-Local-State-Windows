# Problem formulation and method

[← README](../README.md) · [Paper (PDF)](assets/paper.pdf)

This page summarizes the formulation and the LocalWindows operator as stated in the paper, then the contract of the code in this repository. Equation, lemma and theorem numbers refer to the paper.

## The query (Definition 1)

Let $g=(g_1,\ldots,g_n)$ be an ordered series and $P=[L,U]$ a range-count predicate, which may be two-sided, lower-unbounded $(-\infty,U]$ or upper-unbounded $[L,\infty)$. Each reading is perturbed by an integer offset $\delta_i$ from the discrete domain

$$
D=\{-R,-R+1,\ldots,R\},\qquad m=|D|=2R+1,
$$

where $R$ is the maximum per-sample calibration error radius (for example $R\in\{15,30,120\}$ mg/dL). Drift evolves gradually, so the offset trajectory is constrained by its discrete total variation:

$$
\operatorname{TV}(\delta)=\sum_{i=2}^{n}|\delta_i-\delta_{i-1}|,\qquad
\mathcal{F}(V)=\{\delta\in D^n:\operatorname{TV}(\delta)\le V\}.
$$

For a reading $g_i$, the offsets that make $g_i+\delta_i$ a hit form a contiguous interval

$$
I_i=\{\delta_i\in D:L\le g_i+\delta_i\le U\}=[\ell_i,u_i]\cap D,\qquad
\ell_i=\max(-R,\lceil L-g_i\rceil),\quad u_i=\min(R,\lfloor U-g_i\rfloor),
$$

with $I_i=\emptyset$ whenever $\ell_i>u_i$. The hit count of a trajectory is $C(\delta)=\sum_{i=1}^n\mathbf{1}\{\delta_i\in I_i\}$. For an ordered budget bank $\mathcal{V}=\{v_1<\cdots<v_K\}$, the query returns for every $v\in\mathcal{V}$

$$
\operatorname{lo}(v)=\min_{\delta\in\mathcal{F}(v)}C(\delta),\qquad
\operatorname{hi}(v)=\max_{\delta\in\mathcal{F}(v)}C(\delta),
$$

and the range-proportion interval $[100\operatorname{lo}(v)/n,\ 100\operatorname{hi}(v)/n]$.

At $V=0$ the trajectory is a constant calibration shift $\delta_1=\cdots=\delta_n=z\in D$. Because $\mathcal{F}(v)\subseteq\mathcal{F}(v')$ for $v\le v'$, the envelope widens monotonically: $\operatorname{lo}(v')\le\operatorname{lo}(v)\le C(\mathbf{0})\le\operatorname{hi}(v)\le\operatorname{hi}(v')$. Any budget $v\ge V_\text{sat}=2R(n-1)$ saturates at the independent per-sample bounds $\operatorname{lo}_\text{ind}=\sum_i\mathbf{1}\{I_i=D\}$ and $\operatorname{hi}_\text{ind}=\sum_i\mathbf{1}\{I_i\ne\emptyset\}$.

### Clinical predicates (Table I)

The paper's evaluation uses six consensus CGM predicates. For an integer reading $g_i$ (thresholds in mg/dL):

| Metric | Band | Meaning | Compiled interval $I_i\subseteq D$ |
|:--|:--|:--|:--|
| TIR | $[70,180]$ | In range | $[\max(-R,70-g_i),\ \min(R,180-g_i)]$ |
| TITR | $[70,140]$ | Tight in range | $[\max(-R,70-g_i),\ \min(R,140-g_i)]$ |
| TBR70 | $(-\infty,69]$ | Level 1 hypoglycemia | $[-R,\ \min(R,69-g_i)]$ |
| TBR54 | $(-\infty,53]$ | Level 2 hypoglycemia | $[-R,\ \min(R,53-g_i)]$ |
| TAR180 | $[181,\infty)$ | Level 1 hyperglycemia | $[\max(-R,181-g_i),\ R]$ |
| TAR250 | $[251,\infty)$ | Level 2 hyperglycemia | $[\max(-R,251-g_i),\ R]$ |

## LocalWindows

### Stage 1: extrema-preserving run reduction

**Lemma 1 (fixed-row contraction).** Let $c_1$ and $c_0$ count the always-hit ($I_i=D$) and always-miss ($I_i=\emptyset$) rows. If every row is fixed, $\operatorname{lo}(V)=\operatorname{hi}(V)=c_1$. Otherwise, for every $V\ge0$ the exact extrema equal $c_1$ plus the extrema over the subsequence of active rows ($\emptyset\subsetneq I_i\subsetneq D$) under the same budget.

**Theorem 1 (extrema-preserving duplicate-run merging).** Merge each maximal block of identical adjacent active intervals into one run $(I_t,w_t)$ of weight $w_t\ge1$. Then for every $V\ge0$

$$
\operatorname{lo}(V)=c_1+\min_{\eta\in D^r:\operatorname{TV}(\eta)\le V}\sum_{t=1}^r w_t\mathbf{1}\{\eta_t\in I_t\},\qquad
\operatorname{hi}(V)=c_1+\max_{\eta\in D^r:\operatorname{TV}(\eta)\le V}\sum_{t=1}^r w_t\mathbf{1}\{\eta_t\in I_t\}.
$$

These reductions preserve the minimum and maximum; they do not claim that every intermediate count is attainable.

**Static event sweep ($V=0$).** A difference array over $D$ (add $w_t$ at $\ell_t$, subtract it at $u_t+1$) and one prefix sum give the static depth $d(z)=c_1+\sum_t w_t\mathbf{1}\{z\in I_t\}$ for every $z\in D$ in $O(r+m)$ time, and with it the exact envelope $[\alpha,\beta]=[\min_z d(z),\max_z d(z)]$ at $V=0$. The depth array is kept as a lookup bank for Stage 2.

### Stage 2: overlapping $2V$-state windows

A trajectory with $\operatorname{TV}(\eta)\le V$ has range diameter $\max_t\eta_t-\min_t\eta_t\le V$ (Eq. 9).

**Lemma 2 (overlapping $2V$-window cover).** For $V\ge1$, partition $D$ into $B=\lceil m/(V+1)\rceil$ contiguous blocks of at most $V+1$ states and take each union of adjacent blocks, $W_j=B_j\cup B_{j+1}$, as an overlapping window. Every trajectory with $\operatorname{TV}(\eta)\le V$ lies entirely inside at least one window, so the global optimization decomposes exactly into independent local optimizations over the windows (Eq. 11).

**Three-way run classification.** Relative to a window $W_j=[a_j,b_j]$, a run is a *disjoint miss* ($I_t\cap W_j=\emptyset$, contributes 0), a *covered hit* ($W_j\subseteq I_t$, contributes the constant $w_t$), or an *active boundary run* ($\emptyset\subsetneq I_t\cap W_j\subsetneq W_j$).

**Lemma 3 (global boundary-incidence sparsity bound).** Let $R_j$ be the active boundary runs of $W_j$. Then $\sum_j|R_j|\le4r$, and all lists $R_j$ can be built in $O(r+J)$ time: each run nominates itself through its two boundary transitions $\ell_t$ and $u_t+1$, and each coordinate belongs to at most two windows.

**Static baseline restoration.** The constant score of always-hit rows and covered runs in $W_j$ is recovered from the static depth at the window's left anchor $s_j=a_j$:

$$
f_j=d(s_j)-\sum_{t\in R_j}w_t\mathbf{1}\{s_j\in I_t\}.
$$

Windows without active runs reduce to constant trajectories already covered by $[\alpha,\beta]$, so only the active set $\mathcal{A}=\{j:R_j\ne\emptyset\}$, with $|\mathcal{A}|\le\min(J,4r)$, is evaluated.

### Stage 3: linear-time local sweeps

**Two-pass $O(|W_j|)$ transition kernel ($V\ge2$).** Within an active window of width $m_j$ and $N_j=|R_j|$ active runs, a trajectory can usefully spend at most $B_j=\min(V_\text{max},\max(0,N_j-1)(m_j-1))$ units of variation. Leftward and rightward running envelopes (Eq. 16) replace the $O(m_j^2)$ transition scan with $O(m_j)$ work per budget level.

**Proposition 1 (local budget saturation and bank table reuse).** Any trajectory in $W_j$ exceeding variation $B_j$ can be replaced by one with variation at most $B_j$ and the same hit count, so a single sweep to depth $B_j$ yields the window extrema for every budget in the bank.

**Proposition 2 (boundary-prefix exactness at $V=1$).** A non-constant trajectory with $\operatorname{TV}=1$ makes one unit step after some run. Evaluating single steps only at the boundary-adjacent offsets $\partial I_t=\{\ell_t-1,\ell_t,u_t,u_t+1\}\cap D$, with prefix and suffix hit counts, gives the exact $V=1$ envelope in $O(r+m)$ time and $O(m)$ space, with no DP table.

**Global reduction.** For each $v\ge2$, $\operatorname{lo}(v)=\min(\alpha,\min_{j\in\mathcal{A}}[f_j+\operatorname{lo}_j(\min(v,B_j))])$ and $\operatorname{hi}(v)=\max(\beta,\max_{j\in\mathcal{A}}[f_j+\operatorname{hi}_j(\min(v,B_j))])$.

### Exactness and complexity (Theorem 2)

LocalWindows returns the exact envelopes $\{[\operatorname{lo}(v),\operatorname{hi}(v)]\}_{v\in\mathcal{V}}$. Furthermore:

1. Run compression and static $V=0$ evaluation take $O(n+m)$ time.
2. For $V=1$, the boundary-prefix fast path runs in $O(r+m)$ time and $O(m)$ space after compression.
3. For $V\ge2$, the local window DP performs at most $\sum_{j\in\mathcal{A}}|R_j|(B_j+1)|W_j|\le4r(V+1)(2V+1)$ inner-loop state updates, taking $O(rV^2+m)$ time and $O(V^2+m)$ working memory when $V\ll m$, and $O(rVm)$ worst-case time when $V=\Omega(m)$.

**Crossover.** Against global run-compressed DP ($r(V+1)m$ state updates), the work ratio is

$$
\rho(V)=\frac{\sum_{j\in\mathcal{A}}|R_j|(B_j+1)|W_j|}{r(V+1)m}\le\frac{4(2V+1)}{m}.
$$

When $V\ll m$ (for example $V=4$ on $m=61$), LocalWindows prunes most global DP updates. As $2V+1$ approaches $m$ (for example $V\ge16$ on $m=61$, or $V=64>m$), the windows span nearly all of $D$, $\rho(V)$ approaches 1, and window setup becomes overhead. A wider offset grid or a longer series moves the crossover in favor of LocalWindows. [Measured crossover](benchmarks.md)

## This repository's contract

The Python package, the native driver and the browser tool solve the same problem in a slightly more general form.

- **Sign convention.** The code tests the reading minus the offset, $g_i-x_i$, on any nonempty consecutive integer domain $D=\{a,\ldots,b\}$. With $x_i=-\delta_i$ this is the paper's model with the domain reflected; on a symmetric domain $\{-R,\ldots,R\}$ both forms give identical envelopes.
- **Weights.** For rows $i=1,\ldots,n$ with intervals $I_i\subseteq D$ and fixed nonnegative weights $\omega_i$, the code returns
  $\operatorname{lo}(v)=\min_{x:\operatorname{TV}(x)\le v}\sum_i\omega_i\mathbf{1}\{x_i\in I_i\}$ and the corresponding maximum. Zero-weight rows are deleted without resetting the shared budget; every retained run has positive weight. Negative weights are rejected because run contraction requires positivity.
- **Endpoints.** For glucose observations and a range predicate $J$, $I_i=\{x\in D:g_i-x\in J\}$. Finite open or closed endpoints compile to integer bounds through exact floor/ceiling operations; fractional observations are not rounded.
- **Budgets.** Nonnegative integers in request order; duplicates are allowed. Budget zero permits every constant offset in $D$. Both temporal endpoints are free.
- **Windows.** The Python and browser solvers partition the domain into blocks of $V$ states (where $V$ is the largest requested budget), so each overlapping window has at most $2V$ states; any $V+1$ consecutive states lie inside one window, so this is also an exact cover. By default each window is restricted to its critical offsets. At $V=1$, a boundary-prefix calculation replaces the recurrence.
- **Implementation cost.** For the repository's local plan, arithmetic time is $O(n+r\log(r+1)+rV^2+Q)$ and auxiliary memory $O(r+V^2)$ for $Q$ ordered requests (pseudopolynomial in $V$; see [provenance](provenance.md) for wrapper overheads).

## Report semantics

| Item | Meaning |
|:--|:--|
| Temporal mask | A fixed row weight, usually zero or one; excluded rows do not split the shared budget |
| Time order | Input order is temporal order; elapsed time does not weight transitions |
| Count extrema | The exact minimum and maximum, without asserting that all interior scores are attainable |
| Percentage denominator | A fixed selected-sample count, independent of the offset path; it is not interpolated elapsed time |
| Empty mask | Count pair `[0, 0]`; a percentage with zero denominator is unavailable |
| Multiple report cells | Separate marginal queries; extrema need not share one attaining path |
| Offset radius and budget | User-specified query parameters; the code does not fit them to sensor data |

Combining separately optimized cells, for example adding the TBR70 and TAR180 envelopes, can produce bounds that no single trajectory attains.

## Where the guarantee stops

The proofs assume free endpoints, consecutive integer states, nonnegative original weights with positive retained runs, and unweighted absolute-distance transitions. Anchored endpoints, elapsed-time transition penalties, rate limits or opposite-signed run weights require different reasoning. The operator returns extrema, not a full count spectrum or one path realizing every requested metric.

Budgets for which $2V+1$ approaches the offset-grid size favor global or gap-split plans, as the crossover above predicts. This release has no automatic plan selector.
