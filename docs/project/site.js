"use strict";

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

document.querySelectorAll('input[name="budget"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    if (!radio.checked) return;
    const pair = big001Titr[radio.value];
    if (!pair) return;
    document.getElementById("lower-count").textContent = pair[0];
    document.getElementById("upper-count").textContent = pair[1];
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
