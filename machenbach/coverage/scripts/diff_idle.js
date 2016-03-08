if (!document.URL.match(/.*\/diff2?\//)) {
  throw new Error('Incorrect match config');
}

// The coverage data will be fetched asynchroneously.
var uncoveredLines = null;
var coveredLines = null;

var newCodeMarker = 'newcode';
var bucket = 'https://storage.googleapis.com/chromium-v8'


// The file name that's diffed.
var file = document.URL.match(/.*\/\d+\/diff2?\/\d+:?\d*\/(.*)/)[1]


/**
 * Adds a SPAN with coverage data to a line. Expects a node representing the
 * TR that pairs the old/new line TDs.
 *
 * @private
 */
function addCoverageLineData(node) {
  if (!uncoveredLines || !coveredLines) {
    // Bail out if we don't have coverage data.
    return;
  }
  if (!node ||
      !node.id ||
      node.tagName != 'TR' ||
      !node.id.startsWith('pair-')) {
    // Ignore any other nodes, e.g. headers.
    return;
  }
  for (var childIndex = 0; childIndex < node.children.length; childIndex++) {
    var newCodeNode = node.children[childIndex];
    if (!newCodeNode.id ||
        !newCodeNode.id.startsWith(newCodeMarker) ||
        newCodeNode.tagName != 'TD') {
      // We only care for the new code on the right side.
      continue;
    }

    // The number after 'newcode' is the line number.
    var lineNumber = parseInt(newCodeNode.id.substring(newCodeMarker.length));

    // Add a border on the left.
    newCodeNode.style.borderStyle = "none none none solid";

    // Color the border dependent on coverage.
    if (uncoveredLines.has(lineNumber)) {
      newCodeNode.style.borderColor = "red";
    } else if (coveredLines.has(lineNumber)) {
      newCodeNode.style.borderColor = "green";
    } else {
      newCodeNode.style.borderColor = "white";
    }
  }
}


/**
 * Adds coverage data to all new-code lines.
 *
 * @private
 */
function addCoverageFileData() {
  var codeTable = document.getElementById('thecode');
  var nodes = codeTable.childNodes[1].childNodes;
  for (var childIndex = 0; childIndex < nodes.length; childIndex++) {
    var node = nodes[childIndex];
    addCoverageLineData(node);
  }
}


var xhr = new XMLHttpRequest();
// TODO(machenbach): Switch from experimental data to actual coverage data per
// issue/patchset.
xhr.open('GET', bucket + '/experimental/coverage/cover.json', true);
xhr.onload = function (e) {
  if (xhr.readyState === 4) {
    if (xhr.status === 200) {
      // TODO(machenbach): Save each file in a separate json data file.
      var coverage = JSON.parse(xhr.responseText)['files'][file];
      if (!coverage) {
        console.log('No coverage data for ' + file);
        return;
      }
      console.log('Found coverage data for ' + file);

      coveredLines = new Set([]);
      uncoveredLines = new Set([]);
      for (lineIndex = 0; lineIndex < coverage.length; lineIndex++) {
        if (coverage[lineIndex][1]) {
          coveredLines.add(coverage[lineIndex][0]);
        } else {
          uncoveredLines.add(coverage[lineIndex][0]);
        }
      }

      // Update the page.
      addCoverageFileData();
    } else {
      console.log(xhr.statusText);
    }
  }
};

xhr.onerror = function (e) {
  console.log(xhr.statusText);
};
xhr.send(null);

/**
 * Callback for inserted nodes. E.g. the 'expand' button adds more TR nodes.
 *
 * @private
 */
function nodeInsertedCallback(event) {
  addCoverageLineData(event.relatedNode);
};
document.addEventListener('DOMNodeInserted', nodeInsertedCallback);