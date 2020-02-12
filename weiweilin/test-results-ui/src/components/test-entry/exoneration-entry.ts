import { customElement, property, html, css } from "lit-element";
import { MobxLitElement } from "@adobe/lit-mobx";
import { TestResult, TestStatus, TestExoneration } from '../../types/resultdb';
import { classMap } from "lit-html/directives/class-map";
import { unsafeHTML } from "lit-html/directives/unsafe-html";
import "@material/mwc-icon";

import './artifact';
import { observable, computed } from "mobx";
import { repeat } from "lit-html/directives/repeat";
import { styleMap } from "lit-html/directives/style-map";

const STATUS_DISPLAY_MAP = {
    [TestStatus.Unspecified]: 'unspecified',
    [TestStatus.Pass]: 'passed',
    [TestStatus.Fail]: 'failed',
    [TestStatus.Skip]: 'skipped',
    [TestStatus.Crash]: 'crashed',
    [TestStatus.Abort]: 'aborted',
};

@customElement('tr-exoneration-entry')
export class ExonerationEntryElement extends MobxLitElement {
    @observable.ref
    public testExoneration?: TestExoneration;

    @observable.ref
    private expanded: boolean = false;
    @observable.ref
    private explanationExpanded: boolean = true;
    @observable.ref
    private variantExpanded: boolean = false;

    private renderVariant() {
        const variantKV = Object.entries(this.testExoneration!.variant?.def ?? {});
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

    protected render() {
        return html`
        <div>
            <div
                class="expandable-header"
                @click=${() => this.expanded = !this.expanded}
            >
                <mwc-icon class="expand-toggle">${this.expanded ? 'expand_more' : 'chevron_right'}</mwc-icon>
                <span class="one-line-content">
                    #${this.testExoneration!.exonerationId}
                    <span style="color: rgb(210, 63, 49);">exonerated</span>
                </span>
            </div>
            <div id="body">
                <div id="content-ruler"></div>
                <div id="content" class=${classMap({hidden: !this.expanded})}>
                    ${this.renderVariant()}
                    <div class=${classMap({hidden: (this.testExoneration!.explanationHTML ?? '').length === 0})}>
                        <div
                            class="expandable-header"
                            @click=${() => this.explanationExpanded = !this.explanationExpanded}
                        >
                            <mwc-icon class="expand-toggle">${this.explanationExpanded ? 'expand_more' : 'chevron_right'}</mwc-icon>
                            <div class="one-line-content">Explanation:</div>
                        </div>
                        <div id="explanation-html" class=${classMap({hidden: !this.explanationExpanded})}>
                            ${unsafeHTML(this.testExoneration!.explanationHTML)}
                        </div>
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
    #explanation-html {
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
