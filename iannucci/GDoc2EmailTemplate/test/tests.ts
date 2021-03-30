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

// To run tests, remove "_" suffix, which will make this function eligible for running
// in the debugger.
function allTests() {
  let outbuf: string[] = []

  let gt = new GasTap()
  gt.loggerFunc = (msg: any) => {
    outbuf.push(String(msg))
  }

  gt.test('empty', t => {
    let htmlOut = ParseDoc(DocumentApp.openById("1_F25VZrPllYR5tCV4WBrkjbheX2HSMW7wl69Ltoi8M0"))
    let lhs = htmlOut.bodyWithTemplatesAsCode(true, false)
    let rhs = HtmlService.createHtmlOutputFromFile("test/empty").getContent()
    t.equal(lhs.trim(), rhs.trim(), "renders expected content")
  })

  gt.test('comprehensive', t => {
    let htmlOut = ParseDoc(DocumentApp.openById("16_9tBMjkUFOKVoxTiGSNy8P5DAD52IvyxBGS6EnvRXY"))
    let lhs = htmlOut.bodyWithTemplatesAsCode(true, false)
    let rhs = HtmlService.createHtmlOutputFromFile("test/comprehensive").getContent()
    t.equal(lhs.trim(), rhs.trim(), "renders expected content")
  })

  gt.end()

  for (let msg of outbuf) {
    Logger.log(msg)
  }

  return outbuf.join('\n')
}
