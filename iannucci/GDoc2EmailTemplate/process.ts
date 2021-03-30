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
 * Processes a Paragraph.
 *
 * Transforms all Paragraphs 'p' tags... even headers. However we do apply
 * styling to the paragraph according to it's selected 'heading' claim.
 */
function processParagraph_(state: emailBuilder_, el: GoogleAppsScript.Document.Paragraph) {
  if (el.getNumChildren() == 0) {
    state.pushTag("p", { [extraStyle_]: "height:1em" })
    state.popTag(true)
    return
  }

  state.pushTag("p", state.headingStyles.get(el.getHeading()), el.getAttributes())
  if (state.curStartIndent != 0) {
    throw `Unexpected: curStartIndent == ${state.curStartIndent} (should be 0)`
  }
  state.curStartIndent = el.getIndentStart()
  processChildElements_(state, el)
  state.popTag()
  state.curStartIndent = 0
}

let listItemUl_ = new Set([
  DocumentApp.GlyphType.BULLET,
  DocumentApp.GlyphType.HOLLOW_BULLET,
  DocumentApp.GlyphType.SQUARE_BULLET,
])

/**
 * Gdocs stores all list items as adjacent elements, regardless
 * of indentation level. It turns out this format is really useful
 * when interspersing template script blocks with bullet items.
 *
 * To this end, we emit slightly goofy HTML here where each list
 * item is wrapped in N-1 levels of <ol><li> with a style applied
 * to hide their number/bullet.
 *
 * The end result LOOKS like a normally nested list, but it's much
 * easier to deal with in the context of a template because you
 * don't have to worry about "which level of the list did the user
 * mean to have this template block at?"
 */
function processListItems_(state: emailBuilder_, el: GoogleAppsScript.Document.ListItem) {
  let trimmedAttrs = { ...el.getAttributes() }
  trimmedAttrs[DocumentApp.Attribute.INDENT_FIRST_LINE] = null
  trimmedAttrs[DocumentApp.Attribute.INDENT_START] = null
  let listKind = listItemUl_.has(el.getGlyphType()) ? "ul" : "ol"
  let value = listKind == 'ol' ? state.nextListValue(
    `${el.getListId()}.${el.getNestingLevel()}`) : 0

  for (let i = 0; i < el.getNestingLevel() + 1; i++) {
    state.pushTag(listKind, trimmedAttrs)
    if (i < el.getNestingLevel()) {
      state.pushTag('li class="x"')
    } else {
      state.pushTag(value ? `li value='${value}'` : 'li')
    }
  }
  processChildElements_(state, el)
  for (let i = 0; i < el.getNestingLevel() + 1; i++) {
    state.popTag()
    state.popTag()
  }
}

/**
 * This one's pretty tricky, so watch out.
 */
function processHorizontalRule_(state: emailBuilder_, el: GoogleAppsScript.Document.HorizontalRule) {
  state.pushTag("hr/")
}

/**
 * Inline images in email turn out to be pretty easy:
 *   1) Refer to the image by cid:<arbitrary>
 *   2) Provide the blob to the mail api with the key of <arbitrary>
 */
function processInlineImage_(state: emailBuilder_, el: GoogleAppsScript.Document.InlineImage) {
  let bits = [`img src="cid:${state.addImage(el)}"`]
  if (el.getAltDescription()) {
    bits.push(` alt="${escapeHTML_(el.getAltDescription())}"`)
  }
  if (el.getWidth()) {
    bits.push(` width="${el.getWidth()}"`)
  }
  if (el.getHeight()) {
    bits.push(` height="${el.getHeight()}"`)
  }
  bits.push('/')
  state.pushTag(bits.join(''))
}

/**
 * We emit the table here as normal, but note that getParsedDoc does some
 * swizzling to tables:
 *   * Move script blocks into an adjacent table
 *   * Combine adjacent tables together after moving script blocks.
 */
function processTable_(state: emailBuilder_, el: GoogleAppsScript.Document.Table) {
  let tableAttrs = el.getAttributes()
  state.pushTag("table", tableAttrs)
  for (let rowIdx = 0; rowIdx < el.getNumRows(); rowIdx++) {
    let row = el.getRow(rowIdx)
    state.pushTag("tr", tableAttrs, row.getAttributes())
    for (let colIdx = 0; colIdx < row.getNumCells(); colIdx++) {
      let col = row.getCell(colIdx)
      state.pushTag("td", tableAttrs, col.getAttributes())
      processChildElements_(state, col)
      state.popTag()
    }
    state.popTag(true)
  }
  state.popTag()
}

/**
 * Processes Text, and any possible styling applied to it.
 *
 * Transforms a Text into one or more `span` elements.
 *
 * Note that most of the work here is done by emailBuilder_.pushText.
 */
function processText_(state: emailBuilder_, el: GoogleAppsScript.Document.Text) {
  let text = el.getText()
  let idxAttrs = el.getTextAttributeIndices().map(idx => ({
    start: idx,
    end: text.length,
    attrs: el.getAttributes(idx)
  }))
  for (let i = 1; i < idxAttrs.length; i++) {
    idxAttrs[i - 1].end = idxAttrs[i].start
  }

  for (let { start, end, attrs } of idxAttrs) {
    if (attrs[DocumentApp.Attribute.LINK_URL]) {
      state.pushTag(`a href="${attrs[DocumentApp.Attribute.LINK_URL]}"`, attrs)
    } else {
      state.pushTag("?span", attrs)
    }
    state.pushText(text.slice(start, end))
    state.popTag()
  }
}

/**
 * _procFnMapping maps from DocumentApp.ElementType to a processing function.
 *
 * If processing some element is not supported, it has no function here (i.e. lookup
 * will return undefined)
 */
let procFnMapping_ = new Map<GoogleAppsScript.Document.ElementType, unknown>([
  [DocumentApp.ElementType.BODY_SECTION, processChildElements_],
  [DocumentApp.ElementType.HORIZONTAL_RULE, processHorizontalRule_],
  [DocumentApp.ElementType.INLINE_IMAGE, processInlineImage_],
  [DocumentApp.ElementType.LIST_ITEM, processListItems_],
  [DocumentApp.ElementType.PARAGRAPH, processParagraph_],
  [DocumentApp.ElementType.TEXT, processText_],
  [DocumentApp.ElementType.TABLE, processTable_],
])

// Unsupported:
//
// TableOfContents
// Equation
// EquationFunction
// EquationFunctionArgumentSeparator
// EquationSymbol
// HeaderSection
// FooterSection
// PageBreak
// Footnote
// FootnoteSection

type elementProcessor_<T extends GoogleAppsScript.Document.Element> = (state: emailBuilder_, el: T) => number

interface containerElement {
  getNumChildren: () => number
  getChild: (idx: number) => GoogleAppsScript.Document.Element
}

function processChildElements_(state: emailBuilder_, el: containerElement) {
  let numChildren = el.getNumChildren()
  for (let i = 0; i < numChildren; i++) {
    let child = el.getChild(i)
    let ct = child.getType()
    let fn = procFnMapping_.get(ct)

    if (fn) {
      (fn as elementProcessor_<typeof child>)(state, child)
    } else {
      Logger.log(`Skipping element: ${ct}`)
    }
  }
}
