import {LitElement, html} from '@polymer/lit-element';
//import {state} from 'state.js';

class MonBattle extends LitElement {

  static get properties() {
    return {
    };
  }

  constructor() {
    super();
  }

  render() {
    return html`
      ${this.renderStyle()}
    `
  }

  renderStyle() {
    return html`
      <style>
        :host {
          background: white;
          height: 100vh;
          left: 0;
          position: absolute;
          top: 0;
          width: 100vw;
        }
      </style>
    `
  }
}

customElements.define('mon-battle', MonBattle);
