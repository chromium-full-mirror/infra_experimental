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
        this.requestUpdate();
      },
    })
  }

  render() {
    const variantPredicate = new Set((this.predicate || {}).variants || []);

    const variants = Object.values(this.test.test.variants)
      .filter((v) => v.def.some((p) => variantPredicate.has(p)));

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
        .test-body {
          margin-left: 20px;
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

        .test-header {
          cursor: pointer;
        }
        .test-container {
          margin: 5px;
        }
        .variant-pair {
          font-family: monospace;
        }
        .extra-content-container {
          display: flex;
          flex-direction: column;
          min-width: 400px;
          margin-left: 20px;
          margin-top: 10px;
        }
        .extra-content-container:not(.visible), .extra-content:not(.visible) {
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
        .variant-def {
          display: flex;
          align-items: center;
        }
        .variant-container {
          border: solid 1px lightgrey;
          border-radius: 10px;
          margin-bottom: 2px;
          padding: 5px 10px;
        }
        .separator:not(:last-child) {
          border-bottom: solid 1px lightgrey;
        }
        .run-grid {
          padding: 0;
        }
        .run-container-header {
          align-items: center;
        }
        .run-container-header.pass {
          background: #8d4;
        }
        .run-container-header.fail {
          background: #e88;
        }
        .run-container-header.crash {
          background: #c6c;
          color: white;
          font-weight: bold;
        }
        .log-container {
          display: flex;
        }
        .log-button {
          margin: 4px;
          cursor: pointer;
        }
        .log-button:not(:last-child) {
          border-right: solid 1px darkgrey;
          padding-right: 5px;
        }
        .crash .log-button {
          border-color: lightgrey;
        }
      </style>

      <div class="test-container ${this.loaded ? "loaded" : ""} ${this.expanded ? "expanded" : ""}">
        <div class="test-header mdc-layout-grid title-grid" @click=${this.onClick.bind(this)}>
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

        <div class="test-body">
          ${variants.map((variant) => html`
            <div class="variant-container">
              <div class="variant-def">
                Variant:
                <div class="mdc-chip-set">
                  ${variant.def.sort().map((p) => html`
                    <div class="mdc-chip">
                      <div class="mdc-chip__text variant-pair">${p}</div>
                    </div>
                  `)}
                </div>
              </div>
              <div class="mdc-layout-grid run-grid">
                <div class="mdc-layout-grid__inner">
                  <div class="mdc-layout-grid__cell">STATUS</div>
                  <div class="mdc-layout-grid__cell">SUMMARY</div>
                  <div class="mdc-layout-grid__cell">LOGS & ARTIFACTS</div>
                </div>
                ${variant.runs.map((run, i) => html`
                  <div class="run-container">
                    <div class="mdc-layout-grid__inner run-container-header ${run.status.toLowerCase()}">
                      <div class="mdc-layout-grid__cell">${run.status}</div>
                      <div class="mdc-layout-grid__cell">Assertion failed</div>
                      <div class="mdc-layout-grid__cell log-container">
                        <div class="log-button" @click=${this.extraContentHandler(`extra-content-container-${i}`, "1").bind(this)}>Log 1</div>
                        <div class="log-button" @click=${this.extraContentHandler(`extra-content-container-${i}`, "2").bind(this)}>Log 2</div>
                        <div class="log-button" @click=${this.extraContentHandler(`extra-content-container-${i}`, "3").bind(this)}>Screenshot</div>
                      </div>
                    </div>
                    <div id="extra-content-container-${i}" class="mdc-layout-grid__inner extra-content-container">
                      <div class="mdc-layout-grid__cell">
                        <div class="extra-content" data-content-id="1">
                          <textarea readonly>Stack trace goes here....</textarea>
                        </div>
                        <div class="extra-content" data-content-id="2">
                        <textarea readonly>Another log....</textarea>
                        </div>
                        <div class="extra-content" data-content-id="3">
                          <img style="width:300px" src="https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/1200px-Cat03.jpg"></img>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="separator"></div>
                `)}
              </div>
            </div>
          `)}
        </div>
      </div>
    `;
  }

  extraContentHandler(containerId, contentId) {
    return (event) => {
      const container = event.target.closest(".run-container").querySelector(".extra-content-container");
      for (const el of container.querySelectorAll(".extra-content")) {
        el.classList.toggle("visible", el.getAttribute("data-content-id") == contentId);
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
    const tests = {};
    if (this.cqAttempt) {
      // Collect unique variant pairs.
      for (const testName in this.cqAttempt.tests) {
        const test = this.cqAttempt.tests[testName];
        let match = false;
        for (const variant of Object.values(test.variants)) {
          for (const pair of variant.def) {
            variantPairs.add(pair);
            match = match || variantPredicate.has(pair);
          }
        }
        if (match) {
          tests[testName] = test;
        }
      }
    }

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
        .variant-chip-set {
          display: inline;
        }
        .test-container {
          margin: 5px;
        }

        .variant-pair {
          font-family: monospace;
        }
        .extra-content-container:not(.visible), .extra-content:not(.visible) {
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
        .loaded .loading-progress {
          display: none;
        }
        .test-view-container {
          border: solid 1px lightgrey;
          border-radius: 10px;
          margin-bottom: 2px;
        }
      </style>

      <div>
        <h3>Stats<h3>
        <div>Tests: ${this.stats ? this.stats.totalTests : "counting..."}</div>
        <div>Test variants: ${this.stats ? this.stats.totalVariants : "counting..."}</div>
        <div>Test runs: ${this.stats ? this.stats.totalTestRuns : "counting..."}</div>
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
        ${Object.keys(tests).sort().map(testName => html`
          <div class="test-view-container">
            <test-view
              invocationid="${this.cqAttempt.invocationId}"
              test="${JSON.stringify({testName, test: tests[testName]})}"
              predicate="${JSON.stringify(predicate)}"
            ></test-view>
          <div>
        `)}
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

  async updated() {
    if (!this.cqAttempt || (this.statsRequest && this.statsRequest.invocationId == this.cqAttempt.invocationId)) {
      return;
    }
    this.statsRequest = {
      invocationId: this.cqAttempt.invocationId,
      promise: fetch('/rpc/stats', {
        method: 'POST',
        body: JSON.stringify({
          invocationId: this.cqAttempt.invocationId,
        })
      })
    };

    const res = await this.statsRequest.promise;
    this.stats = await res.json();
    this.requestUpdate();
  }
}

customElements.define('cq-attempt', CQAttempt);
