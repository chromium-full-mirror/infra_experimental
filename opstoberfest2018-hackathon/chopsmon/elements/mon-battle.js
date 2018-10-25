import {LitElement, html} from '@polymer/lit-element';
import {addCapturedMonster, getActiveMonster} from './state.js';
import {randInt, arrayChoice, sleep} from './helpers.js';
import './mon-health-bar.js';

const MOVES = {
  bite: (me, enemy) => {
    console.log('bite');
    const attackPower = (me.attack / 10.0) * 10;
    const enemyDamage = randInt(attackPower * 1.5, attackPower * 0.5);
    enemy.health -= enemyDamage;
  },
  sting: (me, enemy) => {
    console.log('sting');
    const attackPower = (me.attack / 10.0) * 10;
    const enemyDamage = randInt(attackPower * 1.5, attackPower * 0.5);
    enemy.health -= enemyDamage;
  },
  tackle: (me, enemy) => {
    console.log('tackle');
    const attackPower = (me.attack / 10.0) * 10;
    const enemyDamage = randInt(attackPower * 1.5, attackPower * 0.5);
    enemy.health -= enemyDamage;
  },
  tornado: (me, enemy) => {
    // Make fancy
    console.log('tornado');
    const attackPower = (me.attack / 10.0) * 10;
    const enemyDamage = randInt(attackPower * 1.5, attackPower * 0.5);
    enemy.health -= enemyDamage;
  },
  file_bug: (me, enemy) => {
    // Make fancy
    console.log('tornado');
    const attackPower = (me.attack / 10.0) * 10;
    const enemyDamage = randInt(attackPower * 1.5, attackPower * 0.5);
    enemy.health -= enemyDamage;
  },
};

class MonBattle extends LitElement {

  static get properties() {
    return {
      battleState: {
        type: String,
      },
      me: {
        type: Object,
      },
      enemy: {
        type: Object,
      },
      myTurnRunning: {
        type: Boolean,
      },
      enemyTurnRunning: {
        type: Boolean,
      },
      ballCapturing:  {
        type: Boolean,
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
      captureAnimationLength: {
        type: Number,
      },
      /* Number of milliseconds for a single turn to animate. */
      turnAnimationLength: {
        type: Number,
      },
      /* Number of milliseconds to wait after a turn completes. */
      turnDelayLength: {
        type: Number,
      },
      isPlayerTurn: {
        type: Boolean,
      },
      setupDone: {
        type: Boolean,
      },
      playerMove: {
        type: String,
      },
      enemyMove: {
        type: String,
      },
    };
  }

  connectedCallback() {
    super.connectedCallback();

    this.battleState = 'intro';
    this.enemy = this.enemy || {};

    this.turnAnimationLength = 200;
    this.turnDelayLength = 1000;

    this.captureAnimationLength = 1000;
    this.messageLength = 1500;

    this.me = getActiveMonster();
    // Make players win on average more
    this.me.attack = 15;

    this.battleSetupAnimations();
    this.isPlayerTurn = true;
  }

  battleSetupAnimations() {
    const duration = 400;
    this.ownerDocument.body.style.backgroundColor = 'black';
    this.ownerDocument.body.style.transition = 'opacity 400ms ease';
    const keyFrames = [1, 0.4, 1, 0.4, 1, 0.4, 1];
    keyFrames.forEach((amount, index) => {
      setTimeout(() => {
        this.ownerDocument.body.style.opacity = amount;
      }, index * duration);
    })

    setTimeout(() => {
      this.shadowRoot.host.style.visibility = 'visible';
    }, keyFrames.length * (duration));

    setTimeout(() => {
      this.shadowRoot.querySelector('#mine').style.left = '10%';
      this.shadowRoot.querySelector('#enemy').style.left = '60%';
      Array.from(this.shadowRoot.querySelectorAll('mon-health-bar')).forEach(bar =>
        bar.style.visibility = 'visible');
      sleep(this.turnDelayLength*2).then(() => {
        this.setupDone = true;
      });
    }, (keyFrames.length + 1) * duration);

    setTimeout(() => {
      this.battleState = 'battle';
    }, (keyFrames.length + 1) * duration + messageLength);
  }

  constructor() {
    super();
  }

  move(move) {
    if (move === "catch") {
      this.capture();
      return;
    }
    if (move === "run") {
      this.run();
      return;
    }
    this.playerMove = move;
    this.myTurnRunning = true;
    this.isPlayerTurn = false;
    console.log(this.isPlayerTurn);
    console.log('me attacking');
    (MOVES[move] || MOVES["tackle"])(this.me, this.enemy);

    console.log('before sleep');
    sleep(this.turnAnimationLength).then(() => {
      if (this.enemy.health <= 0) {
        // You win! :D
        sleep(this.turnDelayLength).then(() => {
          this.battleState = 'win';
          this.end();
        });
        // TODO: You win screen, maybe with XP and level up.
      } else {
        sleep(this.turnDelayLength).then(() => {
          this.myTurnRunning = false;
          this._opponentAttacks();
        });
      }
    });
  }

  _opponentAttacks() {
    // TODO: Replace this with custom numbers per Chopsmon.
    let move = arrayChoice(this.enemy.moves);
    this.enemyMove = move;
    this.enemyTurnRunning = true;
    console.log('enemy attacking');
    (MOVES[move] || MOVES["tackle"])(this.enemy, this.me);

    sleep(this.turnAnimationLength).then(() => {
      sleep(this.turnDelayLength).then(() => {
        this.enemyTurnRunning = false;
        this.isPlayerTurn = true;
      });
      if (this.me.health <= 0) {
        // TODO: Some sort of cutesy "you lose" screen that isn't too
        // discouraging.
        console.log('you lose!');
        sleep(this.turnDelayLength).then(() => {
          this.battleState = 'lose';
          this.end();
        });
      }
    });
  }

  captureEnd() {
    // TODO: Add some sort of animation/indication that you captured the
    // Chopsmon.

    // Out of 100.
    const catchRate = 30;
    const r = randInt(100);

    if (r < catchRate) {
      // Enemy caught!
      addCapturedMonster(this.enemy.name);
      this.battleState = 'catch';
      this.end();
    } else {
      this._opponentAttacks();
    }
  }

  capture() {
    console.log('capture');
    this.ballCapturing = true;
    this.shadowRoot.querySelector('#ball').style.visibility = 'visible';

    console.log('capture2');

    setTimeout(() => {
      console.log('timeout');
      this.ballCapturing = false;
      this.captureEnd();
      this.shadowRoot.querySelector('#ball').style.visibility = 'hidden';
    }, this.captureAnimationLength);
  }

  run() {
    // TODO: Add running away animation.
    this.battleState = 'run';
    this.end();
  }

  end() {
    setTimeout(() => this.dispatchEvent(new CustomEvent('end-battle')), messageLength);
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

        @keyframes attack-left {
          0% {
            transform: translateX(0);
          }
          50% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(0);
          }
        }

        .attack-left {
          animation: attack-left 0.2s;
        }

        :host {
          visibility: hidden; /* initially hidden */
          background: white;
          font-family: 'Roboto', sans-serif;
          font-size: 40px;
          position: fixed;
          height: 100vh;
          width: 100vw;
          left: 0;
          top: 0;
          z-index: 100;
        }

        img {
          max-width: 100%;
          max-height: 100%;
        }

        #mine {
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

        #dialog {
          background: #e3e9ff;
          display: flex;
          align-items: center;
          justify-content: center;
          position: absolute;
          top: 70%;
          height: 30%;
          width: 100%;
        }

