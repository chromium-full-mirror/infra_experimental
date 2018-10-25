import {LitElement, html} from '@polymer/lit-element';
import './mon-battle.js';
import './mon-dex.js';

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
        img {
          max-width: 100%;
          max-height: 100%;
        }
        .dex-button {
          position: fixed;
          right: 0;
          bottom: 0;
          width: 200px;
          height: 200px;
          cursor: pointer;
          background: none;
          background-image: url('/img/lucy.png');
          background-size: 100%;
          border: none;
          transition: transform;
        }
        .dex-button:hover {
          background-image: url('/img/lucy_chromium1.png');
        }
        .dex-button:active {
          transform: translateY(10px);
        }
      </style>
      <mon-battle></mon-battle>
      <button class="dex-button"></button>
      <mon-dex></mon-dex>
    `;
  }
}

customElements.define('mon-game', MonGame);
