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

const paragraphHeadings_: Readonly<GoogleAppsScript.Document.ParagraphHeading[]> = [
  //DocumentApp.ParagraphHeading.NORMAL,
  DocumentApp.ParagraphHeading.TITLE,
  DocumentApp.ParagraphHeading.SUBTITLE,
  DocumentApp.ParagraphHeading.HEADING6,
  DocumentApp.ParagraphHeading.HEADING5,
  DocumentApp.ParagraphHeading.HEADING4,
  DocumentApp.ParagraphHeading.HEADING3,
  DocumentApp.ParagraphHeading.HEADING2,
  DocumentApp.ParagraphHeading.HEADING1,
]

interface debugAttrs {
  debugAttrs(): object
}

class closeTag_ extends String implements debugAttrs {
  openingTag: openTag_
  tag: string

  constructor(value: string, openingTag: openTag_) {
    super(value)
    this.openingTag = openingTag
    this.tag = openingTag.tag
  }

  debugAttrs() {
    return {openingTag: this.openingTag}
  }
}

class scriptBlock_ extends String implements debugAttrs {
  indentLevel: number

  constructor(value: string, indentLevel: number) {
    super(value)
    if (indentLevel % 1 != 0) {
      throw `non-integer indentLevel: ${indentLevel}`
    }
    this.indentLevel = indentLevel
  }

  debugAttrs() {
    return {indentLevel: this.indentLevel}
  }
}

class openTag_ extends String {
  tag: string

  constructor(value: string, tag: string) {
    super(value)
    this.tag = tag
  }
}

type taggedType_ = openTag_ | closeTag_
type scriptType_ = string | scriptBlock_
type bufferType_ = string | openTag_ | closeTag_ | scriptBlock_

class emailBuilder_ {
  subject: string
  toTemplate: string = ''

  // If true, means we're looking for script blocks in the input document,
  // otherwise all text should be HTML escaped as-is.
  templateMode: boolean

  headingStyles: Map<GoogleAppsScript.Document.ParagraphHeading, any> = new Map()
  closingTagStack: (null|closeTag_)[] = []

  // Holds the buffered tokens for the email doc in progress.
  buffer: bufferType_[] = []

  // The current 'INDENT_START' attribute for the paragraph currently being
  // processed.
  //
  // Set and zero'd in processParagraph_; Used to evaluate the current
  // indentation level of script blocks in order to correctly place them
  // within lists.
  curStartIndent = 0

  // buffer of string tokens while we're inside a script block.
  scriptBuffer: string[] = []

  // Holds a mapping from a listid to its current value. Only used for ordered
  // lists.
  listCounterState: Map<string, number> = new Map()

  // Holds start-tags which would have been emitted within
  // a script section. If the script section ends and this is non-empty,
  // they will be emitted after the end of the script section before the
  // rest of thed document processing resumes.
  delayedTags: (openTag_ | null)[] = []

  // Holds all images discovered from document.
  images: GoogleAppsScript.Document.InlineImage[] = []

  // Map<string, number>} Maps from a style string to its class name. Stored
  // "backwards" to allow de-duplication of exactly-matching styles.
  styleToClass: Map<string, number> = new Map()

  globalStyles: string[]

  constructor(doc: GoogleAppsScript.Document.Document, templateMode: boolean) {
    this.subject = doc.getName()

    let body = doc.getBody()
    for (let heading of paragraphHeadings_) {
      this.headingStyles.set(heading, body.getHeadingAttributes(heading))
    }

    this.templateMode = templateMode

    this.globalStyles = [
      // set default style for everything
      `body{${getStyle_(body.getHeadingAttributes(DocumentApp.ParagraphHeading.NORMAL))}}`,
      // margins are specifically adjusted where necessary, default to 0
      `p,ul,ol{margin:0}`,
      // tables by default take the entire width
      `table{width:100%;border-collapse:collapse}`,
      // special class for 'no-show' list items
      `.x{list-style-type:none}`
    ]
  }

  nextListValue(listId: string): number {
    if (!this.listCounterState.has(listId)) {
      this.listCounterState.set(listId, 1)
    }
    let ret = this.listCounterState.get(listId)!
    this.listCounterState.set(listId, ret+1)
    return ret
  }

