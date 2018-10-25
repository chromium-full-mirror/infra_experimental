import {LitElement, html} from '@polymer/lit-element';
import {MONSTERS} from '../data/monsters.js';
import {arrayChoice, randInt} from './helpers.js';
import './mon-battle.js';
import './mon-dex.js';

class MonGame extends LitElement {
  static get properties() {
    return {
      // Percent chance that you'll see a creature on page load.
      encounterRate: {
        type: Number,
      },
      enemy: {
        type: Object,
      },
    };
  }

  connectedCallback() {
    super.connectedCallback();
    this.encounterRate = this.encounterRate || 100;
    const r = randInt(100);
    if (r < this.encounterRate) {
      // Encounter triggered.
      this.enemy = arrayChoice(MONSTERS);
    }
  }

  endBattle() {
    this.enemy = null;
  }

  render() {
    return html`
      <mon-dex></mon-dex>
      ${ this.enemy &&
        html`<mon-battle .enemy="${this.enemy}" @end-battle="${this.endBattle}"></mon-battle>` }
    `;
  }
}

customElements.define('mon-game', MonGame);
