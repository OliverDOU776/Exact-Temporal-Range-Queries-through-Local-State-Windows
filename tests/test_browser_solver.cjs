// Run from a checkout with Node: node tests/test_browser_solver.cjs
"use strict";
const assert = require("node:assert/strict");
const { solve } = require("../docs/project/solver.js");
const big = require("../docs/demos/big001-input.json");

// Independent oracle: enumerate every complete path on a small integer domain.
// The generated observations and band endpoints are integers or exact binary halves.
function enumerate(q) {
  const { values, domain: [a, b], budgets, band: [left, right] } = q;
  const weight = (i) => q.weights ? q.weights[i] : 1;
  const hits = (z) => (left === null || (q.lowerClosed === false ? z > left : z >= left))
    && (right === null || (q.upperClosed === false ? z < right : z <= right));
  const bounds = budgets.map(() => [Infinity, -Infinity]), independent = [Infinity, -Infinity];
  function visit(i, previous, cost, count) {
    if (i === values.length) {
      independent[0] = Math.min(independent[0], count);
      independent[1] = Math.max(independent[1], count);
      budgets.forEach((v, j) => {
        if (cost <= v) {
          bounds[j][0] = Math.min(bounds[j][0], count);
          bounds[j][1] = Math.max(bounds[j][1], count);
        }
      });
    } else {
      for (let x = a; x <= b; ++x)
        visit(i + 1, x, cost + (i ? Math.abs(previous - x) : 0),
          count + weight(i) * hits(values[i] - x));
    }
  }
  visit(0, 0, 0, 0);
  return { bounds, independentBounds: independent,
    nominalCount: values.reduce((s, z, i) => s + weight(i) * hits(z), 0),
    denominator: values.reduce((s, _, i) => s + weight(i), 0) };
}
let seed = 0x1748b;
function rand(n) {
  seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
  return Math.floor(seed / 4294967296 * n);
}
for (let t = 0; t < 320; ++t) {
  const n = 1 + rand(5), a = rand(7) - 3, b = a + rand(7), lo = (rand(9) - 4) / 2;
  const q = { domain: [a, b], values: Array.from({ length: n }, () => (rand(21) - 10) / 2),
    band: [t % 17 ? lo : null, t % 23 ? lo + rand(9) / 2 : null],
    lowerClosed: !!rand(2), upperClosed: !!rand(2),
    budgets: t % 3 ? [rand(6), 1, 0, 1] : [1, 0] };
  if (t % 2) q.weights = q.values.map(() => rand(3) ? 1 : 0);
  const actual = solve(q);
  assert.deepEqual(actual.budgets, q.budgets);
  for (const [key, expected] of Object.entries(enumerate(q)))
    assert.deepEqual(actual[key], expected, "case " + t + ": " + key + " " + JSON.stringify(q));
}

// A missing middle reward leaves a single shared budget. The order (and duplicates) matters.
const base = { values: [0, 9, 1, 9, 0], weights: [1, 0, 1, 0, 1],
  band: [0, 0], domain: [0, 1], budgets: [2, 0, 1, 2] };
assert.deepEqual(solve(base).bounds, [[0, 3], [1, 2], [1, 2], [0, 3]]);
const emptyMask = solve({ ...base, weights: [0, 0, 0, 0, 0] });
assert.equal(emptyMask.denominator, 0);
assert.deepEqual(emptyMask.bounds, base.budgets.map(() => [0, 0]));

// Decimal strings one part in 10^30 above/below an endpoint must not round onto it.
const dec = { values: ["1e-30", "1", "1.000000000000000000000000000001", "-1e-30", "0"],
  band: ["0", "1"], domain: [0, 0], budgets: [0] };
for (const [lowerClosed, upperClosed, n] of [[true, true, 3], [false, false, 1],
  [true, false, 2], [false, true, 2]])
  assert.deepEqual(solve({ ...dec, lowerClosed, upperClosed }).bounds, [[n, n]]);

const official = solve(big);
assert.deepEqual(official.budgets, [0, 1, 4, 16, 64]);
assert.deepEqual(official.bounds, [[63, 91], [63, 91], [63, 92], [63, 96], [51, 96]]);
assert.deepEqual([official.nominalCount, official.denominator, ...official.independentBounds], [84, 96, 33, 96]);

for (const invalid of [{ values: ["NaN"] }, { values: [Infinity] }, { band: [5, 1] },
  { domain: [0, 401] }, { domain: [0, 0.5] }, { budgets: [] }, { budgets: [-1] },
  { budgets: [65] }, { weights: [] }, { weights: [2, 1, 1, 1, 1] }, { lowerClosed: "false" }])
  assert.throws(() => solve({ ...dec, ...invalid }), Error);
console.log("Browser solver passed: 320 exhaustive cases, decimal boundaries, masks, BIG001, and invalid inputs.");
