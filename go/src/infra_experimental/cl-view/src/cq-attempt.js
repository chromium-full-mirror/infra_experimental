// Import LitElement base class and html helper function
import { LitElement, html } from 'lit-element';
import {MDCRipple} from '@material/ripple';
import {MDCChipSet} from '@material/chips';
import {MDCTabBar} from '@material/tab-bar';
import './failed-test';
import { fail } from 'assert';

const StatusNames = {
  1: 'SUCCESS',
  2: 'FAIL',
  3: 'CRASH',
  4: 'ABORT',
  5: 'SKIP',
};

class TestView extends LitElement {
  static get properties() {
    return {
      invocationId: { type: String },
      test: { type: Object },
      predicate: { type: Object },
    };
  }

  constructor() {
    super();

    let expanded = false;
    Object.defineProperty(this, "expanded", {
      get: () => expanded,
      set: (value) => {
        expanded = !!value;
        if (expanded) {
          this._maybeLoadTestRuns();
        }
        this.requestUpdate();
      },
    })
  }

  render() {
    const variantPredicate = new Set((this.predicate || {}).variants || []);

    const runs = (this.runs || [])
      .filter((run) => run.variantDef.length == 0 || run.variantDef.some((p) => variantPredicate.has(p)));

    return html`
      <link href="/node_modules/material-components-web/dist/material-components-web.min.css"  rel="stylesheet">
      <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">

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
        :not(.expanded) .test-body {
          display: none;
        }

        .expand-more {
          display: inline;
        }
        .expand-less {
          display: none;
        }
        .expanded .expand-more {
          display: none;
        }
        .expanded .expand-less {
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

        .test-container {
          margin: 5px;
        }
        .test-name-containier {
          display: flex;
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
        .loaded .loading-progress {
          display: none;
        }
      </style>

      <div class="mdc-card ${this.loaded ? "loaded" : ""} ${this.expanded ? "expanded" : ""}">
        <div class="mdc-card__primary-action test-container" tabindex="0" @click=${this.onClick.bind(this)}>
          <div class="mdc-layout-grid title-grid">
            <div class="mdc-layout-grid__inner">
              <div class="mdc-layout-grid__cell mdc-layout-grid__cell--span-11 test-name">
                <test-name testName="${this.test.testName}"></test-name>
              </div>
              <div class="mdc-layout-grid__cell mdc-layout-grid__cell--span-1 align-right">
                <i class="expand-more material-icons" aria-hidden="true">expand_more</i>
                <i class="expand-less material-icons" aria-hidden="true">expand_less</i>
              </div>
            </div>
          </div>
        </div>

        <div class="test-body">
          <div role="progressbar" class="loading-progress mdc-linear-progress mdc-linear-progress--indeterminate">
            <div class="mdc-linear-progress__buffering-dots"></div>
            <div class="mdc-linear-progress__buffer"></div>
            <div class="mdc-linear-progress__bar mdc-linear-progress__primary-bar">
              <span class="mdc-linear-progress__bar-inner"></span>
            </div>
            <div class="mdc-linear-progress__bar mdc-linear-progress__secondary-bar">
              <span class="mdc-linear-progress__bar-inner"></span>
            </div>
          </div>

          <table class="runs">
            <thead>
              <tr>
                <th>variant</th>
                <th>status</th>
                <th>summary</th>
                <th>logs & artifacts</th>
              </tr>
            </thead>
            <tbody>
              ${runs.map((run) => html`
                <tr>
                  <td>
                    <div class="mdc-chip-set">
                      ${run.variantDef.sort().map((p) => html`
                        <div class="mdc-chip">
                          <div class="mdc-chip__text variant-pair">${p}</div>
                        </div>
                      `)}
                    </div>
                  </td>
                  <td>${StatusNames[run.status]}</td>
                  <td class="variants-end"><pre style="font: monospace">Assertion failed: 1 != 2</pre></td>
                  <td>
                    <div class="mdc-chip-set">
                      <div class="mdc-chip" @click=${this.extraContentHandler("extra-content-1").bind(this)}>Log 1</div>
                      <div class="mdc-chip" @click=${this.extraContentHandler("extra-content-2").bind(this)}>Log 2</div>
                      <div class="mdc-chip" @click=${this.extraContentHandler("extra-content-3").bind(this)}>Screenshot</div>
                    </div>
                  </td>
                </tr>
              `)}
            </tbody>
          </table>

          <div id="extra-content-container">
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
      </div>
    `;
  }

  extraContentHandler(contentId) {
    return () => {
      const container = this.shadowRoot.querySelector("#extra-content-container");
      for (const el of container.querySelectorAll(".extra-content")) {
        el.classList.toggle("visible", el.id == contentId);
      }
      container.classList.add('visible');
    };
  }

  hideExtraContent() {
    this.shadowRoot.getElementById("extra-content-container").classList.remove('visible');
  }

