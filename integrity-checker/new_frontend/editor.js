/* =============================
   WRITE TRACE — BEHAVIOR TRACKING
   ============================= */

/* ---------- MODULE SETUP ---------- */

const BetterTableModule =
  (window.QuillBetterTable && window.QuillBetterTable.default) ||
  window.QuillBetterTable ||
  null;

if (BetterTableModule) {
  Quill.register({ "modules/better-table": BetterTableModule }, true);
}

const Parchment = Quill.import("parchment");

/* Line spacing support */
const LineHeightStyle = new Parchment.Attributor.Style(
  "lineheight",
  "line-height",
  {
    scope: Parchment.Scope.BLOCK,
    whitelist: ["1", "1.5", "2"]
  }
);

Quill.register(LineHeightStyle, true);

/* ---------- EDITOR INIT ---------- */

const modules = { toolbar: "#toolbar" };

if (BetterTableModule) {
  modules["better-table"] = {
    operationMenu: {
      items: { unmergeCells: { text: "Unmerge" } }
    }
  };
  modules.keyboard = {
    bindings: BetterTableModule.keyboardBindings
  };
}

const quill = new Quill("#editor", {
  theme: "snow",
  modules
});

/* =============================
   BEHAVIOR TRACKING ENGINE
   ============================= */

const behaviorLog = [];

let sessionStart = Date.now();
let lastKeyTime = Date.now();
let lastLength = 0;

/* ---------- WORD COUNT ---------- */

function updateWordCount() {
  const text = quill.getText().trim();
  const words = text.length ? text.split(/\s+/).length : 0;
  document.getElementById("wordCount").innerText = "Words: " + words;
}

quill.on("text-change", updateWordCount);
updateWordCount();

/* ---------- TRACK TYPING ---------- */

document.addEventListener("keydown", (e) => {
  const now = Date.now();

  behaviorLog.push({
    type: "key",
    key: e.key,
    time: now,
    gap: now - lastKeyTime
  });

  lastKeyTime = now;
});

/* ---------- TRACK PASTE ---------- */

quill.root.addEventListener("paste", (e) => {
  const pastedText =
    (e.clipboardData || window.clipboardData).getData("text");

  behaviorLog.push({
    type: "paste",
    length: pastedText.length,
    words: pastedText.trim().split(/\s+/).length,
    time: Date.now()
  });
});

/* ---------- TRACK EDIT BURSTS ---------- */

quill.on("text-change", (delta, oldDelta, source) => {
  const currentLength = quill.getLength();

  behaviorLog.push({
    type: "edit",
    delta: currentLength - lastLength,
    totalLength: currentLength,
    time: Date.now()
  });

  lastLength = currentLength;

  /* detect large insert */
  if (delta.ops) {
    delta.ops.forEach(op => {
      if (op.insert && typeof op.insert === "string" && op.insert.length > 50) {
        behaviorLog.push({
          type: "large_insert",
          length: op.insert.length,
          time: Date.now()
        });
      }
    });
  }
});

/* =============================
   TABLE INSERTION
   ============================= */

document.getElementById("insert-table").onclick = () => {
  const tableModule = quill.getModule("better-table");

  if (tableModule) {
    tableModule.insertTable(3, 3);
  } else {
    alert("Table module not loaded");
  }
};

/* =============================
   LINE SPACING
   ============================= */

document.getElementById("line-spacing").addEventListener("change", function () {
  const spacing = this.value;
  const range = quill.getSelection(true);

  if (range) {
    quill.formatLine(range.index, range.length, {
      lineheight: spacing
    });
  }
});

/* =============================
   EXPORT PDF
   ============================= */

document.getElementById("exportPDF").onclick = () => {
  const content = document.querySelector(".ql-editor");

  const opt = {
    margin: 0.5,
    filename: "assignment.pdf",
    image: { type: "jpeg", quality: 1 },
    html2canvas: { scale: 2 },
    jsPDF: { unit: "in", format: "a4", orientation: "portrait" }
  };

  html2pdf().set(opt).from(content).save();
};

/* =============================
   SUBMIT WITH TRACKING DATA
   ============================= */

function submitAssignment() {
  const sessionEnd = Date.now();

  const payload = {
    text: quill.getText(),
    total_chars: quill.getText().length,
    total_words: quill.getText().trim().split(/\s+/).length,

    startTime: sessionStart,
    endTime: sessionEnd,
    duration_seconds: Math.floor((sessionEnd - sessionStart) / 1000),

    events: behaviorLog
  };

  console.log("Submission Payload:");
  console.log(payload);

  fetch("http://127.0.0.1:8000/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
    .then(res => res.json())
    .then(data => {
      alert("Integrity Risk Score: " + data.risk);
      console.log("Server Response:", data);
    })
    .catch(err => {
      console.error("Submission failed:", err);
      alert("Submission failed (backend not running?)");
    });
}

/* expose button usage */
window.submitAssignment = submitAssignment;