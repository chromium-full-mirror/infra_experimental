import { MobxLitElement } from '@adobe/lit-mobx';
import { Router } from '@vaadin/router';
import { css, customElement, html } from 'lit-element';

import './components/test-invocation';
import './lib/aug-utils';
import { store } from './store';

@customElement('app-test-results-ui')
export class TestResultsUI extends MobxLitElement {
    private get invocationName() {
        return this.location!.params.invocation_name;
    }

    protected render() {
        if (!store.googleAuth) {
            return html``;
        }

        return html`
        <tr-test-invocation .invocationName=${this.invocationName}></tr-test-invocation>
        `;
    }

    static styles = css`
        :host {
            display: grid;
            color: #212121;
            font-family: "Roboto";
            font-size: 16px;
            letter-spacing: 0.5px;
            height: 100%;
        }
        `;
}

const router = new Router(document.getElementById('app-root'));
router.setRoutes([
    {path: '/invocation/:invocation_name', component: 'app-test-results-ui'}
]);
