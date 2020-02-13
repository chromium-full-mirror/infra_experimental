import { customElement, property, html, css } from "lit-element";
import { MobxLitElement } from "@adobe/lit-mobx";
import { TestResult, TestStatus } from '../../types/resultdb';
import { classMap } from "lit-html/directives/class-map";
import "@material/mwc-icon";

import './result-entry'
import './exoneration-entry';
import { observable, computed } from "mobx";
import { repeat } from "lit-html/directives/repeat";
import { Test, isTestResult } from "../../models/test-invocation";

@customElement('tr-test-entry')
export class TestEntryElement extends MobxLitElement {
    @observable.ref
    public test?: Test;
    @observable.ref
    public idCommonPrefix: string = '';
    @observable.ref
    public prevTestId: string = '';

    @observable.ref
    public expanded: boolean = false;

    @computed
    private get unexpectedCount() {
        return this.test!.outputs.filter((tr) => isTestResult(tr) && !tr.expected).length;
    }
    @computed
    private get allExpected() {
        return this.unexpectedCount === 0;
    }

    @computed
    private get testIdCommonPrefix() {
        let commonPrefixLength = 0;
        for (let i = 0; i < this.prevTestId.length; ++i) {
            if (this.prevTestId[i] !== this.test!.id[i]) {
                break;
            }
            if (!/\w|-/.test(this.prevTestId[i])) {
                commonPrefixLength = i + 1;
            }
        }
        return this.prevTestId.slice(0, commonPrefixLength);
    }

    protected render() {
        return html`
        <div class=${classMap({expected: this.allExpected})}>
            <div
                class="expandable-header"
                @click=${() => this.expanded = !this.expanded}
            >
                <mwc-icon id="expand-toggle">${this.expanded ? 'expand_more' : 'chevron_right'}</mwc-icon>
                <div id="header" class="one-line-content">
                    <mwc-icon id="expectancy-indicator" class=${classMap({expected: this.allExpected})}>${this.allExpected ? 'check' : 'error'}</mwc-icon>
                    <div id="test-identifier">
                        <span class="light">${this.testIdCommonPrefix.slice(this.idCommonPrefix.length)}</span>${this.test!.id.slice(this.testIdCommonPrefix.length)}
                    </div>
                </div>
            </div>
            <div id="body">
                <div id="content-ruler"></div>
                <div id="content" class=${classMap({hidden: !this.expanded})}>
                    ${repeat(this.test!.outputs, (output) => {
                        if (isTestResult(output)) {
                            return html`<tr-result-entry .testResult=${output}></tr-result-entry>`;
                        } else {
                            return html`<tr-exoneration-entry .testExoneration=${output}></tr-exoneration-entry>`;
                        }
                    })}
                </div>
            </div>
        </div>
        `;
    }

    static styles = css`
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
    .light {
        color: grey;
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

    #header {
        display: grid;
        grid-template-columns: 24px 1fr;
        grid-template-rows: 24px;
        grid-gap: 5px;
    }

    #expectancy-indicator {
        color: #d23f31;
        grid-row: 1;
        grid-column: 1;
    }
    #expectancy-indicator.expected {
        color: #33ac71;
    }

    #test-identifier {
        grid-row: 1;
        grid-column: 2;
        font-size: 16px;
        line-height: 24px;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }

    .hidden {
        display: none;
    }
    `;
}
