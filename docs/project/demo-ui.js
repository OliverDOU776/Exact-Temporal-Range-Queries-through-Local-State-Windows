"use strict";

// UI only. Exact predicate compilation and LocalWindows run in solver-worker.js.
(() => {
  const form = document.getElementById("query-form");
  if (!form) return;
  const el = (id) => document.getElementById(id);
  let worker = null;
  let requestId = 0;
  let pendingPayload = null;
  let lastDownload = null;
  let source = "Teaching example.";
  let busy = false;
  const limits = "Use at most 2,000 rows, 401 integer offset states and 16 budgets from 0 to 64.";

  function status(message, state, error = false) {
    el("query-status").textContent = message;
    el("query-state").textContent = state;
    el("query-answer").classList.toggle("query-error", error);
  }
  function setBusy(value) {
    busy = value;
    el("run-query").disabled = value;
    el("run-query").textContent = value ? "Computing…" : "Compute exact bounds";
    el("cancel-query").hidden = !value;
    el("query-answer").setAttribute("aria-busy", String(value));
    form.querySelectorAll("input, textarea").forEach((input) => { input.disabled = value; });
    document.querySelectorAll(".demo-preset-row button").forEach((button) => { button.disabled = value; });
  }
  function invalidate() {
    if (busy) return;
    lastDownload = null;
    el("query-output").hidden = true;
    el("query-placeholder").hidden = false;
    status("Inputs changed. Compute to get the exact bounds for this query.", "Ready");
  }
  function fields(payload) {
    el("query-data").value = "glucose,weight\n" + payload.values.map((value, i) => `${value},${payload.weights ? payload.weights[i] : 1}`).join("\n");
    el("band-lower").value = payload.band[0];
    el("band-upper").value = payload.band[1];
    el("domain-lower").value = payload.domain[0];
    el("domain-upper").value = payload.domain[1];
    el("query-budgets").value = payload.budgets.join(", ");
    el("lower-closed").checked = payload.lowerClosed !== false;
    el("upper-closed").checked = payload.upperClosed !== false;
  }
  function splitRow(row) {
    // Quoted CSV fields (including escaped quotation marks) are supported.
    const cells = [];
    let text = "", quoted = false;
    for (let i = 0; i < row.length; i++) {
      const char = row[i];
      if (char === '"') {
        if (quoted && row[i + 1] === '"') { text += '"'; i++; }
        else quoted = !quoted;
      } else if ((char === "," || char === ";" || char === "\t") && !quoted) {
        cells.push(text.trim()); text = "";
      } else text += char;
    }
    if (quoted) throw new Error("A CSV row has an unclosed quotation mark.");
    cells.push(text.trim());
    return cells;
  }
  function parseReadings(text) {
    const lines = text.replace(/^\uFEFF/, "").trim().split(/\r?\n/).filter((line) => line.trim());
    if (!lines.length) throw new Error("Paste at least one reading first.");
    const rows = lines.map(splitRow);
    const header = rows[0].map((value) => value.toLowerCase().replace(/[\s_()\-/]/g, ""));
    const valueColumn = header.findIndex((value) => ["glucose", "reading", "value", "glucosevalue", "glucosevaluemgdl", "glucosemgdl"].includes(value));
    const weightColumn = header.findIndex((value) => ["weight", "mask", "include"].includes(value));
    if (valueColumn >= 0) {
      const values = [], weights = [];
      for (const [i, row] of rows.slice(1).entries()) {
        if (!row[valueColumn]) throw new Error(`Missing reading on CSV data row ${i + 1}.`);
        values.push(row[valueColumn]);
        const weight = weightColumn < 0 ? 1 : Number(row[weightColumn]);
        if (weightColumn >= 0 && row[weightColumn] !== "0" && row[weightColumn] !== "1") throw new Error(`Weight must be 0 or 1 on CSV data row ${i + 1}.`);
        weights.push(weight);
      }
      return { values, weights };
    }
    if (lines.length > 1 && rows.every((row) => row.length === 2 && ["0", "1"].includes(row[1]))) {
      return { values: rows.map((row) => row[0]), weights: rows.map((row) => Number(row[1])) };
    }
    return { values: rows.flatMap((row) => row.flatMap((cell) => cell.split(/\s+/))).filter(Boolean) };
  }
  function getPayload() {
    const readings = parseReadings(el("query-data").value);
    const budgetText = el("query-budgets").value.trim();
    if (!budgetText || /(^\s*,|,\s*$|,\s*,)/.test(budgetText)) throw new Error("Enter budgets as comma-separated integers, such as 0, 1, 4.");
    const parts = budgetText.split(/[,\s]+/);
    if (parts.some((value) => !/^\d+$/.test(value))) throw new Error("Each budget must be a nonnegative integer.");
    if (!el("band-lower").value.trim() || !el("band-upper").value.trim()) throw new Error("Enter both range endpoints.");
    return { ...readings, band: [el("band-lower").value.trim(), el("band-upper").value.trim()], domain: [Number(el("domain-lower").value), Number(el("domain-upper").value)], budgets: parts.map(Number), lowerClosed: el("lower-closed").checked, upperClosed: el("upper-closed").checked };
  }
  function svgElement(name, attrs = {}, text) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function drawTrace(payload) {
    const values = payload.values.map(Number), band = payload.band.map(Number);
    if (![...values, ...band].every(Number.isFinite)) {
      const note = document.createElement("p");
      note.className = "field-help";
      note.textContent = "The numeric scale exceeds this plot's display range. The exact count computation still uses your decimal inputs.";
      el("query-trace").replaceChildren(note);
      return;
    }
    const min = Math.min(...values, ...band), max = Math.max(...values, ...band);
    const pad = Math.max((max - min) * 0.14, 1), low = min - pad, high = max + pad;
    if (!Number.isFinite(high - low) || high <= low) {
      const note = document.createElement("p");
      note.className = "field-help";
      note.textContent = "The numeric scale exceeds this plot's display range. The exact count computation still uses your decimal inputs.";
      el("query-trace").replaceChildren(note);
      return;
    }
    const x = (i) => 52 + (values.length === 1 ? 214 : i / (values.length - 1) * 430);
    const y = (v) => 170 - (v - low) / (high - low) * 142;
    const svg = svgElement("svg", { viewBox: "0 0 520 212", role: "img", "aria-label": `${values.length} input readings in row order. Target band from ${payload.band[0]} to ${payload.band[1]}. This plot shows original values, not corrected paths.` });
    svg.append(svgElement("rect", { x: 52, y: y(band[1]), width: 430, height: Math.max(0, y(band[0]) - y(band[1])), fill: "#eaf3fb" }));
    for (let i = 0; i < 2; i++) {
      svg.append(svgElement("line", { x1: 52, x2: 482, y1: y(band[i]), y2: y(band[i]), stroke: "#8baaca", "stroke-dasharray": (i === 0 ? payload.lowerClosed : payload.upperClosed) ? "none" : "4 3" }));
      svg.append(svgElement("text", { x: 44, y: y(band[i]) + 4, "text-anchor": "end" }, Number(band[i].toPrecision(5)).toString()));
    }
    svg.append(svgElement("path", { d: "M52 24V170H482", stroke: "#9ba8b5", fill: "none" }));
    svg.append(svgElement("polyline", { points: values.map((v, i) => `${x(i)},${y(v)}`).join(" "), stroke: "#263f59", "stroke-width": 1.6, fill: "none" }));
    values.forEach((v, i) => { if (values.length <= 160 || payload.weights?.[i] === 0) svg.append(svgElement("circle", { cx: x(i), cy: y(v), r: payload.weights?.[i] === 0 ? 3.5 : 2, fill: payload.weights?.[i] === 0 ? "#fff" : "#263f59", stroke: "#263f59", "stroke-width": 1 })); });
    svg.append(svgElement("text", { x: 52, y: 190, "text-anchor": "middle" }, "1"));
    if (values.length > 1) svg.append(svgElement("text", { x: 482, y: 190, "text-anchor": "middle" }, String(values.length)));
    svg.append(svgElement("text", { x: 267, y: 208, "text-anchor": "middle" }, "Input row order · original readings"));
    el("query-trace").replaceChildren(svg);
  }
  function showResult(result, payload) {
    el("query-output").hidden = false;
    el("query-placeholder").hidden = true;
    el("result-denominator").textContent = result.denominator;
    el("result-nominal").textContent = result.nominalCount + (payload.domain[0] <= 0 && payload.domain[1] >= 0 ? "" : " (outside offset domain)");
    const tbody = el("query-result-rows");
    tbody.replaceChildren();
    result.bounds.forEach((pair, i) => {
      const row = document.createElement("tr");
      const percentage = result.denominator ? `${(100 * pair[0] / result.denominator).toFixed(2)}–${(100 * pair[1] / result.denominator).toFixed(2)}%` : "Unavailable (empty mask)";
      [result.budgets[i], pair[0], pair[1], percentage].forEach((value, j) => {
        const cell = document.createElement(j === 0 ? "th" : "td");
        if (j === 0) cell.scope = "row";
        cell.textContent = value;
        row.appendChild(cell);
      });
      tbody.appendChild(row);
    });
    const independent = result.independentBounds;
    const tighter = result.bounds.some((pair) => pair[0] > independent[0] || pair[1] < independent[1]);
    el("result-interpretation").textContent = `Choosing offsets independently per row gives [${independent.join(", ")}]. ${tighter ? "At least one requested shared budget gives tighter bounds: temporal coupling changes this report." : "These requested budgets reach the independent-row bounds for this input."} Percentages use the fixed count of included observations, rounded for display.`;
    const d = result.diagnostics;
    el("result-diagnostics").textContent = `Local State Windows · ${d.runs} sensitive runs · ${d.localWindows} active window${d.localWindows === 1 ? "" : "s"} · ${d.incidences} sensitive incidences · at most ${d.maxLocalStates} retained states in a solved window. Masked rows keep one shared budget.`;
    drawTrace(payload);
    lastDownload = { format: "lsw-browser-query-v1", input: payload, result, source, note: "Exact count extrema under the supplied integer-offset sensitivity model. Percentages displayed on the page are rounded. No timing benchmark or clinical calibration is implied." };
    status(`Computed ${result.bounds.length} exact budget answer${result.bounds.length === 1 ? "" : "s"} locally from ${payload.values.length} input rows.`, "Complete");
  }
  function run() {
    try {
      if (busy) return;
      const payload = getPayload();
      if (payload.values.length > 2000) throw new Error(limits);
      lastDownload = null;
      el("query-output").hidden = true;
      el("query-placeholder").hidden = false;
      worker?.terminate();
      worker = new Worker("project/solver-worker.js?v=usable-demo-20261109a");
      const id = ++requestId;
      pendingPayload = payload;
      worker.onmessage = (event) => {
        if (event.data.id !== requestId) return;
        setBusy(false);
        if (event.data.error) status(event.data.error, "Check input", true);
        else showResult(event.data.result, pendingPayload);
        worker.terminate(); worker = null;
      };
      worker.onerror = () => { setBusy(false); status("The browser worker could not run. Reload the page, or use the Python implementation linked below.", "Unable to compute", true); worker?.terminate(); worker = null; };
      setBusy(true);
      status("Compiling exact predicates and solving the requested shared-budget queries…", "Computing");
      worker.postMessage({ id, payload });
    } catch (error) { setBusy(false); status(error.message, "Check input", true); }
  }
  form.addEventListener("submit", (event) => { event.preventDefault(); run(); });
  form.addEventListener("input", () => { source = "User-provided sequence, processed locally."; el("demo-source").textContent = source; invalidate(); });
  el("cancel-query").addEventListener("click", () => { requestId++; worker?.terminate(); worker = null; setBusy(false); status("Computation cancelled. You can change the inputs and run again.", "Cancelled"); });
  function preset(masked) {
    fields({ values: masked ? [70, 100, 141] : [70, 141], weights: masked ? [1, 0, 1] : [1, 1], band: [70, 140], domain: [0, 1], budgets: [0, 1] });
    source = masked ? "Teaching example: the middle row has zero reward; it does not reset the movement budget." : "Teaching example: two readings and one shared budget.";
    el("demo-source").textContent = source;
    run();
  }
  el("preset-toy").addEventListener("click", () => preset(false));
  el("preset-mask").addEventListener("click", () => preset(true));
  el("preset-big").addEventListener("click", async () => {
    if (busy) return;
    invalidate();
    const token = ++requestId;
    setBusy(true);
    try {
      status("Loading the fixed public 96-reading example…", "Loading");
      const response = await fetch("demos/big001-input.json");
      if (!response.ok) throw new Error("The public example could not be loaded. You can still paste or import your own data.");
      const data = await response.json();
      if (token !== requestId) return;
      fields(data);
      source = "Public BIG001, 96 original readings. Cho, Kim, Bent & Dunn; BIG IDEAs Lab data v1.1.3; PhysioNet DOI 10.13026/aw6y-fc44; ODC-By. Original CSV lines 14–109. Offsets and budgets define a sensitivity scenario.";
      el("demo-source").textContent = source;
      setBusy(false);
      run();
    } catch (error) { if (token === requestId) { setBusy(false); status(error.message, "Unable to load", true); } }
  });
  el("query-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    if (busy) return;
    invalidate();
    const token = ++requestId;
    setBusy(true);
    status("Reading your file locally…", "Loading");
    try {
      if (file.size > 500000) throw new Error("Choose a file smaller than 500 KB. " + limits);
      const text = await file.text();
      if (token !== requestId) return;
      if (file.name.toLowerCase().endsWith(".json")) {
        const data = JSON.parse(text), input = data.input || data;
        if (!Array.isArray(input.values) || input.values.length === 0 || input.values.length > 2000) throw new Error("JSON must contain a nonempty values array with at most 2,000 readings.");
        if (input.weights !== undefined && (!Array.isArray(input.weights) || input.weights.length !== input.values.length || input.weights.some((value) => value !== 0 && value !== 1))) throw new Error("JSON weights must contain one 0 or 1 per reading.");
        for (const name of ["lowerClosed", "upperClosed"]) if (input[name] !== undefined && typeof input[name] !== "boolean") throw new Error(`JSON ${name} must be true or false.`);
        for (const name of ["band", "domain"]) if (input[name] !== undefined && (!Array.isArray(input[name]) || input[name].length !== 2)) throw new Error(`JSON ${name} must be a two-element array.`);
        if (input.budgets !== undefined && (!Array.isArray(input.budgets) || !input.budgets.length || input.budgets.length > 16 || input.budgets.some((value) => !Number.isInteger(value) || value < 0 || value > 64))) throw new Error("JSON budgets must contain 1–16 integers from 0 to 64.");
        fields({ ...input, band: input.band || [70, 140], domain: input.domain || [-30, 30], budgets: input.budgets || [0, 1, 4] });
      } else el("query-data").value = text;
      source = "User-imported sequence, read only in this browser.";
      el("demo-source").textContent = source;
      setBusy(false);
      status("File loaded locally. Check the range, offsets and budgets, then compute.", "Ready");
    } catch (error) { if (token === requestId) { setBusy(false); status(error.message, "Check file", true); } }
    finally { event.target.value = ""; }
  });
  el("download-result").addEventListener("click", () => {
    if (!lastDownload) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(lastDownload, null, 2) + "\n"], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = "local-state-windows-query.json"; anchor.click();
    status("JSON download requested. The file includes your input, query settings and exact answers.", "Export");
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  });

  const movies = {
    "csv-session": "Paste two readings, set the range and shared budgets, and compute exact bounds. Change 141 to 140, recompute, and download the query with its results. Actual application recording · silent, with on-screen captions.",
    "public-session": "Load 96 public readings, change allowed offsets from ±30 to ±10, recompute and export. At budget 4, the bounds change from [63,92] to [82,89] while the nominal count stays 84. Actual browser recording; idle pauses trimmed and reading holds added.",
    "masked-session": "Import a five-row CSV with a 0/1 count mask. Compute three budgets for the three counted rows, inspect the exact bounds, and download the query with its results. Actual application recording · silent, with on-screen captions."
  };
  const tabs = Array.from(document.querySelectorAll("[data-movie]"));
  function movie(tab) {
    const name = tab.dataset.movie, video = el("demo-video");
    video.pause();
    tabs.forEach((item) => { item.setAttribute("aria-selected", String(item === tab)); item.tabIndex = item === tab ? 0 : -1; });
    video.poster = `demos/${name}.png`;
    el("movie-captions").src = `demos/${name}.vtt`;
    video.querySelector("source").src = `demos/${name}.mp4`;
    video.load();
    el("movie-panel").setAttribute("aria-labelledby", tab.id);
    el("movie-caption").textContent = movies[name];
    el("movie-mp4").href = `demos/${name}.mp4`;
    el("movie-fallback").href = `demos/${name}.mp4`;
    el("movie-gif").href = `demos/${name}.gif`;
  }
  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => movie(tab));
    tab.addEventListener("keydown", (event) => {
      let index;
      if (event.key === "ArrowRight") index = (i + 1) % tabs.length;
      if (event.key === "ArrowLeft") index = (i + tabs.length - 1) % tabs.length;
      if (event.key === "Home") index = 0;
      if (event.key === "End") index = tabs.length - 1;
      if (index === undefined) return;
      event.preventDefault(); tabs[index].focus(); movie(tabs[index]);
    });
  });
  // A real, computed initial result makes the input/output contract immediate.
  run();
})();
