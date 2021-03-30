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

class styleBuilder_ {
  items: string[] = []

  /**
   * Adds a CSS item in the form of
   *
   *    "tag:piece piece piece;"
   *
   * To this style builder.
   */
  addTag(tag: string, ...pieces: (string|undefined)[]) {
    pieces = pieces.filter(itm => itm)
    if (pieces.length == 0) {
      return
    }
    this.items.push(`${tag}:${pieces.join(" ")}`)
  }

  dump(): string {
    if (this.items.length == 0) {
      return ''
    }
    return this.items.join(";")
  }
}

function withAttr_(obj: any, attr: GoogleAppsScript.Document.Attribute, cb: (value: any) => void) {
  let value = obj[attr]
  if (value === undefined) {
    return false
  }
  cb(value)
  return true
}

let DA_ = DocumentApp.Attribute

/**
 * Processes "border" CSS property.
 */
function addBorderStyle_(style: styleBuilder_, el: any) {
  let pieces = []
  withAttr_(el, DA_.BORDER_WIDTH, width => pieces.push(`${width}pt`))
  if (pieces.length > 0) {
    pieces.push('solid')
  }
  withAttr_(el, DA_.BORDER_COLOR, color => pieces.push(color))
  style.addTag('border', ...pieces)
}

// maps known fonts to backup fonts. 'sans-serif' backups
// omitted as that's the default fallback.
let backupFontClassMapping_ = new Map([
  ["Consolas", "monospace"],
  ["Comic Sans MS", "fantasy,sans-serif"],

  ["Times New Roman", "serif"],
  ["Georgia", "serif"],
  ["Garamond", "serif"],
  ["Courier New", "monospace"],
  ["Brush Script MT", "cursive"],
])

/**
 * Processes "color", "background", "direction", "text-decoration" and
 * "font" CSS properties.
 */
function addRichTextStyle_(style: styleBuilder_, el: any) {
  withAttr_(el, DA_.FOREGROUND_COLOR, color => color != "#000000" ? style.addTag("color", color) : null)
  withAttr_(el, DA_.BACKGROUND_COLOR, color => color != "#FFFFFF" ? style.addTag("background", color): null)
  withAttr_(el, DA_.LEFT_TO_RIGHT, ltr => !ltr ? style.addTag("direction", "rtl") : null)

  let textDecoPieces: string[] = []
  withAttr_(el, DA_.UNDERLINE, ul => ul ? textDecoPieces.push("underline") : null)
  withAttr_(el, DA_.STRIKETHROUGH, st => st ? textDecoPieces.push("line-through") : null)
  style.addTag("text-decoration", ...textDecoPieces)

  let fontPieces = []
  withAttr_(el, DA_.ITALIC, it => it ? fontPieces.push("italic") : null)
  withAttr_(el, DA_.BOLD, b => b ? fontPieces.push("bold") : null)

  let fontSize = el[DA_.FONT_SIZE]
  let lineSpacing = el[DA_.LINE_SPACING]
  if (fontPieces.length > 0 || fontSize || lineSpacing) {
    let fontSizeAtom = fontSize ? `${fontSize}pt` : "1em"
    if (lineSpacing) {
      fontSizeAtom += `/${lineSpacing}`
    }
    fontPieces.push(fontSizeAtom)
  }

  let fontFamily = el[DA_.FONT_FAMILY]
  if (fontFamily) {
    if (fontPieces.length == 0) {
      fontPieces.push("1em")  // need a size
    }
    let backup = backupFontClassMapping_.get(fontFamily) ?? "sans-serif"
    if (fontFamily.includes(" ")) {
      fontPieces.push(`"${fontFamily}",${backup}`)
    } else {
      fontPieces.push(`${fontFamily},${backup}`)
    }
  } else if (fontPieces.length > 0) {
    // font family is required for the rest of the `font` tag to work, so
    // if other bits were set, set a font family, too.
    fontPieces.push("sans-serif")
  }
  style.addTag("font", ...fontPieces)
}

function addBoxStyle_(style: styleBuilder_, tag: string,
                      top: number, right: number, bot: number, left: number) {
  top = top ?? 0
  right = right ?? 0
  bot = bot ?? 0
  left = left ?? 0

  if ([bot, left, right, top].every(value => value === 0)) {
    return
  }

  let p = (value: number) => (value ? `${value}pt` : '0')

  // tag: all
  // tag: top+bot left+right
  // tag: top left+right bot
  // tag: top right bot left
  if ([right, bot, left].every(value => value === top)) {
    style.addTag(tag, p(top))
  } else if (top == bot && left == right) {
    style.addTag(tag, p(top), p(right))
  } else if (left == right) {
    style.addTag(tag, p(top), p(right), p(bot))
  } else {
    style.addTag(tag, p(top), p(right), p(bot), p(left))
  }
}

/**
 * Processes "padding" and "min-height" CSS properties
 */
function addTableStyle_(style: styleBuilder_, el: any) {
  withAttr_(el, DA_.MINIMUM_HEIGHT, mh => style.addTag("min-height", mh))

  addBoxStyle_(
    style, "padding",
    el[DA_.PADDING_TOP],
    el[DA_.PADDING_RIGHT],
    el[DA_.PADDING_BOTTOM],
    el[DA_.PADDING_LEFT]
  )
}

/**
 * Processes "margin", "text-indent" CSS Properties.
 */
