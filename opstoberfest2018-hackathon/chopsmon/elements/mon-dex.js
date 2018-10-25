import {LitElement, html} from '@polymer/lit-element'
import {MONSTERS} from '../data/monsters.js';
import {getOwnedMonsterNames, getActiveMonster, setActiveMonster} from './state.js';

class MonDex extends LitElement {
  static get properties() {
    return {
      expanded: {
        type: Boolean,
      },
      activeMonster: {
        type: Object,
      },
    };
  }

  constructor() {
    super();
    this.activeMonster = getActiveMonster();
  }

  toggle() {
    this.expanded = !this.expanded;
  }

  render() {
    // .dex_list.bottom is set to prevent the expanded dex list from overlapping with the dex button
    // Hacky? No idea how it will work if we add more mons than fit on screen
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
        background-image: url('/img/${this.activeMonster.image}');
        background-size: 120%;
        background-position: center;
        border: none;
        transition: transform;
      }
      .dex-button:active {
        transform: translateY(10px);
      }
      .dex-list {
        box-sizing: border-box;
        position: fixed;
        padding: 1em 16px 150px 1em;
        right: 0;
        bottom: 0;
        height: 100%;
        width: 150px;
        background: white;
        border-left: #ddd 1px solid;
        overflow: auto;
      }
      .caught {
        cursor: pointer;
        transition: background 0.2s;
      }
      .caught:hover {
        background: #eee;
      }
      .uncaught {
        filter: contrast(0) brightness(40%);
      }
    </style>
    ${this.expanded ? this.renderDexList() : ''}
    <button class="dex-button" @click="${this.toggle}"></button>
    `;
  }

  renderDexList() {
    const ownedMonsters = getOwnedMonsterNames();
    const monsterEls = MONSTERS.map(monster => {
      const caught = ownedMonsters.includes(monster.name);
      return html`
        <div>
          <img
            src="/img/${monster.image}"
            class="${ caught ? 'caught' : 'uncaught' }"
            @click="${ () => {
              if (caught) {
                this.activeMonster = monster;
                setActiveMonster(monster.name);
              }
            } }"
          />
          <h3>
            ${ caught ? monster.name : '???' }
          </h3>
        </div>
        `
      }
    );
    return html`
      <div class="dex-list">
        <h2>
          Your ChopsMons!
        </h2>
        ${monsterEls}
      </div>`;
  }
}

customElements.define('mon-dex', MonDex);
