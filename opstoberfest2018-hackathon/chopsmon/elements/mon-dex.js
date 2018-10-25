import {LitElement, html} from '@polymer/lit-element'
import {getOwnedMonsters} from './state.js';

class MonDex extends LitElement {

  static get properties() {
    return {
      expanded: {
        type: Boolean,
        value: false,
      },
    };
  }

  toggle() {
    this.expanded = !this.expanded;
  }

  render() {
    return html`<style>
      img {
        max-width: 100%;
        max-height: 100%;
      }
      .dex-button {
        position: fixed;
        right: 0;
        bottom: 0;
        width: 150px;
        height: 150px;
        cursor: pointer;
        background: none;
        background-image: url('/img/lucy.png');
        background-size: 120%;
        background-position: center;
        border: none;
        transition: transform;
      }
      .dex-button:hover {
        background-image: url('/img/lucy_chromium1.png');
      }
      .dex-button:active {
        transform: translateY(10px);
      }
      .dex-list {
        box-sizing: border-box;
        position: fixed;
        padding: 1em 16px;
        right: 0;
        bottom: 0;
        height: 100%;
        width: 300px;
        background: white;
        border-left: #ddd 1px solid;
      }
    </style>
    ${this.expanded && this.renderDexList()}
    <button class="dex-button" @click=${this.toggle}></button>`;
  }

  renderDexList() {
    const monsters = getOwnedMonsters();
    const monsterEls = monsters.map(monster => html`
      <div>
        <img src="/img/${monster.image}" />
        <h3>
          ${monster.name}
        </h3>
      </div>
    `);
    return html`
      <div class="dex-list">
        <h2>
          Your Chopsmons!
        </h2>
        ${monsterEls}
      </div>`;
  }
}

customElements.define('mon-dex', MonDex);
