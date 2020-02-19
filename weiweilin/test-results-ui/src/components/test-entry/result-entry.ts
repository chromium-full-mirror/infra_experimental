import { MobxLitElement } from '@adobe/lit-mobx';
import '@material/mwc-icon';
import { css, customElement, html } from 'lit-element';
import { classMap } from 'lit-html/directives/class-map';
import { unsafeHTML } from 'lit-html/directives/unsafe-html';
import { TestResult, TestStatus } from '../../types/resultdb';

import { observable } from 'mobx';
import './artifact';

const STATUS_DISPLAY_MAP = {
    [TestStatus.Unspecified]: 'unspecified',
    [TestStatus.Pass]: 'passed',
    [TestStatus.Fail]: 'failed',
    [TestStatus.Skip]: 'skipped',
    [TestStatus.Crash]: 'crashed',
    [TestStatus.Abort]: 'aborted',
};

@customElement('tr-result-entry')
export class ResultEntryElement extends MobxLitElement {
    @observable.ref
    public testResult?: TestResult;

    @observable.ref
    private expanded = true;
    @observable.ref
    private outputArtifactsExpanded = true;
    @observable.ref
    private inputArtifactsExpanded = false;
    @observable.ref
    private summaryExpanded = true;
    @observable.ref
    private variantExpanded = false;
    @observable.ref
    private tagExpanded = false;

    private renderVariant() {
        const variantKV = Object.entries(this.testResult!.variant?.def ?? {});
        if (variantKV.length === 0) {
            return html``;
        }
        return html`
        <div
            class="expandable-header"
            @click=${() => this.variantExpanded = !this.variantExpanded}
        >
            <mwc-icon class="expand-toggle">${this.variantExpanded ? 'expand_more' : 'chevron_right'}</mwc-icon>
            <span class="one-line-content">
                Variant:
                <span class=${classMap({hidden: this.variantExpanded, light: true})}>
                ${variantKV.map(([k, v]) => html`
                    <span class="kv-key">${k}</span>:
                    <span class="kv-value">${v}</span>
                `)}
                </span>
            </span>
        </div>
        <div class=${classMap({'kv-table': true, hidden: !this.variantExpanded})}>
        ${variantKV.map(([k, v]) => html`
            <span class="key">${k}:</span>
            <span class="value">${v}</span>
        `)}
        </div>
        `;
    }

    private renderTags() {
        return html`
        <div class=${classMap({hidden: !this.testResult!.tags.length})}>
            <div
                class="expandable-header"
                @click=${() => this.tagExpanded = !this.tagExpanded}>
                <mwc-icon class="expand-toggle">${this.tagExpanded ? 'expand_more' : 'chevron_right'}</mwc-icon>
                <span class="one-line-content">
                    Tags:
                    <span class=${classMap({hidden: this.tagExpanded, light: true})}>
                    ${this.testResult!.tags.map((tag) => html`
                        <span class="kv-key">${tag.key}</span>:
                        <span class="kv-value">${tag.value}</span>
                    `)}
                    </span>
                </span>
            </div>
            <div class=${classMap({'kv-table': true, hidden: !this.tagExpanded})}>
            ${this.testResult!.tags.map((tag) => html`
                <span class="key">${tag.key}:</span>
                <span class="value">${tag.value}</span>
            `)}
            </div>
        </div>
        `;
    }