  swizzleBuffer() {
    // First, apply the following rules:
    //   </table><? ?>    => <? ?></table>
    //   </table><table>  =>
    //   <? ?> | <table ...>  => <table ...> <? ?>
    for (let idx = 1; idx < this.buffer.length - 1; idx++) {
      let a = this.buffer[idx-1]
      let b = this.buffer[idx]

      if (a instanceof closeTag_ && a.tag == 'table' && b instanceof scriptBlock_) {
        [this.buffer[idx], this.buffer[idx -1]] = [this.buffer[idx - 1], this.buffer[idx]];
        idx--  // reprocess the moved close tag
      } else if (a instanceof closeTag_ && b instanceof openTag_ && a.tag == 'table' && a.openingTag.toString() === b.toString()) {
        this.buffer.splice(idx-1, 2)
        idx -= 2
      } else if (a instanceof scriptBlock_ && b instanceof openTag_ && b.tag == 'table') {
        [this.buffer[idx], this.buffer[idx -1]] = [this.buffer[idx - 1], this.buffer[idx]]
      }
    }
  }

  /**
   * @return {ParsedDoc}
   */
  getParsedDoc() {
    if (this.closingTagStack.length != 0) {
      throw `closingTagStack buffer non-empty: ${this.closingTagStack}`
    }
    if (this.scriptBuffer.length) {
      throw `scriptBuffer == ${this.scriptBuffer}: mismatched <? ?> tags?`
    }

    this.swizzleBuffer()

    let body = this.buffer.join("")
    let headBuf = [
      '<head>',
      '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />',
    ]
    if (this.styleToClass.size > 0) {
      headBuf.push('<style>', ...this.globalStyles)
      for (let [style, classId] of this.styleToClass) {
        headBuf.push(`.c${classId}{${style}}`)
      }
      headBuf.push('</style>')
    }
    headBuf.push('</head>')
    return new ParsedDoc(this.subject, `<!DOCTYPE html><html>${headBuf.join('')}${body}</html>`, this.images)
  }

  /**
   * @returns The key for the newly added image.
   */
  addImage(inlineImage : GoogleAppsScript.Document.InlineImage): string {
    let ret = `${this.images.length}`
    this.images.push(inlineImage)
    return ret
  }

  /**
   * Pushes an html tag into the state, deriving the `style` css
   * from `el`.
   *
   * tagPrefix can:
   *   * start with "?" which means that the tag will only be emitted
   *     if it would have stlying classes. A null token will still be
   *     added to the tag stack so popTag() should still be called to
   *     balance this.
   *   * contain a space followed by additional attributes:
   *     "tag attr=value". Should not include 'class' attribute
   *     which will be computed from `attrBlobs`.
   *   * end with a "/" to indicate a self-closing tag
   */
  pushTag(tagPrefix: string, ...attrBlobs: any[]) {
    let classes = attrBlobs.map(attrBlob => {
      let style = getStyle_(attrBlob)
      if (!style) {
        return null
      }
      let cls = this.styleToClass.get(style)
      if (cls === undefined) {
        cls = this.styleToClass.size + 1
        this.styleToClass.set(style, cls)
      }
      return cls
    }).filter(cls => cls !== null)

    let isOptional = tagPrefix.startsWith("?")
    if (isOptional) {
      tagPrefix = tagPrefix.slice(1)
    }

    let isSelfClosing = tagPrefix.endsWith("/")
    if (isSelfClosing) {
      tagPrefix = tagPrefix.slice(0, -1)
    }

    let tag = tagPrefix.split(" ")[0]
    let endBracket = isSelfClosing ? '/>' : '>'

    let fullTag : null|openTag_ = null
    let closeTag : null|closeTag_ = null
    if (classes.length > 0) {
      fullTag = new openTag_(
        `<${tagPrefix} class="${classes.map(cls => `c${cls}`).join(" ")}"${endBracket}`,
        tag)
    } else if (isOptional) {
      fullTag = null
      tag = ""
    } else {
      fullTag = new openTag_(`<${tagPrefix}${endBracket}`, tag)
    }
    if (!isSelfClosing && fullTag) {
      closeTag = new closeTag_(`</${tag}>`, fullTag)
    }

    if (!this.scriptBuffer.length) {  // HTML mode
      let lastItem = this.buffer[-1]
      if (this.buffer.length && lastItem instanceof closeTag_ && fullTag && lastItem.openingTag.toString() == fullTag.toString()) {
        this.buffer.pop()
        fullTag = null
      }
      if (fullTag) {
        this.buffer.push(fullTag)
      }
    } else { // scriptlet mode
      if (tag == "p") {
        // so multi-line scripts actually take multiple lines.
        this.scriptBuffer.push("\n")
      }
      if (!isSelfClosing) {
        // note; it's important to push SOMETHING here for balance in popTag's
        // scriptlet handling section. pushText will filter out any empty items
        // from delayedTags before pushing onto buffer.
        this.delayedTags.push(fullTag)
      }
    }
    if (!isSelfClosing) {
      // it's important we always push SOMETHING to the closingTagStack so that users
      // calling pushTag/popTag in balance won't goof things up.
      this.closingTagStack.push(closeTag)
    }
  }

