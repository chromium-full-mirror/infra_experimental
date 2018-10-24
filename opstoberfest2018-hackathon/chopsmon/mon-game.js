import {LitElement, html} from '/node_modules/@polymer/lit-element';
import {state} from 'state.js';

class MonoDex extends LitElement {

  static get properties() {
    return {
      expanded: {type: Array},
    };
  }

  constructor() {
    super();
    this.expanded = false;
  }

  render() {
    const monsters = state.getOwnedMonsters();
    const monsterEls = monsters.map(monster => html`
      <div>{monster}</div>
    `);

    if (expanded) {
      return html`
        <style></style>
        <div>
          {monsterEls}
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

customElements.define('mon-dex', MyElement);