    protected render() {
        return html`
        <div>
            <div
                class="expandable-header"
                @click=${() => this.expanded = !this.expanded}
            >
                <mwc-icon class="expand-toggle">${this.expanded ? 'expand_more' : 'chevron_right'}</mwc-icon>
                <span class="one-line-content">
                    #${this.testResult!.resultId}
                    ${this.testResult!.expected ? '' : html`<span style="color: rgb(210, 63, 49);">unexpectedly</span>`}
                    ${STATUS_DISPLAY_MAP[this.testResult!.status]} after ${this.testResult!.duration || '-s'}
                </span>
            </div>
            <div id="body">
                <div id="content-ruler"></div>
                <div id="content" class=${classMap({hidden: !this.expanded})}>
                    ${this.renderVariant()}
                    <div class=${classMap({hidden: (this.testResult!.summaryHtml ?? '').length === 0})}>
                        <div
                            class="expandable-header"
                            @click=${() => this.summaryExpanded = !this.summaryExpanded}
                        >
                            <mwc-icon class="expand-toggle">${this.summaryExpanded ? 'expand_more' : 'chevron_right'}</mwc-icon>
                            <div class="one-line-content">Summary:</div>
                        </div>
                        <div id="summary-html" class=${classMap({hidden: !this.summaryExpanded})}>
                            ${unsafeHTML(this.testResult!.summaryHtml)}
                        </div>
                    </div>
                    ${this.renderTags()}
                    <div class=${classMap({hidden: !this.testResult!.outputArtifacts})}>
                        <div
                            class="expandable-header"
                            @click=${() => this.outputArtifactsExpanded = !this.outputArtifactsExpanded}
                        >
                            <mwc-icon class="expand-toggle">${this.outputArtifactsExpanded ? 'expand_more' : 'chevron_right'}</mwc-icon>
                            <div class="one-line-content">
                                Output Artifacts:
                                <span class="light">${this.testResult!.outputArtifacts?.length || 0} artifact(s)</span>
                            </div>
                        </div>
                        <ul class=${classMap({hidden: !this.outputArtifactsExpanded})}>
                            ${this.testResult!.outputArtifacts?.map((artifact) => html`
                            <li><tr-artifact .artifact=${artifact}></tr-artifact></li>
                            `)}
                        </ul>
                    </div>
                    <div class=${classMap({hidden: !this.testResult!.inputArtifacts})}>
                        <div
                            class="expandable-header"
                            @click=${() => this.inputArtifactsExpanded = !this.inputArtifactsExpanded}
                        >
                            <mwc-icon class="expand-toggle">${this.inputArtifactsExpanded ? 'expand_more' : 'chevron_right'}</mwc-icon>
                            <div class="one-line-content">
                                Input Artifacts:
                                <span class="light">${this.testResult!.inputArtifacts?.length || 0} artifact(s)</span>
                            </div>
                        </div>
                        <ul class=${classMap({hidden: !this.inputArtifactsExpanded})}>
                            ${this.testResult!.inputArtifacts?.map((artifact) => html`
                            <li><tr-artifact .artifact=${artifact}></tr-artifact></li>
                            `)}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        `;
    }

    static styles = css`
    .hidden {
        display: none !important;
    }

    .kv-table {
        display: grid;
        margin-left: 29px;
        grid-template-columns: auto 1fr;
    }
    .kv-table>.value {
        margin-left: 5px;
    }
    .expandable-header {
        display: grid;
        grid-template-columns: 24px 1fr;
        grid-template-rows: 24px;
        grid-gap: 5px;
        cursor: pointer;
    }
    .expandable-header .expand-toggle {
        grid-row: 1;
        grid-column: 1;
    }
    .expandable-header .one-line-content {
        grid-row: 1;
        grid-column: 2;
        font-size: 16px;
        line-height: 24px;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }

    #status.pass {
        color: rgb(51, 172, 113);
    }
    #status.fail {
        color: rgb(210, 63, 49);
    }
    #status.crash {
        color: rgb(51, 172, 113);
    }
    #status.abort {
        color: rgb(51, 172, 113);
    }
    #status.skip {
        color: grey;
    }
    #status.unspecified {
        color: grey;
    }

    #body {
        display: grid;
        grid-template-columns: 24px 1fr;
        grid-gap: 5px;
    }
    #content-ruler {
        border-left: 1px solid #DDDDDD;
        width: 0px;
        margin-left: 11.5px;
    }
    #summary-html {
        background-color: rgb(245, 245, 245);
        padding: 5px;
    }

    .light {
        color: grey;
    }
    .kv-value::after {
        content: ',';
    }
    .kv-value:last-child::after {
        content: '';
    }
    `;
}
