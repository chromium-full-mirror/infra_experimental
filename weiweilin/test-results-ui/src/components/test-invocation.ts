import { MobxLitElement } from '@adobe/lit-mobx';
import { html, css, customElement } from 'lit-element';
import { computed, observable, IObservableValue } from 'mobx';
import { repeat } from 'lit-html/directives/repeat';
import { classMap } from 'lit-html/directives/class-map';
import '@material/mwc-icon';
import '@material/mwc-icon-button';
import '@material/mwc-button';
import * as _ from 'lodash';

import { TestResult, Invocation, TestExoneration, InvocationState } from '../types/resultdb';
import { TestFilterMapFn } from './test-output-filters';
import { store } from '../store';
import './test-invocation-details';
import './test-output-filters';
import './test-entry';
import '../lib/components/paginator';
import './test-nav-tree';
import '../lib/aug-utils/array-utils';
import './page-header';
import moment from 'moment';
import { TestInvocation } from '../view-models/test-invocation';
import { TestEntryElement } from './test-entry';
import { TestNavTreeNode } from '../view-models/test-nav-tree';

const INVOCATION_STATE_DISPLAY_MAP = {
    [InvocationState.Unspecified]: 'unspecified',
    [InvocationState.Active]: 'active',
    [InvocationState.Finalizing]: 'finalizing',
    [InvocationState.Finalized]: 'finalized',
};

const INVOCATION_STATE_CLASS_MAP = {
    [InvocationState.Unspecified]: 'unspecified',
    [InvocationState.Active]: 'active',
    [InvocationState.Finalizing]: 'finalizing',
    [InvocationState.Finalized]: 'finalized',
};

@customElement('tr-test-invocation')
export class TestInvocationElement extends MobxLitElement {
    @observable.ref
    private invocationName: string = "";

    @observable.ref
    private timestamp: number = Date.now();

    @observable.ref
    private filterMapFn: TestFilterMapFn = () => undefined;

    @observable.ref
    private menuExpanded: boolean = false;
    @observable.ref
    private selectedTestIds: string[] = [];

    @computed
    private get testNavTreeNode() {
        return new TestNavTreeNode(null, '', this.filteredTestIds);
    }

    @computed
    private get testInvocation(): TestInvocation | null {
        if (!store.resultDbPrpcClient) {
            return null;
        }
        // artificially depends on the timestamp
        // so the API call can be treated as a pure function of f(timestamp, request)
        this.timestamp;
        return new TestInvocation(this.invocationName, store.resultDbPrpcClient);
    }

    @computed
    private get resultStats() {
        const expected = this.testInvocation?.testResults.filter((result) => result.expected).length || 0;
        return {
            expected,
            unexpected: (this.testInvocation?.testResults.length || 0) - expected,
            exonerated: this.testInvocation?.testExonerations.length || 0,
        }
    }

    @computed
    private get filteredTests() {
        const tests = this.testInvocation?.tests || [];
        return tests.filterMap(this.filterMapFn);
    }

    @computed
    private get filteredTestIds() {
        return this.filteredTests.map(({id}) => id);
    }

    @computed
    private get selectedTests() {
        if (this.testNavTreeNode.selectedTestIds.length === 0) {
            return this.filteredTests;
        }
        return this.filteredTests.filter(({id}) => this.testNavTreeNode.selectedTestIds.indexOf(id) !== -1);
    }

    @computed
    private get testIdCommonPrefix() {
        const tests = this.testInvocation?.tests;
        if (!tests || tests.length === 1) {
            return '';
        }

        const testIds = tests.map((t) => t.id);
        let commonPrefix = testIds[0] || '';
        for (const testId of testIds) {
            if (testId.startsWith(commonPrefix)) {
                continue;
            }
            let nextCommonLength = 0;
            for (let i = 0; i < commonPrefix.length; ++i) {
                if (testId[i] !== commonPrefix[i]) {
                    break;
                }
                if (!/\w|-/.test(testId[i])) {
                    nextCommonLength = i + 1;
                }
            }
            commonPrefix = testId.slice(0, nextCommonLength);
        }
        return commonPrefix;
    }


    private renderInvocationState() {
        const invocation = this.testInvocation!.invocation!;
        if (invocation.finalizeTime) {
            return html`
            <i>${INVOCATION_STATE_DISPLAY_MAP[invocation.state]}</i>
            at ${moment(invocation.finalizeTime).format('YYYY-MM-DD HH:mm:ss')}
            `
        }

        return html`
        <i>${INVOCATION_STATE_DISPLAY_MAP[invocation.state]}</i>
        since ${moment(invocation.createTime).format('YYYY-MM-DD HH:mm:ss')}
        `
    }

    private toggleAllTests(expand: boolean) {
        this.shadowRoot!.querySelectorAll("tr-test-entry").forEach((e) => (e as TestEntryElement).expanded = expand);
    }

