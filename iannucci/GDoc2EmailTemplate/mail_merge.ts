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

enum MailMergeStrategy {
  MailDryRun = 'DRY_RUN',
  MailSelf = 'MAIL_SELF',
  MailBroadcast = 'BROADCAST',
}

enum MailMergeStatus {
  // MergeUnset is the default state, and emails in this state will
  // be sent if MailMerge is invoked.
  MergeUnset = "",

  // MergeOK is equivalent to Unset, but will be set by MailMerge in
  // MailDryRun mode when the data parsed and the template rendered fine.
  MergeOK = "OK",

  // MergeSent indicates that this email was successfully sent. Subsequent
  // calls to MailMerge will ignore this email.
  MergeSent = "SENT",

  // MergeError indicates that the last attempt to merge had some error.
  // Subsequent calls to MailMerge will ignore this email (if you want to
  // send it, fix the email and try again).
  MergeError = "ERROR",
}

const MailMergeSheetHeader = Object.freeze([
  // Status is read and written by the MailMerge function and must have
  // a value in MailMergeStatus.
  "Status",
  // ErrorMessage is output from MailMerge when Status==ERROR and indicates
  // what went wrong.
  "ErrorMessage",

  // These are outputs; MailMerge will use these to populate the respective
  // fields. These should be formatted as comma separated lists of emails.
  "To",
  "Cc",
  "Bcc",
])

function GetMailMergeSheetHeader(): Readonly<string[]> {
  return MailMergeSheetHeader
}

type walkMergeCb_ = (
  status: MailMergeStatus,
  dataBlob: {[key: string]: any},
  msg: () => GoogleAppsScript.Mail.MailAdvancedParameters,
) => {next?: boolean, status?: MailMergeStatus, errMsg?: string};


function walkMerge_(
  dataSheet: GoogleAppsScript.Spreadsheet.Sheet,
  template: GoogleAppsScript.Document.Document,
  ctorMap: {[kind: string]: () => object},
  extraProps: {[key: string]: any},
  cb: walkMergeCb_,
) {
  let data = dataSheet.getDataRange().getValues()
  if (data[0].length < MailMergeSheetHeader.length) {
    throw `malformed dataSheet header row; too short`
  }
  for (let idx = 0; idx < MailMergeSheetHeader.length; idx++) {
    if (data[0][idx] != MailMergeSheetHeader[idx]) {
      throw `unexpected header[${idx}]=${data[0][idx]} (expected $)`
    }
  }
  let dataHeaders = data[0].slice(MailMergeSheetHeader.length).map(itm => {
    let sItm = String(itm)
    let literal = sItm.endsWith('=')
    let name = literal ? sItm.slice(0, -1) : sItm
    return {name: name, literal: literal}
  })

  let parsedDoc = ParseDoc(template)
  for (let prop in extraProps) {
    parsedDoc.body[prop] = extraProps[prop]
    parsedDoc.subject[prop] = extraProps[prop]
  }

  let setRowStatus = function(row: number, status: MailMergeStatus, msg: string = '') {
    dataSheet.getRange(row, 1, 1, 2).setValues([
      [status, msg]
    ])
  }

  let jsonParse = function(obj: any): any {
    return JSON.parse(obj.toString(), (key: string, value: any): any => {
      let ret = value
      if (value instanceof Object && value.hasOwnProperty('$kind')) {
        let ctor = ctorMap[value['$kind']]
        if (ctor !== undefined) {
          ret = Object.assign(new (ctor as any)(), value)
          if (ret['postJson']) {
            ret.postJson()
          }
        }
      }
      return ret
    })
  }

  for (let idx = 1; idx < data.length; idx++) {
    let currentStage = 'initializing'
    try {
      let [rawStatus, _errMsg, to, cc, bcc, ...userData] = data[idx]
      let status: MailMergeStatus = rawStatus

      currentStage = 'transforming data'
      let dataBlob: {[key: string]: any} = {}
      for (let datIdx = 0; datIdx < userData.length; datIdx++) {
        let {name, literal} = dataHeaders[datIdx]
        let transform = (itm: string) => itm
        if (!literal) {
          transform = jsonParse
        }
        let datum = transform(userData[datIdx])
        dataBlob[name] = datum
        parsedDoc.body[name] = datum
        parsedDoc.subject[name] = datum
      }

      currentStage = 'applying strategy'
      let cbret = cb(rawStatus, dataBlob, () => {
        currentStage = 'rendering template'
        let message = {
          subject: parsedDoc.subject.evaluate().getContent(),
          to: to,
          cc: cc,
          bcc: bcc,
          htmlBody: parsedDoc.body.evaluate().getContent(),
          inlineImages: parsedDoc.images,
        }
        currentStage = 'applying strategy'
        return message
      })

      if (cbret.status) {
        setRowStatus(idx+1, cbret.status, cbret.errMsg)
      }
      if (cbret.next === false) {
        break
      }
    } catch(ex) {
      if (ex instanceof Error) {
        setRowStatus(idx+1, MailMergeStatus.MergeError, `while ${currentStage}:\n${ex.stack}`)
      } else {
        setRowStatus(idx+1, MailMergeStatus.MergeError, `while ${currentStage}:\n${ex}`)
      }
    }
  }
}

