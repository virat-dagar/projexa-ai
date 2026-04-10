const editor = document.getElementById("editor");
const blockFormat = document.getElementById("blockFormat");
const fontFamily = document.getElementById("fontFamily");
const fontSize = document.getElementById("fontSize");
const lineSpacing = document.getElementById("lineSpacing");
const sessionDuration = document.getElementById("sessionDuration");
const wordCount = document.getElementById("wordCount");
const charCount = document.getElementById("charCount");
const backendStatus = document.getElementById("backendStatus");
const editorStatus = document.getElementById("editorStatus");
const submitResult = document.getElementById("submitResult");
const riskBadge = document.getElementById("riskBadge");
const analysisSummary = document.getElementById("analysisSummary");
const metricList = document.getElementById("metricList");
const riskSignals = document.getElementById("riskSignals");
const reassuringSignals = document.getElementById("reassuringSignals");

const STORAGE_KEY = "writetrace-draft";
const LARGE_INSERT_THRESHOLD = 200;
const API_BASE = window.location.hostname === "localhost"
  ? "http://127.0.0.1:8000"
  : "https://projexa-ai.onrender.com";
  const eventLog = [];

const sessionStart = Date.now();
let lastKeyTime = sessionStart;
let lastText = "";

document.execCommand("styleWithCSS", false, true);

function ensureEditorSeed() {
  if (!editor.innerHTML.trim()) {
    editor.innerHTML = "<p><br></p>";
  }
}

function getPlainText() {
  return editor.innerText.replace(/\u00a0/g, " ").replace(/\n{3,}/g, "\n\n").trim();
}

function getWordCount(text) {
  return text ? text.split(/\s+/).filter(Boolean).length : 0;
}

function formatDuration(totalSeconds) {
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function updateStats() {
  const text = getPlainText();
  wordCount.textContent = String(getWordCount(text));
  charCount.textContent = String(text.length);
}

function updateSessionClock() {
  const seconds = Math.floor((Date.now() - sessionStart) / 1000);
  sessionDuration.textContent = formatDuration(seconds);
}

function saveDraft(showMessage = false) {
  localStorage.setItem(STORAGE_KEY, editor.innerHTML);
  if (showMessage) {
    setStatus("Draft saved locally on this device.");
  }
}

function restoreDraft() {
  const draft = localStorage.getItem(STORAGE_KEY);
  if (draft) {
    editor.innerHTML = draft;
    setStatus("Restored your last local draft.");
  }
}

function setStatus(message, tone = "") {
  editorStatus.textContent = message;
  editorStatus.dataset.tone = tone;
}

function setSubmitMessage(message, tone = "") {
  submitResult.textContent = message;
  submitResult.className = "submit-result";
  if (tone) {
    submitResult.classList.add(`is-${tone}`);
  }
}

function setBackendStatus(message, tone = "neutral") {
  backendStatus.textContent = message;
  backendStatus.dataset.state = tone;
}

function focusEditor() {
  ensureEditorSeed();
  editor.focus();
}

function selectionInsideEditor() {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) {
    return false;
  }

  return editor.contains(selection.anchorNode);
}

function runCommand(command, value = null) {
  focusEditor();
  document.execCommand(command, false, value);
  editor.dispatchEvent(new Event("input", { bubbles: true }));
}

function applyBlockFormat(tagName) {
  runCommand("formatBlock", `<${tagName}>`);
  setStatus(`Applied ${tagName.toLowerCase()} formatting.`);
}

function applyFontFamily(family) {
  runCommand("fontName", family);
  setStatus("Updated font family.");
}

function applyFontSize(size) {
  focusEditor();
  document.execCommand("fontSize", false, "7");

  editor.querySelectorAll('font[size="7"]').forEach((fontNode) => {
    const span = document.createElement("span");
    span.style.fontSize = `${size}pt`;
    span.innerHTML = fontNode.innerHTML;
    fontNode.replaceWith(span);
  });

  editor.dispatchEvent(new Event("input", { bubbles: true }));
  setStatus(`Applied ${size} pt text.`);
}

function getClosestBlock(node) {
  let current = node && node.nodeType === Node.TEXT_NODE ? node.parentElement : node;

  while (current && current !== editor) {
    if (/^(P|H1|H2|BLOCKQUOTE|LI|DIV|TD|TH)$/.test(current.tagName)) {
      return current;
    }
    current = current.parentElement;
  }

  return editor.firstElementChild || editor;
}

