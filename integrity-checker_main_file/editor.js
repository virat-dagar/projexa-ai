// register optional modules safely so editor still initializes if a plugin fails to load
const ImageResizeModule =
  (window.ImageResize && window.ImageResize.default) || window.ImageResize || null;
if (ImageResizeModule) {
  Quill.register('modules/imageResize', ImageResizeModule);
}
if (window.QuillBetterTable) {
  Quill.register({ 'modules/better-table': window.QuillBetterTable }, true);
}
const Parchment = Quill.import('parchment');
const LineHeightStyle = new Parchment.Attributor.Style(
  'lineheight',
  'line-height',
  { scope: Parchment.Scope.BLOCK, whitelist: ['1', '1.5', '2'] }
);
Quill.register(LineHeightStyle, true);

const modules = {
  toolbar: '#toolbar'
};

if (ImageResizeModule) {
  modules.imageResize = {
    parchment: Quill.import('parchment'),
    modules: ['Resize', 'DisplaySize', 'Toolbar']
  };
}

if (window.QuillBetterTable) {
  modules.table = false;
  modules['better-table'] = {
    operationMenu: {
      items: {
        unmergeCells: { text: 'Unmerge' }
      }
    }
  };
  modules.keyboard = {
    bindings: window.QuillBetterTable.keyboardBindings
  };
}

const quill = new Quill('#editor', {
  theme: 'snow',
  modules
});

// insert table button action
document.getElementById("insert-table").onclick = () => {
  const tableModule = quill.getModule('better-table');
  if (tableModule) {
    tableModule.insertTable(3, 3);
  } else {
    alert("Table module did not load. Hard refresh and try again.");
  }
};

// word counter
function updateWordCount() {
  const text = quill.getText().trim();
  const words = text.length ? text.split(/\s+/).length : 0;
  document.getElementById('wordCount').innerText = "Words: " + words;
}

quill.on('text-change', updateWordCount);
updateWordCount();

document.getElementById("line-spacing").addEventListener("change", function() {
  const spacing = this.value;
  const range = quill.getSelection(true);

  if (range) {
    quill.formatLine(range.index, range.length, {
      lineheight: spacing
    });
  }
});

document.getElementById("exportPDF").onclick = () => {
  const content = document.querySelector(".ql-editor");
  if (!content) {
    alert("Editor content not found.");
    return;
  }
  if (typeof html2pdf === "undefined") {
    window.print();
    return;
  }

  const opt = {
    margin: 0.5,
    filename: 'assignment.pdf',
    image: { type: 'jpeg', quality: 1 },
    html2canvas: { scale: 2, useCORS: true, allowTaint: true },
    jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' }
  };

  html2pdf()
    .set(opt)
    .from(content)
    .save()
    .catch(() => {
      window.print();
    });
};
