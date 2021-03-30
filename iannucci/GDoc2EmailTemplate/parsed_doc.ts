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
 * ParsedDoc holds the output from ParseDoc.
 *
 * @typedef {ParsedDoc}
 * @property {HtmlService.HtmlTemplate}  subject - the template document name
 * @property {HtmlService.HtmlTemplate}  body    - the parsed body template
 * @property {object}                    images  - the parsed inline images
 */


class ParsedDoc {
  subject: GoogleAppsScript.HTML.HtmlTemplate
  body: GoogleAppsScript.HTML.HtmlTemplate
  images: Record<string, GoogleAppsScript.Document.InlineImage>

  static scriptTagFinder: RegExp = /<\?(.+?)\?>/gms;

  constructor(subject: string, htmlBody: string, images: GoogleAppsScript.Document.InlineImage[]) {
    this.subject = HtmlService.createTemplate(subject)
    this.body = HtmlService.createTemplate(htmlBody)
    this.images = Object.fromEntries(images.map((img, idx) => [`${idx}`, img]))
  }

  templatesAsCode_(): string {
    let ret = this.body.getRawContent().
      replace("<style>", "<style>code{background-color:rgba(222,222,222,0.3);color:crimson}").
      replace(ParsedDoc.scriptTagFinder, (_match, code) => {
        let tag = "<code xml:space=\"preserve\" style=\"display:block;white-space:pre\">"
        if (code.startsWith('=')) {
          tag = "<code>"
        } else if (code.startsWith('!=')) {
          tag = "<code style=\"background:black;color:red\">"
        }
        return `${tag}${escapeHTML_(code)}</code>`
      })
    return ret
  }

  /**
   * Returns the body formatted as valid (non-template) html suitable for
   * previewing the parsed template.
   *
   * @returns {string}
   */
  bodyWithTemplatesAsCode(formatted: boolean, inline_images: boolean = false): string {
    let rawBody = this.templatesAsCode_()
    if (inline_images) {
      rawBody = RenderInlineImages(rawBody, this.images)
    }
    if (!formatted) {
      return rawBody
    }

    let doc = XmlService.parse(rawBody)

    // prettify the css a bit
    let styleEl = doc.getRootElement().
      getChild("head").
      getChild("style")
    styleEl.setText(styleEl.getText().replace(/\.c\d+{/g, "\n    $&"))

    let fmtr = XmlService.getPrettyFormat()
    fmtr.setOmitDeclaration(true)
    return fmtr.format(doc).replace(/\r\n/g, '\n').trim()
  }
}

/**
 * Returns the parsed doc body with images inlined.
 */
function RenderInlineImages(body: string, images: {[imgKey: string]: GoogleAppsScript.Base.BlobSource}): string {
  let ret = body
  if (images) {
    // replace img tag sources with the urls of the images in `args`
    ret = ret.replace(/<img src="cid:(\d+)"/g, (_match, cid) => {
      let img = images[cid].getBlob()
      return `<img src="data:${img.getContentType()};base64,${Utilities.base64Encode(img.getBytes())}"`
    })
  }
  return ret
}