function getSelectedBlocks() {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0 || !editor.contains(selection.anchorNode)) {
    return [];
  }

  const range = selection.getRangeAt(0);
  const blocks = new Set();
  const fallbackBlock = getClosestBlock(selection.anchorNode);

  if (fallbackBlock) {
    blocks.add(fallbackBlock);
  }

  const walker = document.createTreeWalker(
    editor,
    NodeFilter.SHOW_ELEMENT,
    {
      acceptNode(node) {
        return /^(P|H1|H2|BLOCKQUOTE|LI|TD|TH)$/.test(node.tagName)
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_SKIP;
      }
    }
  );

  let currentNode = walker.nextNode();
  while (currentNode) {
    if (range.intersectsNode(currentNode)) {
      blocks.add(currentNode);
    }
    currentNode = walker.nextNode();
  }

  return Array.from(blocks);
}

function applyLineSpacing(value) {
  const blocks = getSelectedBlocks();
  if (!blocks.length) {
    setStatus("Place the cursor in a paragraph or select text to change spacing.", "warning");
    return;
  }

  blocks.forEach((block) => {
    block.style.lineHeight = value;
  });

  setStatus(`Line spacing set to ${value}.`);
  saveDraft();
}

function insertTable() {
  const tableMarkup = [
    "<table>",
    "<tbody>",
    "<tr><td>Column 1</td><td>Column 2</td><td>Column 3</td></tr>",
    "<tr><td><br></td><td><br></td><td><br></td></tr>",
    "<tr><td><br></td><td><br></td><td><br></td></tr>",
    "</tbody>",
    "</table>",
    "<p><br></p>"
  ].join("");

  runCommand("insertHTML", tableMarkup);
  setStatus("Inserted a 3 x 3 table.");
}

function exportToPdf() {
  setStatus("Opening the print dialog. Choose 'Save as PDF' in your browser.");
  window.print();
}

function createMetricRow(label, value) {
  const wrapper = document.createElement("div");
  wrapper.className = "metric-row";

  const term = document.createElement("dt");
  term.textContent = label;

  const description = document.createElement("dd");
  description.textContent = value;

  wrapper.append(term, description);
  return wrapper;
}

function renderSignalList(target, signals, emptyMessage) {
  target.innerHTML = "";

  if (!signals.length) {
    const item = document.createElement("li");
    item.textContent = emptyMessage;
    target.appendChild(item);
    return;
  }

  signals.forEach((signal) => {
    const item = document.createElement("li");
    item.textContent = `${signal.label}: ${signal.detail}`;
    target.appendChild(item);
  });
}

function renderAnalysis(data) {
  const riskLevel = data.risk_level || "low";
  const score = data.risk_score ?? data.risk ?? 0;
  const metrics = data.metrics || {};
  const signals = Array.isArray(data.signals) ? data.signals : [];

  riskBadge.className = "risk-badge";
  riskBadge.classList.add(`risk-badge-${riskLevel}`);
  riskBadge.textContent = `${riskLevel.toUpperCase()} RISK · ${score}/100`;

  analysisSummary.textContent = data.summary || "Submission scored successfully.";

  metricList.innerHTML = "";
  metricList.append(
    createMetricRow("Time spent", `${metrics.time_spent_minutes ?? "--"} min`),
    createMetricRow("Words per minute", String(metrics.words_per_minute ?? "--")),
    createMetricRow("Paste ratio", `${metrics.paste_ratio_percent ?? "--"}%`),
    createMetricRow("Typed ratio", `${metrics.typed_ratio_percent ?? "--"}%`),
    createMetricRow("Paste events", String(metrics.paste_events ?? "--")),
    createMetricRow("Largest paste", `${metrics.largest_paste_chars ?? "--"} chars`),
    createMetricRow("Sudden inserts", String(metrics.sudden_inserts ?? "--")),
    createMetricRow("Key events", String(metrics.key_events ?? "--"))
  );

  renderSignalList(
    riskSignals,
    signals.filter((signal) => signal.direction === "risk"),
    "No major risk signals were detected."
  );

  renderSignalList(
    reassuringSignals,
    signals.filter((signal) => signal.direction === "reassuring"),
    "No reassuring signals were recorded for this submission."
  );
}