  async onClick(event) {
    this.expanded = !this.expanded;
  }

  async _maybeLoadTestRuns() {
    if (this.runPromise) {
      return;
    }

    this.runPromise = this._loadTestRuns();
    this.runs = await this.runPromise;
    this.loaded = true;
    this.requestUpdate();
  }

  async _loadTestRuns() {
    const res = await fetch("/rpc/test-runs", {
      method: 'POST',
      body: JSON.stringify({
        InvocationId: this.invocationId,
        TestName: this.test.testName,
      })
    });
    const resBody = await res.json();
    return resBody.runs;
  }

}

customElements.define('test-view', TestView);

export class CQAttempt extends LitElement {
  static get properties() {
    return {
      cqAttempt: { type: Object },
    };
  }

  render() {
    const variantPredicate = new Set();
    if (this._variantFilterChipSet) {
      for (const c of this._variantFilterChipSet.chips) {
        if (c.selected) {
          variantPredicate.add(c.root_.getAttribute('data-variant-pair'));
        }
      }
    }

    const predicate = { variants: Array.from(variantPredicate) };

    const variantPairs = new Set();
    const testMap = {};
    if (this.cqAttempt) {
      // Collect unique variant pairs.
      for (const tv of this.cqAttempt.interestingTestVariants || []) {
        for (const pair of tv.variantDef) {
          variantPairs.add(pair);
        }
      }

      for (const tv of this.cqAttempt.interestingTestVariants || []) {
        const match = tv.variantDef.some((p) => variantPredicate.has(p));
        if (match) {
          let test = testMap[tv.testName];
          if (!test) {
            test = {
              testName: tv.testName,
              variants: {},
            };
            testMap[tv.testName] = test;
          }

          test.variants[tv.variantHash] = tv;
        }
      }
    }
    const tests = Object.keys(testMap).sort().map((testName) => testMap[testName]);

    return html`
      <link href="/node_modules/material-components-web/dist/material-components-web.min.css"  rel="stylesheet">
      <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">

      <p>
        ${this.totalTestRuns} test runs of ${this.totalTestVariants} variants of
        ${this.totalTests} tests.
      </p>

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
        :not(.expanded) .test-body {
          display: none;
        }

        .expand-more {
          display: inline;
        }
        .expand-less {
          display: none;
        }
        .expanded .expand-more {
          display: none;
        }
        .expanded .expand-less {
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

        .test-container {
          margin: 5px;
        }
        .test-name-containier {
          display: flex;
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
        .loaded .loading-progress {
          display: none;
        }
      </style>

      <div class="mdc-card mdc-card--outlined failures-card">
        <div>
          <h3>Stats<h3>
          <div>Tests: ${this.cqAttempt.totalTests}</div>
          <div>Test variants: ${this.cqAttempt.totalVariants}</div>
          <div>Test runs: ${this.cqAttempt.totalTestRuns}</div>
        </div>

        <div id="variant-filter-container">
          Variant filter:
          <div id="variant-filter" class="mdc-chip-set mdc-chip-set--filter" @MDCChip:selection=${this.variantPairSelected.bind(this)}>
            ${Array.from(variantPairs).sort().map((p) => html`
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
          <button class="mdc-button" @click=${this.toggleAllTests(true).bind(this)}>EXPAND ALL</button>
          <button class="mdc-button" @click=${this.toggleAllTests(false).bind(this)}>COLLAPSE ALL</button>
        </div>

        <div>
          ${tests.map(test => html`
            <test-view
              invocationid="${this.cqAttempt.invocationId}"
              test="${JSON.stringify(test)}"
              predicate="${JSON.stringify(predicate)}"
            ></test-view>
          `)}
        </div>
      </div>
    `;
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
      const testEl = event.target.closest('.test');
      const container = testEl.querySelector("#extra-content-container");
      for (const el of container.querySelectorAll(".extra-content")) {
        el.classList.toggle("visible", el.id == contentId);
      }
      container.classList.add('visible');
    };
  }

  hideExtraContent() {
    this.shadowRoot.getElementById("extra-content-container").classList.remove('visible');
  }

  variantPairSelected() {
    this.requestUpdate();
  }

  toggleAllTests(expanded) {
    return (event) => {
      for (const testView of this.shadowRoot.querySelectorAll('test-view')) {
        testView.expanded = expanded;
      }
    };
  }

  firstUpdated() {
    const selector = '.mdc-button, .mdc-icon-button, .mdc-card__primary-action';
    [].map.call(this.shadowRoot.querySelectorAll(selector), (el) => new MDCRipple(el));

    this._variantFilterChipSet = new MDCChipSet(this.shadowRoot.getElementById("variant-filter"));
    this.requestUpdate();
  }
}

customElements.define('cq-attempt', CQAttempt);
