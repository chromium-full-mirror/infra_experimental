/**
 * @license
 * Copyright (c) 2018 The Polymer Project Authors. All rights reserved.
 * This code may only be used under the BSD style license found at http://polymer.github.io/LICENSE.txt
 * The complete set of authors may be found at http://polymer.github.io/AUTHORS.txt
 * The complete set of contributors may be found at http://polymer.github.io/CONTRIBUTORS.txt
 * Code distributed by Google as part of the polymer project is also
 * subject to an additional IP rights grant found at http://polymer.github.io/PATENTS.txt
 */


// Import LitElement base class and html helper function
import { LitElement, html } from 'lit-element';
import {MDCRipple} from '@material/ripple';
import {MDCChipSet} from '@material/chips';
import {MDCTabBar} from '@material/tab-bar';
import './failed-test';
import './cq-attempt';


export class CLPage extends LitElement {
  static get properties() {
    return {
      changeInfo: { type: Object },
    };
  }

  constructor() {
    // Must call superconstructor first.
    super();

    // Initialize properties
    this.loadComplete = false;

    const logs = [
      {
        name: "a log",
        contentId: "extra-content-1",
      },
      {
        name: "another log",
        contentId: "extra-content-2",
      },
      {
        name: "screenshot",
        contentId: "extra-content-3",
      },
    ];
    this.failures = [
      {
        testName: "webkit|unit_tests|AccessibilitySelectionTest|List",
        visible: true,
        runs: [
          {
            variant: {
              hash: "deadbeef",
              def: {
                os: "linux",
                site_per_process: "true",
              },
            },
            visible: true,
            status: "failure",
            summary: "Assertion failed: 1 != 2",
            logs: logs,
          },
          {
            variant: {
              hash: "deadbeef",
              def: {
                os: "windows",
                site_per_process: "true",
              },
            },
            visible: true,
            status: "failure",
            summary: "Assertion failed: 1 != 2",
            logs: logs,
          },
          {
            variant: {
              hash: "badcofee",
              def: {
                os: "linux",
                site_per_process: "false",
                gpu: "ati",
              },
            },
            visible: true,
            status: "failure",
            summary: "Assertion failed: 1 != 2",
            logs: logs,
          },
        ],
      },
      {
        testName: "webkit|unit_tests|AccessibilitySelectionTest|AnotherTest",
        visible: true,
        runs: [
          {
            variant: {
              hash: "xxx",
              def: {
                os: "linux",
                site_per_process: "true",
              },
            },
            visible: true,
            status: "failure",
            summary: "incorrect",
            logs: logs,
          },
        ],
      },
      {
        testName: "browser_test|A|B",
        visible: true,
        runs: [
          {
            variant: {
              hash: "xxx",
              def: {
                os: "linux",
                viz: "false",
              },
            },
            visible: true,
            status: "failure",
            summary: "incorrect",
            logs: logs,
          },
          {
            variant: {
              hash: "yyy",
              def: {
                os: "linux",
                viz: "true",
              },
            },
            visible: true,
            status: "failure",
            summary: "wrong",
            logs: logs,
          },
        ],
      },
    ];
  }

