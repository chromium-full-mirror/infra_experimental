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
      <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">

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
