import {LitElement, html} from '@polymer/lit-element';

class MonHealthBar extends LitElement {
  static get properties() {
    return {
      // Percent chance that you'll see a creature on page load.
      maxHealth: {
        type: Number,
      },
      health: {
        type: Number,
      },
      transitionTime: {
        type: Number,
      },
    };
  }

  connectedCallback() {
    super.connectedCallback();
    this.transitionTime = this.transitionTime || 200;
  }

  render() {
    const percentage = Math.max(this.health / this.maxHealth * 100, 0);
    return html`
      <style>
        :host {
          height: 40px;
          width: 100%;
          max-width: 100%;
          border: solid 5px #333333;
          background: #eee;
        }
        .fill {
          height: 100%;
          max-width: 100%;
          background: #00E676;
        }
      </style>
      <div class="fill" style="width: ${percentage}%; transition: width ${this.transitionTime}ms;"></div>
    `;
  }
}

customElements.define('mon-health-bar', MonHealthBar);
