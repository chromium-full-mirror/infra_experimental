import {LitElement, html} from '@polymer/lit-element'
import {getOwnedMonsters} from './state.js';

class MonDex extends LitElement {

  static get properties() {
    return {
      expanded: {type: Boolean},
    };
  }

  constructor() {
    super();
    this.expanded = true;
  }

  render() {
    const monsters = getOwnedMonsters();
    const monsterEls = monsters.map(monster => html`
      <div>${monster.name}</div>
    `);

    if (this.expanded) {
      return html`
        <style></style>
        <div>
          ${monsterEls}
        </div>
      `;
    } else {
      return html`
        <style></style>
        <div>
          not expanded
        </div>
      `;
    }
  }
}

customElements.define('mon-dex', MonDex);
