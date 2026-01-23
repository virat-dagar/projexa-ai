const editor = document.getElementById("editor");

let events = [];
let startTime = Date.now();
let lastKeyTime = Date.now();
let lastLength = 0;

// Utility: word count
function getWordCount(text) {
  return text.trim().split(/\s+/).filter(w => w.length > 0).length;
}

// Track typing
editor.addEventListener("keydown", (e) => {
  const now = Date.now();

  events.push({
    type: "key",
    key: e.key,
    time: now,
    gap: now - lastKeyTime
  });

  lastKeyTime = now;
});

// Track paste
editor.addEventListener("paste", (e) => {
  const pasteData = (e.clipboardData || window.clipboardData).getData("text");

  events.push({
    type: "paste",
    length: pasteData.length,
    words: getWordCount(pasteData),
    time: Date.now()
  });
});

// Track edits
editor.addEventListener("input", () => {
  const currentLength = editor.value.length;
  const delta = currentLength - lastLength;

  events.push({
    type: "edit",
    length: currentLength,
    delta: delta,
    words: getWordCount(editor.value),
    time: Date.now()
  });

  // Detect sudden big insertion (possible AI or bulk paste)
  if (delta > 200) {
    events.push({
      type: "sudden_insert",
      length: delta,
      time: Date.now()
    });
  }

  lastLength = currentLength;
});

// Submit
function submitAssignment() {
  const endTime = Date.now();

  const payload = {
    text: editor.value,
    total_chars: editor.value.length,
    total_words: getWordCount(editor.value),
    startTime: startTime,
    endTime: endTime,
    duration_seconds: Math.floor((endTime - startTime) / 1000),
    events: events
  };

  console.log("Submitting:", payload);

  fetch("http://127.0.0.1:8000/submit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  })
    .then(res => res.json())
    .then(data => {
      console.log("Server response:", data);

      const reportDiv = document.getElementById("report");

      let html = `<b>Risk Score:</b> ${data.risk} / 100<br><br>`;
      html += `<b>Reasons:</b><ul>`;

      data.reasons.forEach(r => {
        html += `<li>${r}</li>`;
      });

      html += `</ul><br><b>Features:</b><pre>${JSON.stringify(data.features, null, 2)}</pre>`;

      reportDiv.innerHTML = html;
    })
    .catch(err => {
      console.error("Submission failed:", err);
      alert("Submission failed. Check console.");
    });
}