function adjustPreviewMessage_(msg: GoogleAppsScript.Mail.MailAdvancedParameters) {
  msg.subject = `[GDoc2EmailTemplate Test] ${msg.subject}`
  msg.htmlBody = msg.htmlBody!.replace(
    '<body>', [
      '<body>',
      msg.to  ? `<p>To: [${escapeHTML_(msg.to)}]</p>`   : '',
      msg.cc  ? `<p>Cc: [${escapeHTML_(msg.cc)}]</p>`   : '',
      msg.bcc ? `<p>Bcc: [${escapeHTML_(msg.bcc)}]</p>` : '',
      `<p><hr/></p>`,
    ].join(''),
  )
}

/**
 * MailMerge takes a sheet of spreadsheet data and a template google doc
 * and then does a mail merge with the given strategy.
 *
 * The dataSheet is expected to have the following format:
 *   * A header which starts with MailMergeSheetHeader
 *   * Each extra column after this will be added as the template context.
 *     If the column header ends with '=' then the cell contents will be
 *     used verbatim, otherwise the cell contents will be deserialized
 *     as JSON using a reviver function with `ctorMap` for re-inflating
 *     classes.
 *
 *     Example 1: if the column after 'Bcc' is 'thing=', then that cell
 *     for the current email will be made available in the template verbatim
 *     as 'thing'.
 *
 *     Example 2: if the column after 'Bcc' is 'thing',
 *     then that cell for the current email will be deserialized as JSON
 *     and made available to the template scriptlets as the variable 'thing'.
 *
 *     See `ctorMap` for it's involvement in this process.
 *   * One row per email which should be sent.
 *
 * @param {SpreadsheetApp.Sheet} dataSheet - The Status column in the data sheet
 *   is a bi-directional indicator for the mail merge procedure. See
 *   MailMergeStatus docs for which each status means.
 *
 *   In particular, rows with Status == {SENT, ERROR} will be skipped by
 *   MailMerge.
 *
 * @param {DocumentApp.Document} template - The Document to use for the email
 *   template. Refer to ParseDoc for how this document will be interpreted.
 *
 * @param {'DRY_RUN'|'MAIL_SELF'|'BROADCAST'} strategy - The method MailMerge
 *   will use to return data to you.
 *
 *   - If strategy == 'DRY_RUN', the dataSheet's Status and ErrorMessage
 *   columns will be updated, but no other action will happen.
 *
 *   - If strategy == 'MAIL_SELF', this will use the MailApp to send your own
 *   email address each of the populated templates. They have the following
 *   differences:
 *     * The Subject will be prepended with `[GDoc2EmailTemplate Test] `
 *     * The `To`, `Cc`, and `Bcc` lines will be in the body of the email.
 *
 *   - If strategy == 'BROADCAST', this sends the emails out to the intended
 *   recipients.
 *
 * @param {Object<string, function(new: Object)>} ctorMap - This maps from
 *   a kind name to a constructor for some object. When the extra data for
 *   the given row is deserialized, a reviver function will:
 *     * Look to see if the deserialized thing is an Object with a key '$kind'.
 *     * If the value of '$kind' is in ctorMap, it will use the result of
 *       `new ctorMap[kind]()` as the target of Object.assign.
 *     * If the new object has a function `postJson`, it will be called.
 *
 * @param {string} replyTo - If specified, will be used as the replyTo address
 *   for all messages.
 *
 * @param {Object<string, any>} extraProps - If provided, all properties of this
 *   object will be assigned as context within the template. This can be used to
 *   make processing functions available within template scriptlets.
 */
