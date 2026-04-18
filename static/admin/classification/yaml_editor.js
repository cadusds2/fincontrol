(function () {
  "use strict";

  function getLineStart(value, position) {
    return value.lastIndexOf("\n", position - 1) + 1;
  }

  function getLineEnd(value, position) {
    var end = value.indexOf("\n", position);
    return end === -1 ? value.length : end;
  }

  function indentSelection(textarea) {
    var value = textarea.value;
    var start = textarea.selectionStart;
    var end = textarea.selectionEnd;
    var lineStart = getLineStart(value, start);
    var lineEnd = getLineEnd(value, end);
    var before = value.slice(0, lineStart);
    var selected = value.slice(lineStart, lineEnd);
    var after = value.slice(lineEnd);
    var indented = selected
      .split("\n")
      .map(function (line) {
        return "  " + line;
      })
      .join("\n");

    textarea.value = before + indented + after;
    textarea.selectionStart = start + 2;
    textarea.selectionEnd = end + (indented.length - selected.length);
  }

  function outdentSelection(textarea) {
    var value = textarea.value;
    var start = textarea.selectionStart;
    var end = textarea.selectionEnd;
    var lineStart = getLineStart(value, start);
    var lineEnd = getLineEnd(value, end);
    var before = value.slice(0, lineStart);
    var selected = value.slice(lineStart, lineEnd);
    var after = value.slice(lineEnd);
    var removedBeforeStart = 0;
    var removedTotal = 0;
    var cursorLineIndex = value.slice(lineStart, start).split("\n").length - 1;
    var lines = selected.split("\n");
    var outdented = lines
      .map(function (line, index) {
        var removed = 0;
        if (line.indexOf("  ") === 0) {
          removed = 2;
        } else if (line.indexOf(" ") === 0) {
          removed = 1;
        }
        if (index < cursorLineIndex || (index === cursorLineIndex && start > lineStart)) {
          removedBeforeStart += removed;
        }
        removedTotal += removed;
        return line.slice(removed);
      })
      .join("\n");

    textarea.value = before + outdented + after;
    textarea.selectionStart = Math.max(lineStart, start - removedBeforeStart);
    textarea.selectionEnd = Math.max(textarea.selectionStart, end - removedTotal);
  }

  function insertAtCursor(textarea, text) {
    var start = textarea.selectionStart;
    var end = textarea.selectionEnd;
    textarea.value = textarea.value.slice(0, start) + text + textarea.value.slice(end);
    textarea.selectionStart = textarea.selectionEnd = start + text.length;
  }

  function updateCounter(textarea, counter) {
    var value = textarea.value || "";
    var lines = value.length ? value.split("\n").length : 0;
    counter.textContent = lines + " linha(s), " + value.length + " caractere(s)";
  }

  function enhanceYamlEditor(textarea) {
    if (!textarea || textarea.dataset.yamlEditorEnhanced === "1") {
      return;
    }
    textarea.dataset.yamlEditorEnhanced = "1";
    textarea.classList.add("yaml-editor-enhanced");

    var help = document.createElement("div");
    help.className = "yaml-editor-help";
    help.innerHTML = "Atalhos: <code>Tab</code> indenta, <code>Shift+Tab</code> remove indentacao, <code>Ctrl+Enter</code> salva.";

    var counter = document.createElement("div");
    counter.className = "yaml-editor-counter";

    textarea.insertAdjacentElement("afterend", counter);
    textarea.insertAdjacentElement("afterend", help);
    updateCounter(textarea, counter);

    textarea.addEventListener("keydown", function (event) {
      if (event.key === "Tab") {
        event.preventDefault();
        if (textarea.selectionStart === textarea.selectionEnd) {
          if (event.shiftKey) {
            outdentSelection(textarea);
          } else {
            insertAtCursor(textarea, "  ");
          }
        } else if (event.shiftKey) {
          outdentSelection(textarea);
        } else {
          indentSelection(textarea);
        }
        updateCounter(textarea, counter);
      }

      if (event.key === "Enter" && event.ctrlKey) {
        event.preventDefault();
        if (textarea.form) {
          textarea.form.requestSubmit();
        }
      }
    });

    textarea.addEventListener("input", function () {
      updateCounter(textarea, counter);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    enhanceYamlEditor(document.getElementById("id_yaml_content"));
  });
})();