function addParagraphStyle_(style: styleBuilder_, el: any) {
  let left = el[DA_.INDENT_START] ?? 0
  let firstLine = (el[DA_.INDENT_FIRST_LINE] ?? 0) - left
  let right = el[DA_.INDENT_END] ?? 0

  if (firstLine) {
    style.addTag("text-indent", `${firstLine}pt`)
  }
  if (left) {
    style.addTag("left", `${left}pt`)
  }
  if (right) {
    style.addTag("right", `${right}pt`)
  }

  addBoxStyle_(
    style, "margin",
    el[DA_.MARGIN_TOP],
    el[DA_.MARGIN_RIGHT],
    el[DA_.MARGIN_BOTTOM],
    el[DA_.MARGIN_LEFT]
  )
}

let verticalAlignmentMap_ = new Map([
  [DocumentApp.VerticalAlignment.TOP, "top"],
  // [DocumentApp.VerticalAlignment.CENTER, "middle"], default
  [DocumentApp.VerticalAlignment.BOTTOM, "bottom"],
])

let horizontalAlignmentMap = new Map([
  // [DocumentApp.HorizontalAlignment.LEFT, "left"], default
  [DocumentApp.HorizontalAlignment.CENTER, "center"],
  [DocumentApp.HorizontalAlignment.RIGHT, "right"],
  [DocumentApp.HorizontalAlignment.JUSTIFY, "justify"],
])

/**
 * Processes "text-align" and "vertical-align" CSS Properties.
 */
function addAlignmentStyle_(style: styleBuilder_, el: any) {
  style.addTag("text-align", horizontalAlignmentMap.get(el[DA_.HORIZONTAL_ALIGNMENT]))
  style.addTag("vertical-align", verticalAlignmentMap_.get(el[DA_.VERTICAL_ALIGNMENT]))
}

let listStyleMap_ = new Map([
  [DocumentApp.GlyphType.BULLET, "disc"],
  [DocumentApp.GlyphType.HOLLOW_BULLET, "circle"],
  [DocumentApp.GlyphType.SQUARE_BULLET, "square"],

  // DocumentApp.GlyphType.NUMBER is the default for EVERYTHING in ol
  [DocumentApp.GlyphType.LATIN_UPPER, "upper-alpha"],
  [DocumentApp.GlyphType.LATIN_LOWER, "lower-alpha"],
  [DocumentApp.GlyphType.ROMAN_UPPER, "upper-roman"],
  [DocumentApp.GlyphType.ROMAN_LOWER, "lower-roman"],
])

let listUlSymbols_ = new Set(["disc", "circle", "square"])

/**
 * Processes "list-style" CSS property.
 *
 * Omits this if the glyph type of the list item is "BULLET" or "NUMBER"
 * (the defaults for ul and ol respectively).
 */
function addListStyle_(style: styleBuilder_, el: any) {
  let gt = el[DA_.GLYPH_TYPE]
  let ls = listStyleMap_.get(gt)
  let lev = el[DA_.NESTING_LEVEL]

  // skip list-style if it would just re-specify the default
  if (ls && listUlSymbols_.has(ls)) {
    if (lev == 0 && ls == "disc") {
      return
    }
    if (lev == 1 && ls == "circle") {
      return
    }
    if (lev >= 2 && ls == "square") {
      return
    }
  }

  if (gt)  {
    style.addTag("list-style", listStyleMap_.get(gt))
  }
}
let unsupportedAttrs_ = [
    [DA_.PAGE_HEIGHT, "document-wide style"],
    [DA_.PAGE_WIDTH, "document-wide style"],
    [DA_.CODE, "equations not supported"],
  ]

function logUnsupportedStyle_(el: any) {
  let toPrint = unsupportedAttrs_
    .map(([attr, reason]) => [attr, reason, el[attr]])
    .filter(([attr, reason, val]) => val)
  for (let [attr, reason, val] of toPrint) {
    Logger.log(`unsupported attr ${attr}: ${reason} - ${val} ${typeof(val)}`)
  }
}

let extraStyle_ = Symbol('extraStyle_')

/**
 * @returns the html attributes for this section.
 */
function getStyle_(el: any): string | null {
  if (!el) {
    return null
  }

  let style = new styleBuilder_()

  if (el[DA_.SPACING_BEFORE]) {
    el[DA_.PADDING_TOP] = el[DA_.SPACING_BEFORE]
  }
  if (el[DA_.SPACING_AFTER]) {
    el[DA_.PADDING_BOTTOM] = el[DA_.SPACING_AFTER]
  }

  if (el[extraStyle_]) {
    style.items.push(el[extraStyle_])
  }

  addBorderStyle_(style, el)
  addRichTextStyle_(style, el)
  addTableStyle_(style, el)
  addParagraphStyle_(style, el)
  addAlignmentStyle_(style, el)
  addListStyle_(style, el)

  logUnsupportedStyle_(el)

  return style.dump()
}

/*
Handled elsewhere

(processText_)
LINK_URL	Enum	The link URL, for rich text. The default link style (foreground color, underline) is automatically applied.

(processList_)
LIST_ID	Enum	The ID of the encompassing list, for list item elements.
NESTING_LEVEL	Enum	The item nesting level, for list item elements.

(processHeading_)
HEADING	Enum	The heading type, for paragraph elements (for example, DocumentApp.ParagraphHeading.HEADING1).
*/
