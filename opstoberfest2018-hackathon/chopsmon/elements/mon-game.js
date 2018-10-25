import {LitElement, html} from '@polymer/lit-element';

class MonGame extends LitElement {
  static get properties() {
    return {
      expanded: {type: Array},
    };
  }

  connectedCallback() {
    // TODO: Load localStorage.
    console.log("connected");
  }

  disconnectedCallback() {
    // TODO: Save Pokemon to localStorage here.
  }

  constructor() {
    super();
    this.expanded = false;
  }

  render() {
    return html`
      <style>
        :host {
          position: fixed;
          right: 0;
          bottom: 0;
          width: 100px;
          height: 100px;
          background: red;
        }
      </style>
    `;
  }
}

customElements.define('mon-game', MonGame);
