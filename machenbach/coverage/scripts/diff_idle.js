if (!document.URL.match(/.*\/diff2?\//)) {
  throw new Error('Incorrect match config');
}

// The coverage data will be fetched asynchroneously.
var uncoveredLines = null;
var coveredLines = null;

var newCodeMarker = 'newcode';

var match = document.URL.match(/.*\/(\d+)\/diff2?\/(?:\d+:)?(\d+)\/(.*)/);

// Rietveld issue and patchset number.
var issue = match[1];
var patchset = match[2];

// The file name that's diffed.
var file = match[3];

// Pretty string to refer to in log files.
var loggingDataStr = file + ', issue ' + issue + ', patchset ' + patchset;

// URL to coverage data.
// TODO(machenbach): Support multiple ports/platforms. Currently hardcoded to
// linux64.
var bucket = 'https://storage.googleapis.com/chromium-v8';
var urlPrefix = (bucket + '/tryserver/sanitizer_coverage/' + issue + '/' +
                 patchset + '/linux64/');
var fullCoverageDataURL = (urlPrefix + 'data.json');
var fileCoverageDataURL = (urlPrefix + file + '.json');

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


/**
 * Callback for inserted nodes. E.g. the 'expand' button adds more TR nodes.
 *
 * @private
 */
function nodeInsertedCallback(event) {
  addCoverageLineData(event.relatedNode);
};
document.addEventListener('DOMNodeInserted', nodeInsertedCallback);


/**
 * Attempts to fall back to deprecated full coverage download if specified.
 *
 * @private
 */
function downloadFallbackCoverageData(fallbackUrl) {
  if (fallbackUrl) {
    console.log('Try downloading deprecated fallback data for ' +
                loggingDataStr);
    downloadCoverageData(fallbackUrl);
  } else {
    console.log('No coverage data for ' + loggingDataStr);
  }
}


/**
 * Download coverage data and add it to the UI if successful.
 *
 * Falls back to use the deprecated fallbackUrl on error which calls this
 * function again without fallback. This is used to stay in sync with the old
 * coverage format that didn't upload data for single files.
 * TODO(machenbach): Remove the fallback once V8 is passed CP 34834 + 1000 +
 * fudge factor (as people might want to look at old CLs).
 *
 * @private
 */
function downloadCoverageData(dataUrl, fallbackUrl) {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', dataUrl, true);
  xhr.onload = function (e) {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        // TODO(machenbach): Save each file in a separate json data file.
        var coverage = JSON.parse(xhr.responseText)['files'][file];
        if (!coverage) {
          downloadFallbackCoverageData(fallbackUrl);
          return;
        }
        console.log('Found coverage data for ' + loggingDataStr);

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
        downloadFallbackCoverageData(fallbackUrl);
      }
    }
  };

  xhr.onerror = function (e) {
    console.log(xhr.statusText);
    downloadFallbackCoverageData(fallbackUrl);
  };

  xhr.send(null);
}

// Download coverage data. First try file-based coverage data and fall back to
// full coverage data if it doesn't exist.
downloadCoverageData(fileCoverageDataURL, fullCoverageDataURL);