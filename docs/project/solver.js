/* Browser port of src/lsw_range/core.py: ordered unit-count or masked rows,
 * exact decimal predicates, free endpoints, one shared integer movement budget.
 * This file is also usable directly in a worker or via CommonJS. */
(function (root) {
  "use strict";

  const LIMITS = Object.freeze({ rows: 2000, domainStates: 401, offsetMagnitude: 1000000,
    queries: 16, budget: 64, dpCells: 40000000, decimalChars: 128, decimalExponent: 400 });
  const powers = new Map([[0, 1n]]);
  function power10(e) {
    if (!powers.has(e)) powers.set(e, 10n ** BigInt(e));
    return powers.get(e);
  }
  function decimal(value, label) {
    if (typeof value === "number") {
      if (!Number.isFinite(value)) throw Error(label + " must be finite.");
      if (Number.isInteger(value) && !Number.isSafeInteger(value))
        throw Error(label + " is outside the safe integer range; pass it as a decimal string.");
      value = String(value);
    }
    if (typeof value !== "string" || value.length > LIMITS.decimalChars)
      throw Error(label + " must be a decimal number of at most 128 characters.");
    const m = /^([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?$/.exec(value.trim());
    if (!m) throw Error(label + " must be a finite decimal number.");
    const exponent = m[5] === undefined ? 0 : Number(m[5]);
    if (!Number.isInteger(exponent) || Math.abs(exponent) > LIMITS.decimalExponent)
      throw Error(label + " decimal exponent must be between −400 and 400.");
    const fraction = m[3] || m[4] || "";
    let n = BigInt((m[2] || "0") + fraction);
    if (m[1] === "-") n = -n;
    const precision = fraction.length - exponent;
    return precision >= 0 ? { n, precision } : { n: n * power10(-precision), precision: 0 };
  }
  function integer(x, name, min, max) {
    if (!Number.isSafeInteger(x) || x < min || x > max)
      throw Error(name + " must be an integer between " + min + " and " + max + ".");
    return x;
  }
  function pair(x, name) {
    if (!Array.isArray(x) || x.length !== 2) throw Error(name + " must have two endpoints.");
    return x;
  }
  function closed(x, label) {
    if (x === undefined) return true;
    if (typeof x !== "boolean") throw Error(label + " must be true or false.");
    return x;
  }
  function floorDiv(n, q) {
    const d = n / q;
    return n < 0n && n % q !== 0n ? d - 1n : d;
  }
  function ceilDiv(n, q) { return -floorDiv(-n, q); }
  const hit = (row, state) => row.lo <= state && state <= row.hi;

  function prepare(input) {
    if (!input || typeof input !== "object" || Array.isArray(input)) throw Error("Expected an input object.");
    const { values, weights, band, domain, budgets } = input;
    if (!Array.isArray(values) || values.length > LIMITS.rows) throw Error("Supply at most 2,000 observations in values.");
    if (weights !== undefined && (!Array.isArray(weights) || weights.length !== values.length))
      throw Error("Supply one weight (0 or 1) per observation.");
    pair(domain, "Offset domain"); pair(band, "Band");
    const a = integer(domain[0], "Lower offset", -LIMITS.offsetMagnitude, LIMITS.offsetMagnitude);
    const b = integer(domain[1], "Upper offset", -LIMITS.offsetMagnitude, LIMITS.offsetMagnitude);
    if (a > b || b - a + 1 > LIMITS.domainStates) throw Error("Use a nonempty domain of at most 401 consecutive integer offsets.");
    if (!Array.isArray(budgets) || !budgets.length || budgets.length > LIMITS.queries)
      throw Error("Supply between 1 and 16 budgets.");
    const requests = Array.from(budgets, v => integer(v, "Budget", 0, LIMITS.budget));
    const lowerClosed = closed(input.lowerClosed, "lowerClosed");
    const upperClosed = closed(input.upperClosed, "upperClosed");
    const lower = band[0] === null ? null : decimal(band[0], "Band lower endpoint");
    const upper = band[1] === null ? null : decimal(band[1], "Band upper endpoint");
    const data = Array.from(values, (v, i) => decimal(v, "Observation " + (i + 1)));
    let precision = Math.max(lower ? lower.precision : 0, upper ? upper.precision : 0);
    for (const d of data) precision = Math.max(precision, d.precision);
    const scaled = (d) => d.n * power10(precision - d.precision);
    const left = lower && scaled(lower), right = upper && scaled(upper), unit = power10(precision);
    if (left !== null && right !== null && left > right) throw Error("Band lower endpoint must not exceed its upper endpoint.");
    const A = BigInt(a), B = BigInt(b);
    const p = { a, b, requests, runs: [], fixed: 0, total: 0, nominal: 0, denominator: 0, activeRows: 0 };
    for (let i = 0; i < data.length; ++i) {
      const w = weights === undefined ? 1 : integer(weights[i], "Weight " + (i + 1), 0, 1);
      if (w === 0) continue;
      ++p.denominator;
      const g = scaled(data[i]);
      if ((left === null || (lowerClosed ? g >= left : g > left)) &&
          (right === null || (upperClosed ? g <= right : g < right))) ++p.nominal;
      // Integer offset x satisfies lower <= g-x <= upper; open ends use strict rounding.
      const xLo = right === null ? A : upperClosed ? ceilDiv(g - right, unit) : floorDiv(g - right, unit) + 1n;
      const xHi = left === null ? B : lowerClosed ? floorDiv(g - left, unit) : ceilDiv(g - left, unit) - 1n;
      if (xHi < A || xLo > B || xLo > xHi) continue;
      // All conversion to Number happens after clipping to the bounded integer domain.
      const lo = Number(xLo < A ? A : xLo), hi = Number(xHi > B ? B : xHi);
      if (lo === a && hi === b) { ++p.fixed; continue; }
      ++p.activeRows; ++p.total;
      const last = p.runs[p.runs.length - 1];
      if (last && last.lo === lo && last.hi === hi) ++last.w;
      else p.runs.push({ lo, hi, w: 1 });
    }
    const changes = new Map([[a, 0]]);
    const change = (x, delta) => changes.set(x, (changes.get(x) || 0) + delta);
    for (const row of p.runs) {
      change(row.lo, row.w);
      if (row.hi < b) change(row.hi + 1, -row.w);
    }
    p.events = Array.from(changes).sort((x, y) => x[0] - y[0]);
    let score = p.fixed, lo = Infinity, hi = -Infinity;
    for (const [, delta] of p.events) {
      score += delta;
      lo = Math.min(lo, score); hi = Math.max(hi, score);
    }
    p.static = [lo, hi];
    return p;
  }

  function support(rows, a, b) {
    const states = new Set([a, b]);
    for (const row of rows) {
      const lo = Math.max(a, row.lo), hi = Math.min(b, row.hi);
      if (lo > hi) continue;
      for (const x of [lo - 1, lo, hi, hi + 1]) if (a <= x && x <= b) states.add(x);
    }
    return Array.from(states).sort((x, y) => x - y);
  }

  function kernel(rows, states, fixed, queries, diag) {
    const n = states.length;
    const maximum = Math.min(queries[queries.length - 1], (rows.length - 1) * (states[n - 1] - states[0]));
    const width = maximum + 1, cells = n * width * rows.length;
    if (diag.dpCells + cells > LIMITS.dpCells)
      throw Error("This query exceeds the 40 million DP-cell browser limit. Use fewer rows, a narrower domain, or a smaller maximum budget.");
    diag.dpCells += cells;
    diag.maxLocalStates = Math.max(diag.maxLocalStates, n);
    // One in-place pair of layers. Movement costs are physical gaps, not compressed indices.
    const low = new Int32Array(n * width), high = new Int32Array(n * width);
    for (const row of rows) {
      for (let j = 1; j < n; ++j) {
        const gap = states[j] - states[j - 1], off = j * width;
        for (let k = off + gap; k < off + width; ++k) {
          const prev = k - width - gap;
          low[k] = Math.min(low[k], low[prev]); high[k] = Math.max(high[k], high[prev]);
        }
      }
      for (let j = n - 2; j >= 0; --j) {
        const gap = states[j + 1] - states[j], off = j * width;
        for (let k = off + gap; k < off + width; ++k) {
          const prev = k + width - gap;
          low[k] = Math.min(low[k], low[prev]); high[k] = Math.max(high[k], high[prev]);
        }
      }
      for (let j = 0; j < n; ++j) if (hit(row, states[j])) {
        const off = j * width;
        for (let k = off; k < off + width; ++k) { low[k] += row.w; high[k] += row.w; }
      }
    }
    return queries.map(v => {
      let lo = Infinity, hi = -Infinity;
      for (let k = Math.min(v, maximum); k < n * width; k += width) {
        lo = Math.min(lo, low[k]); hi = Math.max(hi, high[k]);
      }
      return [fixed + lo, fixed + hi];
    });
  }

  function localBank(p, queries, diag) {
    const V = queries[queries.length - 1], blocks = Math.ceil((p.b - p.a + 1) / V);
    const windows = new Map(), answers = queries.map(() => p.static.slice());
    for (const row of p.runs) {
      const ids = new Set();
      if (blocks === 1) ids.add(0);
      else for (const edge of [row.lo, row.hi + 1]) {
        if (edge <= p.a || edge > p.b) continue;
        const block = Math.floor((edge - p.a) / V);
        for (const id of [block - 1, block]) if (id >= 0 && id < blocks - 1) {
          const start = p.a + id * V, end = Math.min(p.b, start + 2 * V - 1);
          if (start <= edge - 1 && edge <= end) ids.add(id);
        }
      }
      for (const id of ids) {
        if (!windows.has(id)) {
          const start = p.a + id * V;
          windows.set(id, { start, end: Math.min(p.b, start + 2 * V - 1), rows: [] });
        }
        windows.get(id).rows.push(row);
        ++diag.incidences;
      }
    }
    diag.localWindows = windows.size;
    let event = 0, base = p.fixed;
    for (const id of Array.from(windows.keys()).sort((x, y) => x - y)) {
      const { start, end, rows } = windows.get(id);
      while (event < p.events.length && p.events[event][0] <= start) base += p.events[event++][1];
      let local;
      if (V === 1 && end === start + 1) {
        let sum = 0, low = 0, high = 0;
        for (const row of rows) {
          sum += row.w * (Number(hit(row, end)) - Number(hit(row, start)));
          low = Math.min(low, sum); high = Math.max(high, sum);
        }
        diag.prefixSteps += rows.length; diag.maxLocalStates = Math.max(diag.maxLocalStates, 2);
        local = queries.map(v => v === 0 ? [base + Math.min(0, sum), base + Math.max(0, sum)]
          : [base + Math.min(low, sum - high), base + Math.max(high, sum - low)]);
      } else {
        let fixed = base;
        for (const row of rows) if (hit(row, start)) fixed -= row.w;
        local = kernel(rows, support(rows, start, end), fixed, queries, diag);
      }
      for (let i = 0; i < queries.length; ++i) {
        answers[i][0] = Math.min(answers[i][0], local[i][0]);
        answers[i][1] = Math.max(answers[i][1], local[i][1]);
      }
    }
    return answers;
  }

  function solve(input) {
    const p = prepare(input);
    const queries = Array.from(new Set(p.requests)).sort((x, y) => x - y);
    const diagnostics = { inputRows: input.values.length, activeRows: p.activeRows, runs: p.runs.length,
      localWindows: 0, incidences: 0, maxLocalStates: 0, dpCells: 0, prefixSteps: 0, commonFastPath: false };
    const independentBounds = [p.fixed, p.fixed + p.total];
    diagnostics.commonFastPath = queries[queries.length - 1] === 0 || !p.runs.length ||
      (p.static[0] === independentBounds[0] && p.static[1] === independentBounds[1]);
    const answers = diagnostics.commonFastPath ? queries.map(() => p.static) : localBank(p, queries, diagnostics);
    const bank = new Map(queries.map((v, i) => [v, answers[i]]));
    return { bounds: p.requests.map(v => bank.get(v).slice()), budgets: p.requests,
      nominalCount: p.nominal, denominator: p.denominator, independentBounds,
      diagnostics, method: "local", domain: [p.a, p.b] };
  }
  const api = Object.freeze({ solve, limits: LIMITS });
  root.LSWDemo = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(globalThis);
