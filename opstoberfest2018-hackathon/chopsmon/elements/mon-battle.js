import {LitElement, html} from '@polymer/lit-element';
import {addCapturedMonster, getActiveMonster} from './state.js';
import {randInt} from './helpers.js';
import './mon-health-bar.js';

class MonBattle extends LitElement {

  static get properties() {
    return {
      me: {
        type: Object,
      },
      enemy: {
        type: Object,
      },
      myMaxHealth: {
        type: Number,
      },
      myHealth: {
        type: Number,
      },
      enemyMaxHealth: {
        type: Number,
      },
      enemyHealth: {
        type: Number,
      },
      /* Number of milliseconds for a single turn to animate. */
      turnAnimationLength: {
        type: Number,
      },
    };
  }

  connectedCallback() {
    super.connectedCallback();
    this.enemy = this.enemy || {};
    this.myMaxHealth = 100;
    this.myHealth = this.myMaxHealth;

    this.enemyMaxHealth = 100;
    this.enemyHealth = this.enemyMaxHealth;

    this.turnAnimationLength = 200;

    this.me = getActiveMonster();

    this.battleSetupAnimations();
  }

  battleSetupAnimations() {
    const duration = 500;
    this.ownerDocument.body.style.transition = 'filter 500ms linear';
    const keyFrames = [0, 50, 0, 50, 0];
    keyFrames.forEach((amount, index) => {
      setTimeout(() => {
        this.ownerDocument.body.style.filter = `invert(${amount}%)`;
      }, index * duration);
    })

    setTimeout(() => {
      this.shadowRoot.host.style.visibility = 'visible';
    }, keyFrames.length * (duration - 1));

    setTimeout(() => {
      this.shadowRoot.querySelector('#mine').style.left = '10%';
      this.shadowRoot.querySelector('#enemy').style.left = '60%';
      Array.from(this.shadowRoot.querySelectorAll('mon-health-bar')).forEach(bar =>
        bar.style.visibility = 'visible');
    }, keyFrames.length * duration);

    return new Promise(resolve => setTimeout(resolve, 4 * 500))
  }

  constructor() {
    super();
  }

  attack() {
    // TODO: Replace this with custom numbers per Chopsmon.
    const attackPower = 30;
    const myDamage = randInt(attackPower * 1.5, attackPower * 0.5);

    // Run my turn before the enemy's turn.
    // TODO: Add speed mechanic so this isn't always the same.
    this.enemyHealth -= myDamage;

    if (this.enemyHealth <= 0) {
      // You win! :D
      setTimeout(() => this.dispatchEvent(new CustomEvent('end-battle')),
        this.turnAnimationLength * 1.5);

      // TODO: You win screen, maybe with XP and level up.
    } else {
      setTimeout(this._opponentAttacks.bind(this), this.turnAnimationLength);
    }
  }

  _opponentAttacks() {
    // TODO: Replace this with custom numbers per Chopsmon.
    const attackPower = 30;
    const enemyDamage = randInt(attackPower * 1.5, attackPower * 0.5);
    this.myHealth -= enemyDamage;
    if (this.myHealth <= 0) {
      // You lose. :(
      setTimeout(() => this.dispatchEvent(new CustomEvent('end-battle')),
        this.turnAnimationLength * 1.5);

      // TODO: Some sort of cutesy "you lose" screen that isn't too
      // discouraging.
    }
  }

  capture() {
    // TODO: Add some sort of animation/indication that you captured the
    // Chopsmon.

    // Out of 100.
    const catchRate = 30;
    const r = randInt(100);

    if (r < catchRate) {
      // Enemy caught!
      addCapturedMonster(this.enemy.name);
      setTimeout(() => this.dispatchEvent(new CustomEvent('end-battle')),
        this.turnAnimationLength * 1.5);
    } else {
      this._opponentAttacks();
    }
  }

  run() {
    // TODO: Add running away animation.
    this.dispatchEvent(new CustomEvent('end-battle'));
  }

  render() {
    return html`
      ${this.renderStyle()}
      ${this.renderDom()}
    `
  }

  renderStyle() {
    return html`
      <style>
        @import url('https://fonts.googleapis.com/css?family=Roboto');

        :host {
          visibility: hidden; /* initially hidden */
          background: white;
          font-family: 'Roboto', sans-serif;
          font-size: 40px;
          position: absolute;
          height: 100vh;
          width: 100vw;
          left: 0;
          top: 0;
          z-index: 100;
        }

        #mine {
          filter: contrast(0%);
          left: -50%;
          transition: left 500ms linear;
          /* left: 10%; original */
          top: 20%;
          height: 80%;
          position: absolute;
          transform: scaleX(-1);
        }

        #enemy {
          left: 150%;
          /* left: 60%; original */
          height: 50%;
          position: absolute;
          transition: left 500ms linear;
        }

        #mine-hp {
          left: 50%;
          top: 60%;
          width: 30%;

          position: absolute;
        }

        #enemy-hp {
          left: 20%;
          top: 20%;

          position: absolute;
        }

        #menu {
          background: #e3e9ff;
          display: flex;
          align-items: center;
          justify-content: center;
          position: absolute;
          top: 70%;
          height: 30%;
          width: 100%;
        }

        #question {
          margin: 0;
          text-align: center;
          width: 50%;
        }

        #options {
          display: grid;
          grid-template-columns: auto auto;
          height: 100%;
          width: 50%;
        }

        #options * {
          line-height: 100%;
          height: 100%;
          vertical-align: middle;
          text-align: center;
        }

        .capitalize {
          text-transform: uppercase;
        }

        button {
          background: none;
          font-size: inherit;
          cursor: pointer;
        }

        mon-health-bar {
          visibility: hidden; /* shown after intro */
        }
      </style>
    `
  }

  renderDom() {
    return html`
      <img id="mine" src="/img/${this.me.image}">
      <img id="enemy" src="/img/${this.enemy.image}">

      <mon-health-bar
        id="mine-hp"
        .maxHealth="${this.myMaxHealth}"
        .health="${this.myHealth}"
        .transitionTime="${this.turnAnimationLength}"
      ></mon-health-bar>
      <mon-health-bar
        id="enemy-hp"
        .maxHealth="${this.enemyMaxHealth}"
        .health="${this.enemyHealth}"
        .transitionTime="${this.turnAnimationLength}"
      ></mon-health-bar>

      <div id="menu">
        <div id="question">What will <span class="capitalize">${this.me.name}</span> do?</div>
        <div id="options">
          <button class="capitalize" @click="${this.attack}">Choo choo</button>
          <button class="capitalize" @click="${this.attack}">Tackle</buton>
          <button class="capitalize" @click="${this.capture}">Catch</button>
          <button class="capitalize" @click="${this.run}">Run</button>
        </div>
      </div>
    `
  }
}

customElements.define('mon-battle', MonBattle);