        #ball {
          height: 20%;
          position: absolute;
          visibility: hidden;
        }

        @keyframes capture {
          0% {
            top: 60%;
            left: 30%;
          }

          100% {
            top: 15%;
            left: 65%;
          }
        }

        #ball.ball-animation {
          animation: capture ${this.captureAnimationLength}ms;
          visibility: visible;
        }

        #prompt {
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

  renderDialog() {
    switch (this.battleState) {
      case 'intro':
        return html`
          <div id="prompt">
            A wild <span class="capitalize">${this.enemy.name}</span> appeared!
          </div>`;
      case 'battle':
        let moves = this.me.moves.slice();
        moves.push('catch');
        moves.push('run');
        let moveDisplay = (move) => move.replace('_', ' ');
        let movesStr = moves.map(move => html`
            <button class="capitalize" @click="${() => this.move(move)}">${moveDisplay(move)}</button>`);

        let message = '';
        if (this.isPlayerTurn) {
          message = html`What will <span class="capitalize">${this.me.name}</span> do?`
        }
        else if (this.myTurnRunning) {
          message = html`<span class="capitalize">${this.me.name}</span> uses <span class="capitalize">${moveDisplay(this.playerMove)}</span>`;
        }
        else if (this.enemyTurnRunning) {
          message = html`<span class="capitalize">${this.enemy.name}</span> uses <span class="capitalize">${moveDisplay(this.enemyMove)}</span>`;
        }

        return html`
          <div id="prompt">
            ${message}
          </div>
          <div id="options">${movesStr}</div>
        `;
      case 'catch':
        return html`
          <div id="prompt">
            Gotcha! <span class="capitalize">${this.enemy.name}</span> was caught!
          </div>`;
      case 'win':
        return html`
          <div id="prompt">
            Wild <span class="capitalize">${this.enemy.name}</span> fainted!
          </div>`;
      case 'lose':
        return html`
          <div id="prompt">
            Wild <span class="capitalize">${this.enemy.name}</span> fled!
          </div>`;
      case 'run':
        return html`<div id="prompt">Got away safely!</div>`;
    }
  }

  renderDom() {

    return html`
      <div id="mine">
        <img src="/img/${this.me.image}" class="${this.myTurnRunning ? 'attack-left' : ''}" />
      </div>
      <div id="enemy">
        <img src="/img/${this.enemy.image}" class="${this.enemyTurnRunning ? 'attack-left' : ''}" />
      </div>

      <mon-health-bar
        id="mine-hp"
        .maxHealth="${this.me.maxHealth}"
        .health="${this.me.health}"
        .transitionTime="${this.turnAnimationLength}"
      ></mon-health-bar>
      <mon-health-bar
        id="enemy-hp"
        .maxHealth="${this.enemy.maxHealth}"
        .health="${this.enemy.health}"
        .transitionTime="${this.turnAnimationLength}"
      ></mon-health-bar>

      <div id="dialog">
        ${this.renderDialog()}
      </div>
      <img id="ball" src="/img/ball.png" class="${this.ballCapturing ? 'ball-animation' : ''}" />
    `
  }
}

customElements.define('mon-battle', MonBattle);
