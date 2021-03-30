// Copyright 2021 The LUCI Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * Installs a "GDoc2EmailTemplate" menu in the current google doc.
 *
 * Can be used to preview what the current doc will look like as an
 * email, usually called from your doc's script `onOpen` handler.
 *
 * Example (in your doc's script editor):
 *   function onOpen(e) {
 *     GDoc2EmailTemplate.InstallDocumentAppPreviews()
 *   }
 *
 * Must be called with an active Document.
 */
function InstallDocumentAppPreviews() {
  DocumentApp.getUi().createMenu("GDoc2EmailTemplate").
    addItem("Preview", "GDoc2EmailTemplate.PreviewCurrentDoc").
    addItem("Preview raw", "GDoc2EmailTemplate.PreviewCurrentDocRaw").
    addItem("Preview raw (ugly)", "GDoc2EmailTemplate.PreviewCurrentDocRawUgly").
    addItem("Debug buffer", "GDoc2EmailTemplate.PreviewDebugBuffer").
    addItem("Debug swizzled buffer", "GDoc2EmailTemplate.PreviewDebugSwizzledBuffer").
    addToUi()
}

/**
 * Shows the current doc rendered as a templatized HTML email in
 * a modal dialog.
 *
 * Must be called with an active Document.
 */
function PreviewCurrentDoc() {
  let args = ParseDoc(DocumentApp.getActiveDocument())
  DocumentApp.getUi().showModalDialog(
    HtmlService.createHtmlOutput(args.bodyWithTemplatesAsCode(false, true)).setWidth(890).setHeight(500),
    args.subject.evaluate().getContent(),
  );
}

function previewCurrentDocRaw_(stopStep?: string) {
  let doc = DocumentApp.getActiveDocument()
  let content = function(): string {
    let state = new emailBuilder_(doc, true)
    let getDebugAttrs = function(obj: Object): string {
      if (obj.hasOwnProperty('debugAttrs')) {
        return JSON.stringify((obj as debugAttrs).debugAttrs())
      }
      return ''
    }

    state.pushTag("body")
    processChildElements_(state, doc.getBody())
    state.popTag()

    if (stopStep == "buffer") {
      return state.buffer.map(
        itm => `[${itm}] ${getDebugAttrs(itm)}`
      ).join('\n')
    }

    let parsed = state.getParsedDoc()  // swizzles buffer as side effect

    if (stopStep == "swizzle") {
      return state.buffer.map(
        itm => `[${itm}] ${getDebugAttrs(itm)}`
      ).join('\n')
    }

    if (stopStep == "raw") {
      return parsed.body.getRawContent()
    }

    return parsed.bodyWithTemplatesAsCode(true)
  }()

  let body = HtmlService.createHtmlOutput(
    `<html><body><pre>${escapeHTML_(content)}</pre></body></html>`
  )

  DocumentApp.getUi().showModalDialog(
    HtmlService.createHtmlOutput(body).setWidth(890).setHeight(500),
    doc.getName(),
  );
}

/**
 * Shows the raw, formatted, HTML source for the current doc, as would
 * be shown by PreviewCurrentDoc. Formatted as an HTML document with the
 * raw source in a `<pre>` tag.
 *
 * Must be called with an active Document.
 */
function PreviewCurrentDocRaw() { return previewCurrentDocRaw_() }

/**
 * Shows the raw templated HTML source for the current doc, as would
 * be directly returned from ParseDoc.
 * Formatted as an HTML document with the raw source in a <pre> tag.
 *
 * Must be called with an active Document.
 */
function PreviewCurrentDocRawUgly() { return previewCurrentDocRaw_("raw") }

function PreviewDebugBuffer() {return previewCurrentDocRaw_("buffer") }

function PreviewDebugSwizzledBuffer() {return previewCurrentDocRaw_("swizzle") }

/**
 * ParseDoc parses the given Document into a GMail compatible HTML email.
 *
 * Template Processing
 *
 * By default, this will look for `template` directives in the doc,
 * indicated by <?...?>, per Apps Script `HtmlService.createTemplate`.
 * These sections will be preserved in the output verbatim, with the
 * following adjustments:
 *   * If a non-printing scriptlet is adjacent to a table, the scriptlet
 *     will be pulled into that table. This allows you to surround a table
 *     with scriptlets, and have those scriptlets apply directly to the
 *     table row, rather than the entire table.
 *   * If moving a scriptlet due to the table-adjacency rule would cause
 *     a close-tag to become adjacent to a matching open-tag, remove both
 *     the close and open tags to create a continuous table. This allows
 *     you to put a header and/or footer row on a table.
 *
 * Note that the HTML emitted here uses a rather terrible representation
 * of lists; Instead of a normally nested list, this renders each
 * individual list item as it's own stack of <ul|ol><li> tags with CSS
 * applied to prevent the accumulation of unwanted bullets/numbers.
 * However this does mean that script blocks surrounding sub-sections
 * of a list will do exactly what you expect them to do.
 *
 * Example:
 *     | some | table | header |
 *     <? for (let itm of whatever) { ?>
 *     | some | table | contents <?= itm ?> |
 *     <? } ?>
 *     | some | table | footer |
 *
 * Would create a single set of `table` tags with the for loop
 * surrounding the center row of cells.
 *
 * Limitations
 *
 * This does its best to preserve all style and formatting information
 * available in the DocumentApp API. However, this API only contains a
 * small subset of the styling options available in GDocs, and so it's
 * possible to do things in GDocs which this parser simply cannot see.
 *
 * Additionally, this parser does not support several Document Elements
 * which seem ill-suited to email (like a table of contents) or very
 * difficult to translate (e.g. equations would have to be rendered to
 * an inline image... I'm not sure how one would even go about doing this
 * from Apps Script). The list of unsupported elements is:
 *   * TableOfContents
 *   * Equation
 *   * EquationFunction
 *   * EquationFunctionArgumentSeparator
 *   * EquationSymbol
 *   * HeaderSection
 *   * FooterSection
 *   * PageBreak
 *   * Footnote
 *   * FootnoteSection
 *
 * @param {DocumentApp.Document} doc  The document to parse.
 * @param {boolean} templateMode      If true (default), this will
 *   preserve sections of the doc surrounded by <?...?> verbatim,
 *   stripping any errant style directives, for use with Apps Script
 *   `HtmlService.createTemplate`. If false, such spans will be HTML
 *   escaped. If your doc doesn't contain template directives, pass
 *   false to avoid accidental identification of such elements.
 * @return {ParsedDoc}
 */
function ParseDoc(doc: GoogleAppsScript.Document.Document, templateMode: boolean = true): ParsedDoc {
  let state = new emailBuilder_(doc, templateMode)

  state.pushTag("body")
  processChildElements_(state, doc.getBody())
  state.popTag()

  return state.getParsedDoc()
}