  popTag(important = false) {
    if (this.closingTagStack.length == 0) {
      throw 'popTag called with empty closingTagStack'
    }
    let closeTag = this.closingTagStack.pop()

    if (this.scriptBuffer.length && this.delayedTags.length) {
      // if there's a tag in delayedTags then the tag we just popped out
      // cancels out a push within the script
      this.delayedTags.pop()
      return
    }

    if (!closeTag) {
      return
    }

    let { prev, idx } = this.prevOpenTag()
    if (!important && prev == closeTag.openingTag) {
      // If we're just closing the tag we just opened (and it wasn't important
      // to keep), just cut it out. Also applies if we're closing a tag which
      // only contains a scriptblock.
      this.buffer.splice(idx, 1)
    } else {
      this.buffer.push(closeTag)
    }
  }

  pushText(text: string) {
    if (!this.templateMode) {
      this.buffer.push(escapeHTML_(text))
      return
    }

    while (text.length > 0) {
      if (!this.scriptBuffer.length) {
        let scriptStart = text.indexOf("<?")
        if (scriptStart == -1) {
          this.buffer.push(escapeHTML_(text))
          return
        }

        if (scriptStart) {
          // some text between us and the previous tag
          this.buffer.push(escapeHTML_(text.slice(0, scriptStart)))
        }

        this.scriptBuffer = ['<?']
        text = text.slice(scriptStart + 2)
      } else {
        // scan until we find ?>
        //
        // NOTE: As of 2021Q1, HTMLService.createTemplate is dumb as bricks.
        // It doesn't know anything about the content between <? and ?>, meaning
        // that, e.g.
        //     <?= "?>" ?>
        // Does not produce "?&gt;", as you would expect, but instead results
        // in an error. Makes our job easier though since we don't have to
        // parse quotes, escapes or arbitrary javascript expressions within
        // backtick strings :)
        let scriptEnd = text.indexOf("?>")
        if (scriptEnd == -1) {
          // no match in this block, it's all script data
          this.scriptBuffer.push(text)
          return
        }

        // however much it was, it's script data and we want it
        this.scriptBuffer.push(text.slice(0, scriptEnd + 2))  // 2 == "?>".length
        let code: scriptType_ = this.scriptBuffer.join("")
        if (code.startsWith("<? ")) {
          code = new scriptBlock_(code, this.curStartIndent / 36)
        }
        this.buffer.push(code)
        this.scriptBuffer = []
        text = text.slice(scriptEnd + 2)

        let delayedTags = this.delayedTags.filter(itm => itm) as openTag_[]
        this.delayedTags = []
        if (delayedTags.length) {
          this.buffer.push(...delayedTags)
        }
      }
    }
  }

  /**
   * Looks back at most 2 elements in the buffer and returns the earliest
   * of the two which is an HTML open or close tag.
   *
   * If both tokens are a script, returns {prev: "", idx: -1}
   */
  prevOpenTag() {
    let [a, b] = this.buffer.slice(-2)
    if (b instanceof openTag_) {
      return { prev: b, idx: this.buffer.length - 1 }
    }
    // only allow skipping the last element if it is a script tag.
    if (b instanceof scriptBlock_ && a instanceof openTag_) {
      return { prev: a, idx: this.buffer.length - 2 }
    }
    // otherwise consider the search failed
    return { prev: null, idx: -1 }
  }
}


let htmlEntityMap_ = new Map([
  ['&', '&amp;'],
  ['<', '&lt;'],
  ['>', '&gt;'],
  ['"', '&quot;'],
  ["'", '&#39;'],
  ['/', '&#x2F;'],
  ['`', '&#x60;'],
  ['=', '&#x3D;'],
])
let htmlEntityRE_ = new RegExp(`[${Array.from(htmlEntityMap_.keys()).join('')}]`, 'g')

/**
 * @param {string} data
 * @return {string}
 */
function escapeHTML_(data: string): string {
  return data.replace(htmlEntityRE_, m => htmlEntityMap_.get(m) ?? '')
}
