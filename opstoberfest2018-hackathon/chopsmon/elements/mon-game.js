import {LitElement, html} from '@polymer/lit-element';
import './mon-battle.js';
import './mon-dex.js';

class MonGame extends LitElement {
  connectedCallback() {
    super.connectedCallback();
    // TODO: Load localStorage.
    console.log("connected");
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    // TODO: Save Pokemon to localStorage here.
  }

  render() {
    return html`
      <mon-dex></mon-dex>
      <mon-battle></mon-battle>
    `;
  }
}

customElements.define('mon-game', MonGame);
