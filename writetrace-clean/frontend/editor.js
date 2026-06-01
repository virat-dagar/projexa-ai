const editor = document.getElementById("editor");
const blockFormat = document.getElementById("blockFormat");
const fontFamily = document.getElementById("fontFamily");
const fontSize = document.getElementById("fontSize");
const sessionDuration = document.getElementById("sessionDuration");
const wordCount = document.getElementById("wordCount");
const charCount = document.getElementById("charCount");
const backendStatus = document.getElementById("backendStatus");
const editorStatus = document.getElementById("editorStatus");
const submitResult = document.getElementById("submitResult");

const studentModeButton = document.getElementById("studentModeButton");
const teacherModeButton = document.getElementById("teacherModeButton");
const studentDashboard = document.getElementById("studentDashboard");
const teacherDashboard = document.getElementById("teacherDashboard");

const studentNameInput = document.getElementById("studentName");
const studentIdInput = document.getElementById("studentId");
const assignmentSelect = document.getElementById("assignmentSelect");
const assignmentPreview = document.getElementById("assignmentPreview");

const newAssignmentTitle = document.getElementById("newAssignmentTitle");
const newAssignmentDescription = document.getElementById("newAssignmentDescription");
const newAssignmentDueDate = document.getElementById("newAssignmentDueDate");
const newAssignmentMaxScore = document.getElementById("newAssignmentMaxScore");
const createAssignmentButton = document.getElementById("createAssignmentButton");
const teacherCreateStatus = document.getElementById("teacherCreateStatus");
const refreshTeacherData = document.getElementById("refreshTeacherData");
const teacherAssignmentList = document.getElementById("teacherAssignmentList");
const teacherSubmissionList = document.getElementById("teacherSubmissionList");
const teacherSubmissionDetail = document.getElementById("teacherSubmissionDetail");
const toolbar = document.getElementById("toolbar");
const submitAssignmentButton = document.getElementById("submitAssignment");

const STORAGE_KEY = "writetrace-draft";
const ASSIGNMENT_STATE_PREFIX = "writetrace-assignment-state-";
const LARGE_INSERT_THRESHOLD = 200;
const LOCAL_HOSTNAMES = new Set(["localhost", "127.0.0.1"]);
const RUNTIME_CONFIG = window.WRITETRACE_CONFIG || {};
const HAS_CONFIGURED_API_BASE = Object.prototype.hasOwnProperty.call(RUNTIME_CONFIG, "apiBaseUrl");

function normalizeApiBase(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

const API_BASE = HAS_CONFIGURED_API_BASE
  ? normalizeApiBase(RUNTIME_CONFIG.apiBaseUrl)
  : (LOCAL_HOSTNAMES.has(window.location.hostname) ? "http://127.0.0.1:8000" : "/api");

let eventLog = [];
let sessionStart = null;
let lastKeyTime = null;
let lastText = "";
let studentAssignments = [];
let selectedTeacherAssignmentId = "";
let currentAssignmentId = "";

document.execCommand("styleWithCSS", false, true);

function ensureSessionStarted(now = Date.now()) {
  if (typeof sessionStart !== "number") {
    sessionStart = now;
  }
  if (typeof lastKeyTime !== "number") {
    lastKeyTime = sessionStart;
  }
}

function setEditorEnabled(enabled) {
  const nextValue = enabled ? "true" : "false";
  if (editor.getAttribute("contenteditable") !== nextValue) {
    editor.setAttribute("contenteditable", nextValue);
  }

  editor.classList.toggle("is-disabled", !enabled);
  if (submitAssignmentButton) {
    submitAssignmentButton.disabled = !enabled;
  }

  if (toolbar) {
    toolbar.classList.toggle("is-disabled", !enabled);
    toolbar.querySelectorAll("button, select").forEach((control) => {
      // Keep mode switch buttons outside toolbar unaffected.
      if (control.id === "studentModeButton" || control.id === "teacherModeButton") {
        return;
      }
      control.disabled = !enabled;
    });
  }
}

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
  if (typeof sessionStart !== "number") {
    sessionDuration.textContent = "00:00";
    return;
  }

  const seconds = Math.floor((Date.now() - sessionStart) / 1000);
  sessionDuration.textContent = formatDuration(seconds);
}

function getAssignmentDraftKey(assignmentId = currentAssignmentId) {
  return assignmentId ? `${ASSIGNMENT_STATE_PREFIX}${assignmentId}` : STORAGE_KEY;
}

