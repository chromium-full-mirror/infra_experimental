import {LitElement, html} from '@polymer/lit-element';
import {MONSTERS} from '../data/monsters.js';
import './mon-battle.js';
import './mon-dex.js';

class MonGame extends LitElement {
  static get properties() {
    return {
      // Percent chance that you'll see a creature on page load.
      encounterRate: {
        type: Number,
      },
      opponent: {
        type: Object,
      },
    };
  }

  connectedCallback() {
    super.connectedCallback();
    this.encounterRate = this.encounterRate || 100;
    const r = this._randInt(100);
    if (r < this.encounterRate) {
      // Encounter triggered.
      this.opponent = MONSTERS[this._randInt(MONSTERS.length)];
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    // TODO: Save Pokemon to localStorage here.
  }

  endBattle() {
    this.opponent = null;
  }

  _randInt(max) {
    return Math.floor(Math.random() * max);
  }

  render() {
    return html`
      <mon-dex></mon-dex>
      ${ this.opponent &&
        html`<mon-battle .opponent="${this.opponent}" @run="${this.endBattle}"></mon-battle>` }
    `;
  }
}

customElements.define('mon-game', MonGame);