    protected render() {
        const invocation = this.testInvocation?.invocation;
        if (!invocation) {
            return html`
            <tr-page-header></tr-page-header>
            <div>Please Sign In</div>
            `;
        }

        return html`
        <tr-page-header></tr-page-header>
        <div id="test-invocation-summary">
            <span>${invocation.name.slice('invocations/'.length)}</span>
            <span class="badge unexpected">${this.resultStats.unexpected} Unexpected</span>
            <span class="badge exonerated">${this.resultStats.exonerated} Exonerated</span>
            <span class="badge expected">${this.resultStats.expected} Expected</span>
            <span style="float: right">${this.renderInvocationState()}</span>
        </div>
        <tr-test-invocation-details
            id="invocation-details"
            .invocation=${invocation}
        ></tr-test-invocation-details>
        <div id="main" class=${classMap({'show-menu': this.menuExpanded})}>
            <div id="left-panel">
                <tr-test-output-filters
                    id="test-result-filter"
                    .onFilterChange=${(filterMapFn: TestFilterMapFn) => this.filterMapFn = filterMapFn}
                    .testResults=${this.testInvocation?.testResults || []}
                    .testExonerations=${this.testInvocation?.testExonerations || []}
                ></tr-test-output-filters>
                <tr-test-nav-tree
                    .testIds=${this.filteredTestIds}
                    .selectedTests=${(tests: string[]) => this.selectedTestIds = tests}
                    .node=${this.testNavTreeNode}
                ></tr-test-nav-tree>
            </div>
            <div id="test-result-view">
                <div id="test-result-header">
                    <div
                        style="display: inline-table; height: 100%;"
                        @click=${() => this.menuExpanded = !this.menuExpanded}
                    >
                        <mwc-icon style="vertical-align: middle; display: table-cell">menu</mwc-icon>
                    </div>
                    <span style="vertical-align: middle; display: inline-table; height: 100%; margin-left: 5px;">${this.testIdCommonPrefix}</span>
                    <span style="float: right">
                        <mwc-button
                            label="Expand All"
                            @click=${() => this.toggleAllTests(true)}
                        ></mwc-button>
                        <mwc-button
                            label="Collapse All"
                            @click=${() => this.toggleAllTests(false)}
                        ></mwc-button>
                    </span>
                </div>
                <div id="test-result-content">
                    ${repeat(this.selectedTests, (t) => t.id, (t, i) => html`
                    <tr-test-entry
                        .test=${t}
                        .idCommonPrefix=${this.testIdCommonPrefix}
                        .prevTestId=${(this.selectedTests[i-1]?.id || this.testIdCommonPrefix)}
                    ></tr-test-entry>
                    `)}
                    <div>
                        <span>Showing ${this.selectedTests.length}/${this.selectedTests.length} tests.</span>
                        <span
                            id="load-more"
                        >
                            Load More
                        </span>
                    </div>
                </div>
            </div>
        </div>
        `;
    }

    static styles = css`
        :host {
            display: grid;
            grid-gap: 5px;
            grid-template-rows: auto auto auto 1fr;
            overflow-y: hidden;
        }
        #refresh-icon {
            color: #03a9f4;
            --mdc-icon-button-size: 1em;
            --mdc-icon-size: 1em;
            vertical-align: middle;
        }

        .badge {
            border: 1px solid;
            border-radius: 5px;
            padding: 0 2px 0 2px;
        }
        .badge.unexpected {
            color: rgb(210, 63, 49);
            border-color: rgb(210, 63, 49);
        }
        .badge.exonerated {
            color: #ffc107;
            border-color: #ffc107;
        }
        .badge.expected {
            color: rgb(51, 172, 113);
            border-color: rgb(51, 172, 113);
        }

        #main {
            display: grid;
            grid-template-columns: 350px 1fr;
            grid-template-rows: 1fr;
            grid-template-areas: "test-result-view test-result-view";
            border-top: 2px solid #DDDDDD;
            overflow-y: hidden;
        }
        #main.show-menu {
            grid-template-areas: "left-panel test-result-view";
        }
        #left-panel {
            grid-area: left-panel;
            display: none;
            overflow-y: hidden;
            border-right: 2px solid #DDDDDD;
        }
        #main.show-menu #left-panel {
            display: block;
        }
        #test-result-view {
            grid-area: test-result-view;
            display: grid;
            overflow-y: hidden;
            grid-template-rows: 32px 1fr;
        }
        #test-result-header {
            background: #DDDDDD;
        }
        #test-result-content > * {
            margin: 5px 0 5px 0;
            display: block;
        }
        #test-result-content {
            overflow-y: auto;
        }
        #test-invocation-summary {
            border-bottom: solid red;
            padding: 5px;
        }

        .inline-icon {
            --mdc-icon-size: 1em;
            vertical-align: middle;
        }
        #load-more {
            color: blue;
        }

        .hidden {
            display: none;
        }
        `;
}
