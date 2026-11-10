"use strict";

// Deliberately tiny invented examples. All pairs and witnesses were checked
// against local/global/gap/reference solve_glucose and original-row enumeration.
// This page displays fixed exact examples; it does not run the research solver.
const toyExamples = Object.freeze({
  single: {
    title: "A zero budget still allows a constant offset.",
    story: "A reading of 141 is just above the band. Subtracting 0 leaves it outside; subtracting 1 gives 140, which is inside.",
    values: [141], weights: [1],
    bounds: { 0: [0, 1], 1: [0, 1] },
    paths: { 0: [[0], [1]], 1: [[0], [1]] },
    lessons: {
      0: "Budget 0 means no change between offsets. It does not force the offset to be 0. Either constant choice is allowed, giving the exact pair [0,1].",
      1: "With one reading, there is no between-row movement to spend. Either offset is allowed, so the exact pair remains [0,1]."
    },
    extra: "This is a one-reading illustration of free endpoints: the initial offset does not spend the movement budget."
  },
  shared: {
    title: "Two readings, tied together.",
    story: "The first reading, 70, is in the band at offset 0. The second, 141, enters the band at offset 1. Can we count both?",
    values: [70, 141], weights: [1, 1],
    bounds: { 0: [1, 1], 1: [0, 2] },
    paths: { 0: [[0, 0], [1, 1]], 1: [[1, 0], [0, 1]] },
    lessons: {
      0: "At budget 0, the offsets must stay constant. Choosing [0,0] counts only the first reading; choosing [1,1] counts only the second. The exact pair is [1,1].",
      1: "One unit can move the offset from 0 to 1, putting both readings in the band. Moving from 1 to 0 puts both outside. The exact pair expands to [0,2]."
    },
    extra: "Giving each row its own free choice would count both. A shared budget of 0 does not allow the offset path [0,1]."
  },
  masked: {
    title: "Skip a reward, keep the same budget.",
    story: "Insert a reading of 100 between 70 and 141, but give it weight 0. It contributes no counted hit. The other two readings still share one movement budget.",
    values: [70, 100, 141], weights: [1, 0, 1],
    bounds: { 0: [1, 1], 1: [0, 2] },
    paths: { 0: [[0, 0, 0], [1, 1, 1]], 1: [[1, 0, 0], [0, 0, 1]] },
    lessons: {
      0: "At budget 0, the offsets stay constant across all three rows. The masked reading adds nothing to the score. Exactly one of the two counted readings is in the band: [1,1].",
      1: "One unit of total movement still gives the exact pair [0,2]. The paths below spend that unit once, before or after the masked reading."
    },
    extra: "Masking is not a budget reset. The offset path [0,1,0] spends 2 units, even though the middle row is masked; it is inadmissible at budgets 0 and 1."
  }
});

const toyTabs = Array.from(document.querySelectorAll("[data-scenario]"));
let toyScenario = "shared";
let toyBudget = 0;

function toyRow(label, values, weights, className = "") {
  const row = document.createElement("tr");
  row.className = className;
  const heading = document.createElement("th");
  heading.scope = "row";
  heading.textContent = label;
  row.appendChild(heading);
  values.forEach((value, index) => {
    const cell = document.createElement("td");
    cell.textContent = value;
    if (weights[index] === 0) cell.className = "toy-masked";
    row.appendChild(cell);
  });
  return row;
}

function renderToyExample(announce = true) {
  const example = toyExamples[toyScenario];
  const pair = example.bounds[toyBudget];
  const panel = document.getElementById("toy-panel");
  document.getElementById("toy-heading").textContent = example.title;
  document.getElementById("toy-story").textContent = example.story;
  document.getElementById("toy-lesson").textContent = example.lessons[toyBudget];
  document.getElementById("toy-extra").textContent = example.extra;
  document.getElementById("toy-pair").textContent = `[${pair.join(",")}]`;
  const countedRows = example.weights.reduce((sum, weight) => sum + weight, 0);
  document.getElementById("toy-denominator").textContent = `among ${countedRows} counted reading${countedRows === 1 ? "" : "s"}`;
  panel.setAttribute("aria-labelledby", `toy-tab-${toyScenario}`);
  toyTabs.forEach((tab) => {
    const selected = tab.dataset.scenario === toyScenario;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
  });

  const table = document.getElementById("toy-table");
  const caption = document.createElement("caption");
  caption.textContent = "Two paths that attain the exact bounds";
  const head = document.createElement("thead");
  const headingRow = document.createElement("tr");
  const corner = document.createElement("th");
  corner.scope = "col";
  corner.textContent = "In temporal order";
  headingRow.appendChild(corner);
  example.values.forEach((_, index) => {
    const heading = document.createElement("th");
    heading.scope = "col";
    heading.textContent = index + 1;
    if (example.weights[index] === 0) {
      const label = document.createElement("span");
      label.textContent = "masked";
      heading.appendChild(label);
      heading.className = "toy-masked";
    }
    headingRow.appendChild(heading);
  });
  head.appendChild(headingRow);
  const observed = document.createElement("tbody");
  observed.appendChild(toyRow("Observed reading", example.values, example.weights, "toy-observed"));
  observed.appendChild(toyRow("Count this row? (weight)", example.weights, example.weights));
  table.replaceChildren(caption, head, observed);

  example.paths[toyBudget].forEach((path, boundIndex) => {
    const corrected = example.values.map((value, index) => value - path[index]);
    const hits = corrected.map((value, index) => example.weights[index] * Number(value >= 70 && value <= 140));
    const movement = path.slice(1).reduce((sum, value, index) => sum + Math.abs(value - path[index]), 0);
    const body = document.createElement("tbody");
    body.className = `toy-path ${boundIndex === 0 ? "toy-minimum" : "toy-maximum"}`;
    const row = document.createElement("tr");
    row.className = "toy-path-heading";
    const heading = document.createElement("th");
    heading.scope = "rowgroup";
    heading.colSpan = example.values.length + 1;
    heading.textContent = `${boundIndex === 0 ? "Minimum" : "Maximum"}: ${pair[boundIndex]} hit${pair[boundIndex] === 1 ? "" : "s"} `;
    const used = document.createElement("span");
    used.textContent = `movement used: ${movement} / ${toyBudget}`;
    heading.appendChild(used);
    row.appendChild(heading);
    body.appendChild(row);
    body.appendChild(toyRow("Offset", path, example.weights));
    body.appendChild(toyRow("Corrected (reading − offset)", corrected, example.weights));
    body.appendChild(toyRow("Counted hit", hits, example.weights, "toy-hits"));
    table.appendChild(body);
  });

  if (announce) {
    document.getElementById("toy-status").textContent = `${example.title} Budget ${toyBudget}: exact minimum ${pair[0]}, maximum ${pair[1]}. ${example.lessons[toyBudget]}`;
  }
}

