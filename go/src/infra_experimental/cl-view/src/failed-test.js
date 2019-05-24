// Import LitElement base class and html helper function
import { LitElement, html } from 'lit-element';
import {MDCChipSet} from '@material/chips';
import './test-name';

export class FailedTest extends LitElement {
  static get properties() {
    return {
      failedTest: { type: Object },
    };
  }

  /**
   * Define a template for the new element by implementing LitElement's
   * `render` function. `render` must return a lit-html TemplateResult.
   */
  render() {
    if (!this.failedTest) {
      return html`not initialized`;
    }

    return html`
      <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
      <link href="https://unpkg.com/material-components-web@latest/dist/material-components-web.min.css" rel="stylesheet">

      <style>
        .variant {
          border-radius: 5px;
          border-style: solid;
          padding: 3px;
          border-color: lightgray;
          background: #f1f1f1;
          font-family: monospace;
          margin-right: 4px;
        }
        test-name {
          font-size: larger;
        }
      </style>


      <div class="mdc-chip-set mdc-chip-set--filter">
        <div class="mdc-chip">
          <div class="mdc-chip__checkmark" >
            <svg class="mdc-chip__checkmark-svg" viewBox="-2 -3 30 30">
              <path class="mdc-chip__checkmark-path" fill="none" stroke="black"
                    d="M1.73,12.91 8.1,19.28 22.79,4.59"/>
            </svg>
          </div>
          <div class="mdc-chip__text">os:linux site_per_process:true</div>
        </div>

        <div class="mdc-chip">
          <div class="mdc-chip__checkmark" >
            <svg class="mdc-chip__checkmark-svg" viewBox="-2 -3 30 30">
              <path class="mdc-chip__checkmark-path" fill="none" stroke="black"
                    d="M1.73,12.91 8.1,19.28 22.79,4.59"/>
            </svg>
          </div>
          <div class="mdc-chip__text">os:win site_per_process:true</div>
        </div>
      </div>
      <button @click=${this.expandAll} class="foo-button mdc-button">expand all</button>
      <button @click=${this.collapseAll} class="foo-button mdc-button">collapse all</button>
      <ul id="test-runs" class="list-group">
      <li class="test-run d-none list-group-item list-group-item-danger" data-variant-hash="deafbeef">
      failure
      <pre>1 != 2</pre>
    </li>
    <li class="test-run d-none list-group-item list-group-item-danger" data-variant-hash="deafbeef">
    failure
    <pre>1 != 2</pre>
  </li>
  <li class="test-run d-none list-group-item list-group-item-danger" data-variant-hash="deafbeef">
  failure
  <pre>1 != 2</pre>
</li>
<li class="test-run d-none list-group-item list-group-item-danger" data-variant-hash="deafbeef">
failure
<pre>1 != 2</pre>
</li>
</ul>
      `;
  }

  expandAll(event) {
    for (let t of this.shadowRoot.querySelectorAll(".test-run")) {
      t.classList.remove("d-none");
    }
  }
  collapseAll(event) {
    for (let t of this.shadowRoot.querySelectorAll(".test-run")) {
      t.classList.add("d-none");
    }
  }

  updated() {
    const chipSetEl = this.shadowRoot.querySelector('.mdc-chip-set');
    new MDCChipSet(chipSetEl);
  }
}
// Register the element with the browser
customElements.define('failed-test', FailedTest);