  render() {
    return html`
      <link href="/node_modules/material-components-web/dist/material-components-web.min.css"  rel="stylesheet">
      <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">

      <h1><a href="https://crrev.com/12345">CL 12345</a></h1>

      <style>
        :host {
          font-family: Roboto;
        }
        .title-grid {
          margin: 0;
          padding: 0;
        }
        .align-right {
          text-align: right;
        }
        .test .test-body {
          display: none;
        }
        .test.expanded .test-body {
          display: block;
        }

        .test .expand-more {
          display: inline;
        }
        .test .expand-less {
          display: none;
        }
        .test.expanded .expand-more {
          display: none;
        }
        .test.expanded .expand-less {
          display: inline;
        }
        .variant-def {
          font-family: monospace;
        }
        .variant-chip-set {
          display: inline;
        }
        table.runs {
          width: 100%;
          display: table;
          border-collapse: collapse;
          border-spacing: 0;
          border: none;
        }
        table.runs tr:not(:last-child) {
          border-bottom: 1px solid rgba(0, 0, 0, 0.12);
        }
        table.runs th, table.runs td {
          border: none;
          display: table-cell;
          text-align: left;
          vertical-align: middle;
          border-radius: 2px;
        }
        table.runs ul {
          margin: 0;
        }
        .failures-card {
          margin: 10px;
          padding: 10px;
        }

        .test-name-container {
          margin: 5px;
        }
        .variant-pair {
          font-family: monospace;
        }
        #extra-content-container {
          min-width: 400px;
        }
        #extra-content-container:not(.visible), .extra-content:not(.visible) {
          display: none;
        }
        #content-container {
          display: flex;
        }
        #main-content {
          flex-grow: 1;
        }
        #variant-filter-container {
          display: flex;
          align-items: center;
        }
        #extra-content-container {
          display: flex;
          flex-direction: column;
        }
        .extra-content {
          flex-grow: 1;
        }
        .extra-content textarea {
          height: 100%;
          width: 94%;
          font-family: monospace;
        }
        .variant-column {
          min-width: 400px;
        }
        cq-attempt {
          display: none;
        }
        cq-attempt.is-active {
          display: block;
        }
      </style>

      <div id="content-container">
        <div id="main-content">

          ${!this.changeInfo.cqAttempts ? html`<p>No CQ attempts<p>` : html`
            <h2>CQ attempts</h2>
            <div id="cq-attempt-tab-bar" class="mdc-tab-bar" role="tablist">
              <div class="mdc-tab-scroller">
                <div class="mdc-tab-scroller__scroll-area">
                  <div class="mdc-tab-scroller__scroll-content">

                    ${this.changeInfo.cqAttempts.map((a, i) => {
                      const selected = i == this.changeInfo.cqAttempts.length - 1;
                      return html`
                        <button class="mdc-tab mdc-tab--min-width ${selected ? "mdc-tab--active" : ""}" role="tab" aria-selected="${selected}">
                          <span class="mdc-tab__content">
                            <span class="mdc-tab__text-label">${this.cqAttemptTabLabel(a.started)}</span>
                          </span>
                          <span class="mdc-tab-indicator ${selected ? "mdc-tab-indicator--active" : ""}">
                            <span class="mdc-tab-indicator__content mdc-tab-indicator__content--underline"></span>
                          </span>
                          <span class="mdc-tab__ripple"></span>
                        </button>
                      `;
                    })}

                  </div>
                </div>
              </div>
            </div>

            ${this.changeInfo.cqAttempts.map((a, i) => html`
              <cq-attempt
                cqattempt=${JSON.stringify(a)}
                class="${i == this.changeInfo.cqAttempts.length - 1 ? "is-active" : ""}"
                @extra-content-selected=${this.displayContent.bind(this)}
              ></cq-attempt>
            `)}
          `}

          <div class="mdc-card mdc-card--outlined failures-card">
            <h3>
              <i class="material-icons" aria-hidden="true">error</i>
              Failures
            </h3>
            <h4 class="demo-card__subtitle mdc-typography mdc-typography--subtitle2">Tests failed because of this CL</h4>

            <div id="variant-filter-container">
              Variant filter:
              <div id="variant-filter" class="mdc-chip-set mdc-chip-set--filter" @MDCChip:selection=${this.variantPairSelected.bind(this)}>
              ${Array.from(this.failedVariantPairs()).sort().map((p) => html`
                <div class="mdc-chip mdc-chip--selected" data-variant-pair=${p}>
                  <div class="mdc-chip__checkmark">
                    <svg class="mdc-chip__checkmark-svg" viewBox="-2 -3 30 30">
                      <path class="mdc-chip__checkmark-path" fill="none" stroke="black"
                            d="M1.73,12.91 8.1,19.28 22.79,4.59"/>
                    </svg>
                  </div>
                  <div class="mdc-chip__text variant-pair">${p}</div>
                </div>
              `)}
              </div>
              <button class="mdc-button" @click=${this.toggleVariantFilterHandler(true)}>all</a>
              <button class="mdc-button" @click=${this.toggleVariantFilterHandler(false)}>none</a>
            </div>

            <div>
              <button class="mdc-button" @click=${this.toggleAllTestsHandler(true)}>EXPAND ALL</button>
              <button class="mdc-button" @click=${this.toggleAllTestsHandler(false)}>COLLAPSE ALL</button>
            </div>

            <div>
              ${this.failures.filter((f) => f.visible).map(test => html`
                <div class="mdc-card test">
                  <div class="mdc-card__primary-action test-name-container" tabindex="0" @click=${this.onTestClick}>
                    <div class="mdc-layout-grid title-grid">
                      <div class="mdc-layout-grid__inner">
                        <div class="mdc-layout-grid__cell mdc-layout-grid__cell--span-11">
                          <h5><test-name testName="${test.testName}"></test-name></h5>
                        </div>
                        <div class="mdc-layout-grid__cell mdc-layout-grid__cell--span-1 align-right">
                          <i class="expand-more material-icons" aria-hidden="true">expand_more</i>
                          <i class="expand-less material-icons" aria-hidden="true">expand_less</i>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="mdc-card__actions test-body">

                    <table class="runs">
                      <thead>
                        <tr>
                          <th class="variant-column">variant</th>
                          <th class="variants-end">summary</th>
                          <th>logs & artifacts</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${test.runs.filter((r) => r.visible).sort(this.compareByVariant.bind(this)).map(tr => html`
                          <tr>
                            <td>
                              <div class="mdc-chip-set">
                                ${Object.keys(tr.variant.def).sort().map((k) => html`
                                  <div class="mdc-chip">
                                    <div class="mdc-chip__text variant-pair">${k}:${tr.variant.def[k]}</div>
                                  </div>
                                `)}
                              </div>
                            </td>
                            <td class="variants-end"><pre style="font: monospace">${tr.summary}</pre></td>
                            <td>
                              <div class="mdc-chip-set">
                              ${tr.logs.sort().map((log) => html`
                                <div class="mdc-chip" @click=${this.extraContentHandler(log.contentId)}>
                                  ${log.name}
                                </div>
                              `)}
                              </div>
                            </td>
                          </tr>
                        `)}
                      </tbody>
                    </table>

                  </div>
                </div>
              `)}
            </div>
          </div>
        </div>
        <div id="extra-content-container">
          <a href="#" @click=${this.hideExtraContent}>Close</a>
          <div class="extra-content" id="extra-content-1">
            <textarea readonly>Stack trace goes here....</textarea>
          </div>
          <div class="extra-content" id="extra-content-2">
          <textarea readonly>Another log....</textarea>
          </div>
          <div class="extra-content" id="extra-content-3">
            <img style="width:300px" src="https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/1200px-Cat03.jpg"></img>
          </div>
        </div>
      </div>
    `;
  }