function createEmptyAssignmentState() {
  return {
    html: "",
    eventLog: [],
    sessionStart: null,
    lastKeyTime: null,
    lastText: ""
  };
}

function serializeAssignmentState() {
  return {
    html: editor.innerHTML,
    eventLog,
    sessionStart,
    lastKeyTime,
    lastText
  };
}

function applyAssignmentState(state) {
  editor.innerHTML = state.html || "";
  if (!editor.innerHTML.trim()) {
    ensureEditorSeed();
  }

  eventLog = Array.isArray(state.eventLog) ? state.eventLog : [];
  sessionStart = typeof state.sessionStart === "number" ? state.sessionStart : null;
  lastKeyTime = typeof state.lastKeyTime === "number" ? state.lastKeyTime : null;
  lastText = typeof state.lastText === "string" ? state.lastText : getPlainText();
  updateStats();
  updateSessionClock();
}

function readStoredAssignmentState(assignmentId = currentAssignmentId) {
  const rawValue = localStorage.getItem(getAssignmentDraftKey(assignmentId));
  if (!rawValue) {
    return null;
  }

  try {
    const parsedValue = JSON.parse(rawValue);
    if (parsedValue && typeof parsedValue === "object") {
      return parsedValue;
    }
  } catch (error) {
    return {
      ...createEmptyAssignmentState(),
      html: rawValue
    };
  }

  return null;
}

function saveDraft(showMessage = false, assignmentId = currentAssignmentId) {
  localStorage.setItem(getAssignmentDraftKey(assignmentId), JSON.stringify(serializeAssignmentState()));
  if (showMessage) {
    setStatus("Draft saved locally on this device.");
  }
}

function getStoredDraft(assignmentId = currentAssignmentId) {
  const storedState = readStoredAssignmentState(assignmentId);
  return storedState ? storedState.html : null;
}

