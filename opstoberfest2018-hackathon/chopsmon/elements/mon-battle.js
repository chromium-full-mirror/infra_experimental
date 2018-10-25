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
      ${this.renderDom()}
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

        #mine {
          filter: contrast(20%);
          left: 10%;
          top: 10%;
          height: 80%;
          position: absolute;
          transform: scaleX(-1);
        }

        #enemy {
          left: 60%;
          top: 10%;
          height: 50%;
          position: absolute;
        }
      </style>
    `
  }

  renderDom() {
    return html`
      <img id="mine" src="/img/lucy.png">
      <img id="enemy" src="/img/lucy.png">
    `
  }
}

customElements.define('mon-battle', MonBattle);
