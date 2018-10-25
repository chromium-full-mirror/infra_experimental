import {LitElement, html} from '@polymer/lit-element';
//import {state} from 'state.js';

class MonBattle extends LitElement {

  static get properties() {
    return {
      opponent: {
        type: Object,
      },
      yourHealth: {
        type: Number,
      },
      opponentHealth: {
        type: Number,
      },
    };
  }

  connectedCallback() {
    super.connectedCallback();
    this.opponent = this.opponent || {};
    this.yourHealth = 100;
    this.opponentHealth = 100;
  }

  constructor() {
    super();
  }

  attack() {
    // TODO: Implement logic to handle an attack.
  }

  capture() {
    // TODO: Implement logic to catch Chopsmon.
  }

  run() {
    this.dispatchEvent(new CustomEvent('run'));
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
        @import url('https://fonts.googleapis.com/css?family=Roboto');

        :host {
          background: white;
          font-family: 'Roboto', sans-serif;
          font-size: 40px;
          position: absolute;
          height: 100vh;
          width: 100vw;
          left: 0;
          top: 0;
        }

        #mine {
          filter: contrast(0%);
          left: 10%;
          top: 20%;
          height: 80%;
          position: absolute;
          transform: scaleX(-1);
        }

        #enemy {
          left: 60%;
          height: 50%;
          position: absolute;
        }

        #mine-hp {
          left: 50%;
          top: 60%;
          width: 30%;
          height: 5%;
          border: solid 5px #333333;
          position: absolute;
        }

        #enemy-hp {
          left: 20%;
          top: 20%;
          width: 30%;
          height: 5%;

          border:solid 5px #333333;
          position: absolute;
        }

        #menu {
          background: #e3e9ff;
          display: flex;
          align-items: center;
          justify-content: center;
          position: absolute;
          top: 70%;
          height: 30%;
          width: 100%;
        }

        #question {
          margin: 0;
          text-align: center;
          width: 50%;
        }

        #options {
          display: grid;
          grid-template-columns: auto auto;
          height: 100%;
          width: 50%;
        }

        #options * {
          line-height: 100%;
          height: 100%;
          vertical-align: middle;
          text-align: center;
        }

        .capitalize {
          text-transform: uppercase;
        }

        button {
          background: none;
          font-size: inherit;
          cursor: pointer;
        }
      </style>
    `
  }

  renderDom() {
    return html`
      <img id="mine" src="/img/monorail1.png">
      <img id="enemy" src="/img/${this.opponent.image}">

      <div id="mine-hp"></div>
      <div id="enemy-hp"></div>

      <div id="menu">
        <div id="question">What will <span class="capitalize">Monorail</span> do?</div>
        <div id="options">
          <button class="capitalize" @click="${this.attack}">Choo choo</button>
          <button class="capitalize" @click="${this.attack}">Tackle</buton>
          <button class="capitalize" @click="${this.capture}">Catch</button>
          <button class="capitalize" @click="${this.run}">Run</button>
        </div>
      </div>
    `
  }
}

customElements.define('mon-battle', MonBattle);