if (toyTabs.length) {
  document.querySelector(".toy-tabs").hidden = false;
  document.querySelector(".toy-budget-picker").hidden = false;
  toyTabs.forEach((tab, index) => {
    tab.addEventListener("click", () => {
      toyScenario = tab.dataset.scenario;
      renderToyExample();
    });
    tab.addEventListener("keydown", (event) => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % toyTabs.length;
      if (event.key === "ArrowLeft") next = (index + toyTabs.length - 1) % toyTabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = toyTabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      toyTabs[next].focus();
      toyScenario = toyTabs[next].dataset.scenario;
      renderToyExample();
    });
  });
  document.querySelectorAll('input[name="toy-budget"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      if (!radio.checked) return;
      toyBudget = Number(radio.value);
      renderToyExample();
    });
  });
  renderToyExample(false);
}

// Fixed original Figure 2 payload, not a solver or interpolated estimate.
const big001Titr = Object.freeze({
  0: [63, 91],
  1: [63, 91],
  4: [63, 92],
  16: [63, 96],
  64: [51, 96]
});

const budgetNotes = {
  0: "At v = 0, the exact TITR count pair is [63,91]. Every constant offset in D is allowed.",
  1: "At v = 1, the exact TITR count pair is [63,91] out of 96.",
  4: "At v = 4, the exact TITR count pair is [63,92] out of 96.",
  16: "At v = 16, the exact TITR count pair is [63,96] out of 96.",
  64: "At v = 64, the exact TITR count pair is [51,96] out of 96."
};

// Opening film: honour reduced-motion preferences by showing the poster with controls instead of autoplay.
const openingFilm = document.getElementById("opening-film");
if (openingFilm && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  openingFilm.removeAttribute("autoplay");
  openingFilm.pause();
  openingFilm.controls = true;
}

document.querySelectorAll('input[name="budget"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    if (!radio.checked) return;
    const pair = big001Titr[radio.value];
    if (!pair) return;
    document.getElementById("lower-count").textContent = pair[0];
    document.getElementById("upper-count").textContent = pair[1];
    // Endpoint positions encode only the exact extrema, not attainable interiors.
    const lowerX = 18 + 244 * pair[0] / 96;
    const upperX = 18 + 244 * pair[1] / 96;
    document.getElementById("count-range-line").setAttribute("d", `M${lowerX} 36H${upperX}`);
    document.getElementById("count-min-dot").setAttribute("cx", lowerX);
    document.getElementById("count-max-dot").setAttribute("cx", upperX);
    document.getElementById("count-range-title").textContent = `Exact count extrema: ${pair[0]} and ${pair[1]} out of 96`;
    document.getElementById("budget-explanation").textContent = budgetNotes[radio.value];
    document.getElementById("budget-status").textContent = budgetNotes[radio.value];
  });
});

function fallbackCopy(value) {
  const selection = document.getSelection();
  const previousRanges = selection ? Array.from({ length: selection.rangeCount }, (_, i) => selection.getRangeAt(i).cloneRange()) : [];
  const focusedElement = document.activeElement;
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.cssText = "position:fixed;left:-9999px;top:0;";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (focusedElement instanceof HTMLElement) focusedElement.focus({ preventScroll: true });
  if (selection) {
    selection.removeAllRanges();
    previousRanges.forEach((range) => selection.addRange(range));
  }
  if (!copied) throw new Error("Clipboard unavailable");
}

document.querySelectorAll("[data-copy]").forEach((button) => {
  const originalText = button.innerHTML;
  let resetTimer;
  button.addEventListener("click", async () => {
    const source = document.getElementById(button.dataset.copy);
    if (!source) return;
    try {
      const value = source.textContent.trim();
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(value);
      } else {
        fallbackCopy(value);
      }
      button.textContent = "Copied";
      document.getElementById("copy-status").textContent = "Copied to clipboard.";
    } catch (_) {
      button.textContent = "Select and copy below";
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(source);
      selection.removeAllRanges();
      selection.addRange(range);
      document.getElementById("copy-status").textContent = "Clipboard unavailable. The text is selected for manual copying.";
    }
    clearTimeout(resetTimer);
    resetTimer = window.setTimeout(() => { button.innerHTML = originalText; }, 2600);
  });
});
