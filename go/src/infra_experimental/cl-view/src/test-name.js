// Import LitElement base class and html helper function
import { LitElement, html } from 'lit-element';

export class TestName extends LitElement {
  static get properties() {
    return {
      testName: { type: String },
    };
  }

  render() {
    return html`
      <link href="/node_modules/material-components-web/dist/material-components-web.min.css"  rel="stylesheet">

      <style>
        .component:not(:last-child)::after {
          content: ">";
          margin-left: 0.5em;
        }
        /**
        :host {
          border-radius: 5px;
          border-style: solid;
          padding: 3px;
          padding-right: 0;
          border-color: lightgray;
          background: #f1f1f1;
          font-family: monospace;
          margin-right: 4px;
          display: inline;
        }*/
      </style>

      ${(this.testName || '').split('|').map(c => html`
        <span class="component">${c}</span>
      `)}
    `;
  }
}

customElements.define('test-name', TestName);