async function checkBackendHealth() {
  setBackendStatus("Checking...", "neutral");

  try {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed with ${response.status}`);
    }

    setBackendStatus("Online", "online");
  } catch (error) {
    console.error("Backend health check failed:", error);
    setBackendStatus("Offline", "offline");
  }
}

function trackKeyboardEvent(event) {
  if (!editor.contains(event.target)) {
    return;
  }

  const now = Date.now();

  eventLog.push({
    type: "key",
    key: event.key,
    time: now,
    gap: now - lastKeyTime
  });

  lastKeyTime = now;
}

function trackPaste(event) {
  const pastedText = (event.clipboardData || window.clipboardData).getData("text");

  eventLog.push({
    type: "paste",
    length: pastedText.length,
    words: getWordCount(pastedText.trim()),
    time: Date.now()
  });
}

function trackInput() {
  const currentText = getPlainText();
  const delta = currentText.length - lastText.length;
  const timestamp = Date.now();

  eventLog.push({
    type: "edit",
    length: currentText.length,
    delta,
    words: getWordCount(currentText),
    time: timestamp
  });

  if (delta > 50) {
    eventLog.push({
      type: "large_insert",
      length: delta,
      time: timestamp
    });
  }

  if (delta > LARGE_INSERT_THRESHOLD) {
    eventLog.push({
      type: "sudden_insert",
      length: delta,
      time: timestamp
    });
  }

  lastText = currentText;
  updateStats();
  saveDraft();
}

async function submitAssignment() {
  const text = getPlainText();
  const sessionEnd = Date.now();

  if (!text) {
      setSubmitMessage("Write something before submitting.", "error");
      return;
  }

  const payload = {
    text,
    total_chars: text.length,
    total_words: getWordCount(text),
    startTime: sessionStart,
    endTime: sessionEnd,
    duration_seconds: Math.floor((sessionEnd - sessionStart) / 1000),
    events: eventLog
  };

  setSubmitMessage("Submitting to the server...");
  setStatus("Sending assignment and behavior log to the backend.");

  try {
    const response = await fetch(`${API_BASE}/submit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    const data = await response.json();
    renderAnalysis(data);
    setSubmitMessage(
      `Backend connected. Risk score ${data.risk_score ?? data.risk}/100 with ${data.risk_level ?? "unknown"} risk.`,
      "success"
    );
    setStatus("Submission finished. The analysis panel has been updated.");
    setBackendStatus("Online", "online");
    console.log("Submission payload", payload);
    console.log("Server response", data);
  } catch (error) {
    console.error("Submission failed:", error);
    setSubmitMessage("Submission failed. Make sure the FastAPI backend is running on port 8000.", "error");
    setStatus("Could not reach the backend. Start the local API and try again.", "error");
    setBackendStatus("Offline", "offline");
  }
}

function seedEditorFormatting() {
  editor.style.fontFamily = fontFamily.value;
  editor.style.fontSize = `${fontSize.value}pt`;
  editor.style.lineHeight = lineSpacing.value;
}

function bindToolbar() {
  document.querySelectorAll(".tool-button").forEach((button) => {
    button.addEventListener("mousedown", (event) => {
      event.preventDefault();
    });

    button.addEventListener("click", () => {
      runCommand(button.dataset.command);
    });
  });

  blockFormat.addEventListener("change", () => applyBlockFormat(blockFormat.value));
  fontFamily.addEventListener("change", () => applyFontFamily(fontFamily.value));
  fontSize.addEventListener("change", () => applyFontSize(fontSize.value));
  lineSpacing.addEventListener("change", () => applyLineSpacing(lineSpacing.value));

  document.getElementById("insertTable").addEventListener("click", insertTable);
  document.getElementById("saveDraft").addEventListener("click", () => saveDraft(true));
  document.getElementById("exportPDF").addEventListener("click", exportToPdf);
  document.getElementById("submitAssignment").addEventListener("click", submitAssignment);
}

function syncToolbarState() {
  if (!selectionInsideEditor()) {
    return;
  }

  const activeBlock = getClosestBlock(window.getSelection().anchorNode);
  if (activeBlock && /^(P|H1|H2|BLOCKQUOTE)$/.test(activeBlock.tagName)) {
    blockFormat.value = activeBlock.tagName;
  }
}

function init() {
  restoreDraft();
  seedEditorFormatting();
  updateStats();
  updateSessionClock();
  bindToolbar();
  lastText = getPlainText();

  editor.addEventListener("paste", trackPaste);
  editor.addEventListener("input", trackInput);
  editor.addEventListener("mouseup", syncToolbarState);
  editor.addEventListener("keyup", syncToolbarState);
  document.addEventListener("keydown", trackKeyboardEvent);
  setInterval(updateSessionClock, 1000);
  checkBackendHealth();
  setInterval(checkBackendHealth, 15000);

  window.addEventListener("beforeunload", () => saveDraft());
  setStatus("Editor ready. Drafts are saved locally as you type.");
}

window.submitAssignment = submitAssignment;
init();