  cqAttemptTabLabel(startTime) {
    return startTime.toString();
  }

  uniqueVariants(runs) {
    return new Map(runs.map(r => [r.variant.hash, r.variant]));
  }

  uniqueKeys(runs) {
    const keys = new Set();
    for (const r of runs) {
      for (const k of Object.keys(r.variant.def)) {
        keys.add(k);
      }
    }
    return Array.from(keys).sort();
  }

  variantDefArray(variantDef) {
    return Object.keys(variantDef).sort().map(k => [k, variantDef[k]]);
  }

  variantDefArrayOfStrings(variantDef) {
    return this.variantDefArray(variantDef).map((k, v) => `${k}:${v}`);
  }

  variantTitle(variantDef) {
    return this.variantDefArrayOfStrings(variantDef).join(' ');
  }

  compareByVariant(run1, run2) {
    const def1 = this.variantDefArrayOfStrings(run1.variant.def);
    const def2 = this.variantDefArrayOfStrings(run2.variant.def);
    for (let i = 0; i < Math.min(def1.length, def2.length); i++) {
      let cmp = this.compareStrings(def1[i], def2[i]);
      if (cmp != 0) {
        return cmp;
      }
    }
    return def1.length - def2.length;
  }

  compareStrings(a, b) {
    if (a < b) {
      return -1;
    }
    if (a > b) {
      return 1;
    }
    return 0;
  }

