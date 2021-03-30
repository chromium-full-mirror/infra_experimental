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

// Very heavily adapted from
// From https://github.com/huan/gast/blob/93bcc59f1081e1ca3be38b31944ee396d128f5ae/src/gas-tap-lib.js
// Code released under the MIT License (according to README.md)


class GasTapStop extends Error{}


class GasTapSession {
  tapOutput: (ok: boolean, msg?: string, stack?: string) => void

  succCounter = 0
  failCounter = 0
  skipCounter = 0

  constructor(tapOutput: (ok: boolean, msg?: string, stack?: string) => void) {
    this.tapOutput = tapOutput
  }

  ok(value: any, msg?: string) {
    if (value) {
      this.succCounter++;
      this.tapOutput(true, msg)
    } else {
      this.failCounter++;
      this.tapOutput(false, msg)
    }
  }

  notOk(value: any, msg?: string) {
    if (!value) {
      this.succCounter++;
      this.tapOutput(true, msg)
    } else {
      this.failCounter++;
      this.tapOutput(false, msg)
    }
  }

  equal(v1: any, v2: any, msg?: string) {
    if (v1 == v2) {
      this.succCounter++;
      this.tapOutput(true, msg)
    } else {
      this.failCounter++;
      this.tapOutput(false, `${v1} not equal ${v2} - ${msg}`)
    }
  }

  notEqual(v1: any, v2: any, msg?: string) {
    if (v1 != v2) {
      this.succCounter++;
      this.tapOutput(true, msg)
    } else {
      this.failCounter++;
      this.tapOutput(false, `${v1} equal ${v2} - ${msg}`)
    }
  }

  deepEqual(v1: any, v2: any, msg?: string) {
    var isDeepEqual = recursionDeepEqual(v1, v2)

    function recursionDeepEqual(rv1: any, rv2: any) {
      if (!(rv1 instanceof Object) || !(rv2 instanceof Object)) return rv1 == rv2

      if (Object.keys(rv1).length != Object.keys(rv2).length) return false

      for (var k in rv1) {
        if (!(k in rv2)
            || ((typeof rv1[k]) != (typeof rv2[k]))
        ) return false

        if (!recursionDeepEqual(rv1[k], rv2[k])) return false
      }

      return true
    }

    if (isDeepEqual) {
      this.succCounter++;
      this.tapOutput(true, msg)
    } else {
      this.failCounter++;
      this.tapOutput(false, `${v1} not deepEqual ${v2} - ${msg}`)
    }
  }

  notDeepEqual(v1: any, v2: any, msg?: string) {
    var isNotDeepEqual = recursionNotDeepEqual(v1, v2)

    function recursionNotDeepEqual(rv1: any, rv2: any) {
      if (!(rv1 instanceof Object) || !(rv2 instanceof Object)) return rv1 != rv2

      if (Object.keys(rv1).length != Object.keys(rv2).length) return true

      for (var k in rv1) {
        if (!(k in rv2)
            || ((typeof rv1[k]) != (typeof rv2[k]))
        ) return true

        if (recursionNotDeepEqual(rv1[k], rv2[k])) return true
      }

      return false
    }

    if (isNotDeepEqual) {
      this.succCounter++;
      this.tapOutput(true, msg)
    } else {
      this.failCounter++;
      this.tapOutput(false, `${v1} deepEqual ${v2} - ${msg}`)
    }
  }

  nan(v1: any, msg?: string) {
    if (v1 !== v1) {
      this.succCounter++;
      this.tapOutput(true, msg)
    } else {
      this.failCounter++;
      this.tapOutput(false, `${v1} not is NaN - ${msg}`);
    }
  }

  notNan(v1: any, msg?: string) {
    if (!(v1 !== v1)) {
      this.succCounter++;
      this.tapOutput(true, msg)
    } else {
      this.failCounter++;
      this.tapOutput(false, `${v1} is NaN - ${msg}`);
    }
  }

  throws(fn: () => void, msg?: string) {
    try {
      fn()

      this.failCounter++;
      this.tapOutput(false, 'exception wanted - ' + msg)
    } catch (e) {
      this.succCounter++;
      this.tapOutput(true, msg)
    }
  }

  notThrow(fn: ()=>void, msg?: string) {
    try {
      fn()

      this.succCounter++;
      this.tapOutput(true, msg)
    } catch (e) {
      this.failCounter++;
      this.tapOutput(false, `unexpected exception: ${e.message} - ${msg}`, e.stack)
    }
  }

  skip(msg: string) {
    this.skipCounter++;
    this.tapOutput(true, msg + ' # SKIP')
    throw new GasTapStop()
  }

  pass(msg: string) {
    this.succCounter++;
    this.tapOutput(true, msg + ' # PASS')
    throw new GasTapStop()
  }

  fail(msg: string) {
    this.failCounter++;
    this.tapOutput(false, msg + ' # FAIL')
    throw new GasTapStop()
  }
}


class GasTap {
  static VERSION = '0.3.0'

  loggerFunc: (msg: any) => void

  counter = 0

  totalSucc = 0
  totalFail = 0
  totalSkip = 0

  constructor(options?: {logger: (msg: any) => void}) {
    this.loggerFunc = (options ?? {}).logger ?? ((msg) => Logger.log(msg))
  }

  print(...args: any[]) {
    this.loggerFunc(args.map(String).join(" "))
  }

  end() {
    var totalNum = this.totalSucc + this.totalFail + this.totalSkip

    var msg = Utilities.formatString('%s..%s'
      , Math.floor(totalNum)>0 ? 1 : 0
      , Math.floor(totalNum))
    this.print(msg)

    msg = Utilities.formatString('%s tests, %s failures', Math.floor(totalNum),
                                 Math.floor(this.totalFail))

    if (this.totalSkip>0) {
      msg += ', ' + Math.floor(this.totalSkip) + ' skipped'
    }

    this.print(msg)
  }

  test(description: string, run: (t: GasTapSession) => void) {
    let tapOutput = (ok: boolean, msg?: string, stack?: string): void => {
      this.print(`${!ok?'not ':''}ok ${++this.counter} - ${msg} - ${description}`)
      if (stack != null) {
        this.print(stack.split("\n").map((line) => `  ${line}`).join("\n"))
      }
    }
    let session = new GasTapSession(tapOutput)

    try {
      run(session)
    } catch ( e ) {
      if (!(e instanceof GasTapStop)) {
        if (e instanceof Error) {
          this.loggerFunc(`Stack:\n${e.stack}`)
        }
        throw e
      }
    } finally {
      this.totalSucc += session.succCounter
      this.totalFail += session.failCounter
      this.totalSkip += session.skipCounter
    }
  }
}
