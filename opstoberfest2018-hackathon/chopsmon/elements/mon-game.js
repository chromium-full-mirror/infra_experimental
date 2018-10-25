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
      <mon-battle></mon-battle>
      <mon-dex></mon-dex>
    `;
  }
}

customElements.define('mon-game', MonGame);