function restoreDraft(assignmentId = currentAssignmentId) {
  const storedState = readStoredAssignmentState(assignmentId);
  if (storedState) {
    applyAssignmentState(storedState);
    setStatus("Restored this assignment's saved draft.");
  } else {
    applyAssignmentState(createEmptyAssignmentState());
    setStatus("Fresh assignment draft ready.");
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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
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
}

function applyFontFamily(family) {
  runCommand("fontName", family);
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

function getCurrentSectionLabel() {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) {
    return "Body";
  }

  const anchorBlock = getClosestBlock(selection.anchorNode);
  if (!anchorBlock) {
    return "Body";
  }

  let cursor = anchorBlock;
  while (cursor) {
    if (cursor.tagName === "H1" || cursor.tagName === "H2") {
      const headingText = cursor.innerText.trim();
      if (headingText) {
        return headingText.slice(0, 80);
      }
    }
    cursor = cursor.previousElementSibling;
  }

  return "Body";
}

function exportToPdf() {
  setStatus("Opening print dialog.");
  window.print();
}

function toggleMode(mode) {
  const isStudent = mode === "student";
  studentDashboard.classList.toggle("hidden", !isStudent);
  teacherDashboard.classList.toggle("hidden", isStudent);
  studentModeButton.classList.toggle("active", isStudent);
  teacherModeButton.classList.toggle("active", !isStudent);

  if (!isStudent) {
    loadTeacherAssignments();
  }
}

function persistCurrentAssignmentDraft() {
  if (currentAssignmentId) {
    saveDraft(false, currentAssignmentId);
  }
}

function renderAssignmentPreview() {
  const selected = studentAssignments.find((item) => item.id === assignmentSelect.value);
  if (!selected) {
    assignmentPreview.textContent = "No assignment selected.";
    return;
  }

  assignmentPreview.innerHTML = `
    <strong>${escapeHtml(selected.title)}</strong><br>
    Due: ${escapeHtml(selected.due_date)}<br>
    Max Score: ${escapeHtml(selected.max_score)}<br><br>
    ${escapeHtml(selected.description)}
  `;
}

function createTeacherItem({ title, body, meta, actionLabel, onClick }) {
  const item = document.createElement("div");
  item.className = "teacher-item";

  const header = document.createElement("div");
  header.className = "teacher-item-header";

  const titleEl = document.createElement("h3");
  titleEl.textContent = title;

  const actionButton = document.createElement("button");
  actionButton.type = "button";
  actionButton.className = "secondary-button";
  actionButton.textContent = actionLabel;
  actionButton.addEventListener("click", onClick);

  header.append(titleEl, actionButton);

  const bodyEl = document.createElement("p");
  bodyEl.textContent = body;

  const metaEl = document.createElement("p");
  metaEl.className = "meta";
  metaEl.textContent = meta;

  item.append(header, bodyEl, metaEl);
  return item;
}

function renderTeacherAssignments(assignments) {
  teacherAssignmentList.innerHTML = "";

  if (!assignments.length) {
    teacherAssignmentList.textContent = "No assignments yet.";
    return;
  }

  assignments.forEach((assignment) => {
    const avgRiskText = assignment.average_risk_score == null
      ? "No submissions yet"
      : `Average risk ${assignment.average_risk_score}/100`;

    const item = createTeacherItem({
      title: assignment.title,
      body: assignment.description,
      meta: `Due ${assignment.due_date} | Submissions ${assignment.submission_count} | ${avgRiskText}`,
      actionLabel: "View Submissions",
      onClick: () => loadAssignmentSubmissions(assignment.id)
    });

    teacherAssignmentList.appendChild(item);
  });
}

function renderTeacherSubmissions(assignment, submissions) {
  teacherSubmissionList.innerHTML = "";

  if (!submissions.length) {
    teacherSubmissionList.textContent = `No submissions yet for ${assignment.title}.`;
    return;
  }

  submissions.forEach((submission) => {
    const item = createTeacherItem({
      title: `${submission.student_name} (${submission.student_id})`,
      body: submission.summary,
      meta: `Risk ${submission.risk_score}/100 (${submission.risk_level}) | Pasted sections ${submission.paste_section_count} | Flagged sections ${submission.flagged_section_count}`,
      actionLabel: "Review",
      onClick: () => loadSubmissionDetail(submission.id)
    });

    teacherSubmissionList.appendChild(item);
  });
}

function renderDetailList(items) {
  if (!items.length) {
    return "<p>None detected.</p>";
  }

  return `<ul class="detail-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderSubmissionDetail(detail) {
  const analysis = detail.analysis || {};
  const metrics = analysis.metrics || {};
  const riskSignals = Array.isArray(analysis.signals)
    ? analysis.signals.filter((signal) => signal.direction === "risk")
    : [];

  const pastedRows = (detail.paste_sections || []).map((section) => {
    const snippet = section.snippet ? `"${section.snippet}"` : "No snippet captured";
    return `Section: ${section.target_section || "Body"} | Length: ${section.length_chars} chars | ${snippet}`;
  });

  const flaggedRows = (detail.flagged_sections || []).map((section) => {
    const reasonText = Array.isArray(section.reasons) ? section.reasons.join("; ") : "Flagged";
    return `Sentence ${section.section_index}: ${section.text_excerpt} (${reasonText})`;
  });

  const riskRows = riskSignals.slice(0, 6).map((signal) => `${signal.label}: ${signal.detail}`);

  teacherSubmissionDetail.innerHTML = `
    <strong>Assignment:</strong> ${escapeHtml(detail.assignment_title)}<br>
    <strong>Student:</strong> ${escapeHtml(detail.student_name)} (${escapeHtml(detail.student_id)})<br>
    <strong>Submitted:</strong> ${escapeHtml(detail.submitted_at)}

    <div class="detail-metric-grid">
      <div class="detail-chip">Combined Risk: ${escapeHtml(analysis.risk_score ?? "--")}/100</div>
      <div class="detail-chip">Risk Level: ${escapeHtml(analysis.risk_level ?? "--")}</div>
      <div class="detail-chip">Behavior Score: ${escapeHtml(analysis.behavior_analysis?.risk_score ?? "--")}/100</div>
      <div class="detail-chip">Content Score: ${escapeHtml(analysis.content_analysis?.risk_score ?? "--")}/100</div>
      <div class="detail-chip">Paste Ratio: ${escapeHtml(metrics.paste_ratio_percent ?? "--")}%</div>
      <div class="detail-chip">Words Per Minute: ${escapeHtml(metrics.words_per_minute ?? "--")}</div>
    </div>

    <h3>Top Risk Signals</h3>
    ${renderDetailList(riskRows)}

    <h3>Pasted Sections</h3>
    ${renderDetailList(pastedRows)}

    <h3>Flagged Assignment Sections</h3>
    ${renderDetailList(flaggedRows)}
  `;
}

function syncAssignmentSelection() {
  const availableIds = new Set(studentAssignments.map((assignment) => assignment.id));
  const desiredId =
    (currentAssignmentId && availableIds.has(currentAssignmentId) && currentAssignmentId)
    || (assignmentSelect.value && availableIds.has(assignmentSelect.value) && assignmentSelect.value)
    || (studentAssignments.length ? studentAssignments[0].id : "");

  if (!desiredId) {
    persistCurrentAssignmentDraft();
    currentAssignmentId = "";
    assignmentSelect.value = "";
    applyAssignmentState(createEmptyAssignmentState());
    assignmentPreview.textContent = "No assignments available yet. Ask a teacher to create one.";
    setEditorEnabled(false);
    setStatus("Waiting for an assignment before drafting.", "neutral");
    return;
  }

  if (desiredId !== currentAssignmentId) {
    persistCurrentAssignmentDraft();
    currentAssignmentId = desiredId;
  }

  assignmentSelect.value = desiredId;
  restoreDraft(desiredId);
  setEditorEnabled(true);
  renderAssignmentPreview();
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
  if (typeof lastKeyTime !== "number") {
    lastKeyTime = now;
  }

  eventLog.push({
    type: "key",
    key: event.key,
    time: now,
    gap: now - lastKeyTime
  });

  lastKeyTime = now;
}

function trackPaste(event) {
  ensureSessionStarted();
  const pastedText = (event.clipboardData || window.clipboardData).getData("text");
  const snippet = pastedText.replace(/\s+/g, " ").trim().slice(0, 220);

  eventLog.push({
    type: "paste",
    length: pastedText.length,
    words: getWordCount(pastedText.trim()),
    target_section: getCurrentSectionLabel(),
    snippet,
    time: Date.now()
  });
}

function trackInput() {
  ensureSessionStarted();
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

async function loadPublicAssignments() {
  try {
    const response = await fetch(`${API_BASE}/assignments/public`);
    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    const data = await response.json();
    studentAssignments = Array.isArray(data.assignments) ? data.assignments : [];

    assignmentSelect.innerHTML = '<option value="">Select an assignment</option>';
    studentAssignments.forEach((assignment) => {
      const option = document.createElement("option");
      option.value = assignment.id;
      option.textContent = `${assignment.title} (due ${assignment.due_date})`;
      assignmentSelect.appendChild(option);
    });

    syncAssignmentSelection();
  } catch (error) {
    console.error("Failed to load assignments:", error);
    assignmentPreview.textContent = "Could not load assignments from backend.";
  }
}

async function submitAssignment() {
  const text = getPlainText();
  const sessionEnd = Date.now();
  const assignmentId = assignmentSelect.value;
  const studentName = studentNameInput.value.trim();
  const studentId = studentIdInput.value.trim();

  if (!assignmentId) {
    setSubmitMessage("Select an assignment before submitting.", "error");
    return;
  }

  if (!studentName || !studentId) {
    setSubmitMessage("Enter your student name and ID before submitting.", "error");
    return;
  }

  if (!text) {
    setSubmitMessage("Write something before submitting.", "error");
    return;
  }

  // If the draft text exists due to a restore, but no new input happened this load,
  // fall back to counting from now so duration doesn't explode to days.
  if (typeof sessionStart !== "number") {
    ensureSessionStarted(sessionEnd);
  }

  const payload = {
    student_name: studentName,
    student_id: studentId,
    text,
    total_chars: text.length,
    total_words: getWordCount(text),
    startTime: sessionStart,
    endTime: sessionEnd,
    duration_seconds: Math.floor((sessionEnd - sessionStart) / 1000),
    events: eventLog
  };

  setSubmitMessage("Submitting to teacher dashboard...");
  setStatus("Sending submission for teacher review.");

  try {
    const response = await fetch(`${API_BASE}/assignments/${assignmentId}/submit`, {
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
    setSubmitMessage(data.message || "Submitted successfully for teacher review.", "success");
    setStatus("Submission complete. Scores are visible to teachers in their dashboard.");
    setBackendStatus("Online", "online");

    // Start a fresh evidence log for any subsequent resubmission attempt.
    // Keep the text draft, but do not carry old paste/key/edit evidence forward.
    eventLog = [];
    sessionStart = null;
    lastKeyTime = null;
    lastText = getPlainText();
    saveDraft(false, assignmentId);
  } catch (error) {
    console.error("Submission failed:", error);
    setSubmitMessage("Submission failed. Make sure the backend API is reachable.", "error");
    setStatus("Could not reach backend. Start API and try again.", "error");
    setBackendStatus("Offline", "offline");
  }
}

async function createAssignment() {
  const payload = {
    title: newAssignmentTitle.value.trim(),
    description: newAssignmentDescription.value.trim(),
    due_date: newAssignmentDueDate.value,
    max_score: Number(newAssignmentMaxScore.value || "100")
  };

  if (!payload.title || !payload.description || !payload.due_date) {
    teacherCreateStatus.textContent = "Title, description, and due date are required.";
    return;
  }

  teacherCreateStatus.textContent = "Creating assignment...";

  try {
    const response = await fetch(`${API_BASE}/teacher/assignments`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    teacherCreateStatus.textContent = "Assignment created.";
    newAssignmentTitle.value = "";
    newAssignmentDescription.value = "";
    newAssignmentDueDate.value = "";
    newAssignmentMaxScore.value = "100";
    await Promise.all([loadTeacherAssignments(), loadPublicAssignments()]);
  } catch (error) {
    console.error("Failed to create assignment:", error);
    teacherCreateStatus.textContent = "Failed to create assignment.";
  }
}

async function loadTeacherAssignments() {
  teacherAssignmentList.textContent = "Loading assignments...";

  try {
    const response = await fetch(`${API_BASE}/teacher/assignments`);
    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    const data = await response.json();
    const assignments = Array.isArray(data.assignments) ? data.assignments : [];
    renderTeacherAssignments(assignments);

    if (selectedTeacherAssignmentId) {
      await loadAssignmentSubmissions(selectedTeacherAssignmentId, false);
    }
  } catch (error) {
    console.error("Failed to load teacher assignments:", error);
    teacherAssignmentList.textContent = "Could not load assignments.";
  }
}

async function loadAssignmentSubmissions(assignmentId, clearDetail = true) {
  selectedTeacherAssignmentId = assignmentId;
  teacherSubmissionList.textContent = "Loading submissions...";

  if (clearDetail) {
    teacherSubmissionDetail.textContent = "Select a submission to view details.";
  }

  try {
    const response = await fetch(`${API_BASE}/teacher/assignments/${assignmentId}/submissions`);
    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    const data = await response.json();
    renderTeacherSubmissions(data.assignment, Array.isArray(data.submissions) ? data.submissions : []);
  } catch (error) {
    console.error("Failed to load submissions:", error);
    teacherSubmissionList.textContent = "Could not load submissions for this assignment.";
  }
}

async function loadSubmissionDetail(submissionId) {
  teacherSubmissionDetail.textContent = "Loading submission details...";

  try {
    const response = await fetch(`${API_BASE}/teacher/submissions/${submissionId}`);
    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }

    const data = await response.json();
    renderSubmissionDetail(data);
  } catch (error) {
    console.error("Failed to load submission detail:", error);
    teacherSubmissionDetail.textContent = "Could not load submission details.";
  }
}

function handleAssignmentChange() {
  persistCurrentAssignmentDraft();
  currentAssignmentId = assignmentSelect.value;

  if (!currentAssignmentId) {
    applyAssignmentState(createEmptyAssignmentState());
    assignmentPreview.textContent = "No assignment selected.";
    setEditorEnabled(false);
    setStatus("Select an assignment to start drafting.", "neutral");
    return;
  }

  restoreDraft(currentAssignmentId);
  setEditorEnabled(true);
  renderAssignmentPreview();
}

function seedEditorFormatting() {
  editor.style.fontFamily = fontFamily.value;
  editor.style.fontSize = `${fontSize.value}pt`;
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

function bindDashboardEvents() {
  studentModeButton.addEventListener("click", () => toggleMode("student"));
  teacherModeButton.addEventListener("click", () => toggleMode("teacher"));
  assignmentSelect.addEventListener("change", handleAssignmentChange);
  createAssignmentButton.addEventListener("click", createAssignment);
  refreshTeacherData.addEventListener("click", loadTeacherAssignments);
}

async function init() {
  const defaultMode = document.body.dataset.defaultMode === "teacher" ? "teacher" : "student";

  seedEditorFormatting();
  updateStats();
  updateSessionClock();
  bindToolbar();
  bindDashboardEvents();
  toggleMode(defaultMode);
  lastText = getPlainText();
  setEditorEnabled(false);

  editor.addEventListener("paste", trackPaste);
  editor.addEventListener("input", trackInput);
  editor.addEventListener("mouseup", syncToolbarState);
  editor.addEventListener("keyup", syncToolbarState);
  document.addEventListener("keydown", trackKeyboardEvent);

  setInterval(updateSessionClock, 1000);
  await checkBackendHealth();
  setInterval(checkBackendHealth, 15000);

  await loadPublicAssignments();

  window.addEventListener("beforeunload", () => saveDraft());
  setStatus("Editor ready. Submit sends data to teacher dashboard only.");
}

init();