function MailMerge(
  dataSheet: GoogleAppsScript.Spreadsheet.Sheet,
  template: GoogleAppsScript.Document.Document,
  strategy: MailMergeStrategy = MailMergeStrategy.MailDryRun,
  ctorMap: {[kind: string]: () => object},
  replyTo = '',
  extraProps: {[key: string]: any} = {}
) {

  let userAddress = Session.getActiveUser().getEmail()
  walkMerge_(dataSheet, template, ctorMap, extraProps, (status, _, msgFn) => {
    switch (status) {
      case MailMergeStatus.MergeError:
      case MailMergeStatus.MergeSent:
        // These indicate that we're skipping this row.
        return {}

      case MailMergeStatus.MergeUnset:
        case MailMergeStatus.MergeOK:
        break

      default:
        // In typescript this lets us statically assert that we've covered
        // all the known enum cases.
        let exhaustivenessCheck_ : never = status
        // However, in javascript, we'll still get here if the user enters
        // a bogus status. Set an error message and continue.
        return {
          status: MailMergeStatus.MergeError,
          errMsg: `Unknown Status '${status}'`,
        }
    }

    let finalStatus = MailMergeStatus.MergeOK
    let msg = msgFn()
    switch (strategy) {
      case MailMergeStrategy.MailDryRun:
        return {status: MailMergeStatus.MergeOK}

      case MailMergeStrategy.MailBroadcast:
        finalStatus = MailMergeStatus.MergeSent
        break

      case MailMergeStrategy.MailSelf:
        adjustPreviewMessage_(msg)
        msg.to = userAddress
        msg.cc = undefined
        msg.bcc = undefined
        msg.replyTo = replyTo
        break

      default:
        let exhaustivenessCheck_ : never = strategy
        throw `strategy ${strategy} not implemented`
    }

    MailApp.sendEmail(msg)
    return {status: finalStatus}
  })
}

/**
 * Similar to MailMerge, but renders a single merged email of your
 * choosing in the current ui.
 *
 * Pops a modal dialog with an HTML rendering of the email we would
 * send as if MailMerge had been selected with MAIL_SELF as the
 * strategy.
 *
 * @param {Base.Ui} ui - The UI object to display a dialog in.
 * @param {(rowData: {[key: string]: any}) => boolean} predicate - A
 *   function which is provided an Object with all decoded data columns
 *   from the row, and should return `true` if this is the row we
 *   should preview.
 *
 * See MailMerge for other parameters.
 */
function PreviewMail(
  ui: GoogleAppsScript.Base.Ui,
  predicate: (rowData: {[key: string]: any}) => boolean,
  dataSheet: GoogleAppsScript.Spreadsheet.Sheet,
  template: GoogleAppsScript.Document.Document,
  ctorMap: {[kind: string]: () => object},
  extraProps: {[key: string]: any} = {}) {

  walkMerge_(dataSheet, template, ctorMap, extraProps, (status, dataBlob, msgFn) => {
    if (predicate(dataBlob)) {
      let msg = msgFn()
      adjustPreviewMessage_(msg)

      let body = RenderInlineImages(msg.htmlBody!, msg.inlineImages!)

      ui.showModalDialog(
        HtmlService.createHtmlOutput(body).setWidth(890).setHeight(500),
        msg.subject!)
      return {next: false}
    }
    return {}
  })
}