  failedVariantPairs() {
    var pairs = new Set();
    for (const f of this.failures) {
      for (const r of f.runs) {
        for (const k in r.variant.def) {
          pairs.add(`${k}:${r.variant.def[k]}`);
        }
      }
    }
    return pairs;
  }


  toggleVariantFilterHandler(show) {
    return () => {
      for (const c of this._variantFilterChipSet.chips) {
        c.selected = show;
      }
    };
  }
  extraContentHandler(contentId) {
    return (event) => {
      const container = this.shadowRoot.getElementById("extra-content-container");
      for (const el of container.querySelectorAll(".extra-content")) {
        el.classList.toggle("visible", el.id == contentId);
      }
      container.classList.add('visible');
    };
  }

  displayContent(event) {
    const contentId = event.detail.contentId;
    const container = this.shadowRoot.getElementById("extra-content-container");
    for (const el of container.querySelectorAll(".extra-content")) {
      el.classList.toggle("visible", el.id == contentId);
    }
    container.classList.add('visible');
}

  hideExtraContent() {
    this.shadowRoot.getElementById("extra-content-container").classList.remove('visible');
  }

  variantPairSelected() {
    if (!this._variantFilterChipSet) {
      return;
    }
    const predicate = new Set();
    for (const c of this._variantFilterChipSet.chips) {
      if (c.selected) {
        predicate.add(c.root_.getAttribute('data-variant-pair'));
      }
    }

    for (const f of this.failures) {
      f.visible = false;
      for (const r of f.runs) {
        r.visible = false;
        for (const k in r.variant.def) {
          if (predicate.has(`${k}:${r.variant.def[k]}`)) {
            r.visible = true;
            f.visible = true;
            break;
          }
        }
      }
    }
    this.requestUpdate();
  }

  toggleAllTestsHandler(expand) {
    return (event) => {
        for (const tEl of this.shadowRoot.querySelectorAll('.test')) {
          tEl.classList.toggle('expanded', expand);
        }
      };
  }

  onTestClick(event) {
    event.target.closest('.test').classList.toggle('expanded');
  }

  expandAll(event) {
    const filterSet = event.target.closest('.test-body').querySelector('.variant-filter-set').mdc;
    for (const c of filterSet.chips) {
      c.selected = true;
    }
  }

  collapseAll(event) {
    const filterSet = event.target.closest('.test-body').querySelector('.variant-filter-set').mdc;
    for (const c of filterSet.chips) {
      c.selected = false;
    }
  }

  /**
   * Implement firstUpdated to perform one-time work on first update:
   * - Call a method to load the lazy element if necessary
   * - Focus the checkbox
   */
  firstUpdated() {
    const selector = '.mdc-button, .mdc-icon-button, .mdc-card__primary-action';
    [].map.call(this.shadowRoot.querySelectorAll(selector), (el) => new MDCRipple(el));

    // for (const el of this.shadowRoot.querySelectorAll('.mdc-chip-set')) {
    //   el.mdc = new MDCChipSet(el);
    //   el.addEventListener('selection', () => {debugger;})
    // }

    this._variantFilterChipSet = new MDCChipSet(this.shadowRoot.getElementById("variant-filter"));

    const cqAttemptTabBarEl = this.shadowRoot.getElementById('cq-attempt-tab-bar');
    if (cqAttemptTabBarEl) {
      new MDCTabBar(cqAttemptTabBarEl);
    }
  }
}

// Register the element with the browser
customElements.define('cl-page', CLPage);
