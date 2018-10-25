import {LitElement, html} from './node_modules/lit-element/lit-element.js';
// import {state} from 'state.js';

class MonDex extends LitElement {

  static get properties() {
    return {
      expanded: {type: Boolean},
    };
  }

  constructor() {
    super();
    this.expanded = false;
  }

  render() {
    return html`<p>hey</p>`
    /*
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
    */
  }
}

customElements.define('mon-dex', MonDex);
