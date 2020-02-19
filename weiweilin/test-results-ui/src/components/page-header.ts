import { MobxLitElement } from '@adobe/lit-mobx';
import { css, customElement, html } from 'lit-element';
import { store } from '../store';

@customElement('tr-page-header')
export class PageHeaderElement extends MobxLitElement {
    protected render() {
        return html`
        <img style="display: inline-block; width: 50px; vertical-align: middle;" src="/assets/chromium-icon.png"/>
        <span style="font-size: 32px; vertical-align: middle;">LUCI Test Results</span>
        <div style="float: right; padding: 5px; color: blue; text-decoration: underline;">
        ${store.isSignedIn ?
            html`<a @click=${() => store.googleAuth!.signOut()}>Sign Out</a>` :
            html`<a @click=${() => store.googleAuth!.signIn({prompt: 'consent'})}>Sign In</a>`}
        </div>
        `;
    }

    static styles = css`
        :host {
            padding-left: 5px;
        }
        `;
}
