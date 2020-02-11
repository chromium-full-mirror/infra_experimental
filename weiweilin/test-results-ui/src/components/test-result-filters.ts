import { MobxLitElement } from "@adobe/lit-mobx";
import { customElement, css, property } from "lit-element";
import { html } from "lit-html";
import { TestResult, TestExoneration } from '../models/resultdb';
import '@material/mwc-checkbox';
import '@material/mwc-formfield';
import { observable, computed } from "mobx";
import { Checkbox } from "@material/mwc-checkbox";

export type TestResultFilter = (testResult: TestResult) => boolean

@customElement('tr-test-result-filters')
export class TestResultFilters extends MobxLitElement {
    public onFilterChange: (filter: TestResultFilter) => void = () => undefined;
    @observable.ref
    public testResults: TestResult[] = [];
    @observable.ref
    public testExonerations: TestExoneration[] = [];

    @computed
    private get resultStats() {
        const expected = this.testResults.filter((result) => result.expected).length || 0;
        return {
            expected,
            unexpected: (this.testResults.length || 0) - expected,
            exonerated: this.testExonerations.length,
        }
    }

    @observable.ref
    private unexpectedTests = true;
    @observable.ref
    private expectedTests = false;
    @observable.ref
    private exoneratedTests = false;
    @observable.ref
    private siblingResults = true;

    private filterResults = (testResult: TestResult) => {
        if (this.unexpectedTests && !testResult.expected) {
            return true;
        }
        if (this.expectedTests && testResult.expected) {
            return true;
        }
        return false;
    }

    protected render() {
        return html`
        <mwc-formfield id="unexpected" label=${`Unexpected (${this.resultStats.unexpected})`}
        >
            <mwc-checkbox
                ?checked=${this.unexpectedTests}
                @change=${(v: MouseEvent) => this.unexpectedTests = (v.target as Checkbox).checked}
            ></mwc-checkbox>
        </mwc-formfield>
        <mwc-formfield id="siblings" label=${`Siblings`}>
            <mwc-checkbox
                ?disabled=${!this.unexpectedTests}
                ?checked=${this.siblingResults}
                @change=${(v: MouseEvent) => this.siblingResults = (v.target as Checkbox).checked}
            ></mwc-checkbox>
        </mwc-formfield>
        <mwc-formfield id="expected" label=${`Expected (${this.resultStats.expected})`}>
            <mwc-checkbox
                ?checked=${this.expectedTests}
                @change=${(v: MouseEvent) => this.expectedTests = (v.target as Checkbox).checked}
            ></mwc-checkbox>
        </mwc-formfield>
        <mwc-formfield id="exonerated" label=${`Exonerated (${this.resultStats.exonerated})`}>
            <mwc-checkbox
                ?checked=${this.exoneratedTests}
                @change=${(v: MouseEvent) => this.exoneratedTests = (v.target as Checkbox).checked}
            ></mwc-checkbox>
        </mwc-formfield>
        <span id="advanced">
            <img id="filter-icon" src="/assets/svg/Filter-icon-vector-02.svg" width="25px" height="25px" class="center"/>
            <span id="filter-text">Advanced</span>
        </span>
        <div id="search-box-container">
            <input id="search-box" placeholder="Search"/>
        </div>
        `;
    }

    protected firstUpdated() {
        this.onFilterChange(this.filterResults);
    }

    static styles = css`
        :host {
            display: grid;
            grid-template-areas:
                "unexpected siblings"
                "expected exonerated"
                "advanced advanced"
                "search-box search-box";
            grid-template-rows: repeat(4);
            grid-template-columns: repeat(auto, 2);
            padding: 5px 0;
        }
        .center {
            vertical-align: middle;
        }
        #filter-icon {
            height: 20px;
            width: 20px;
        }
        #filter-text {
            font-size: 14px;
            margin-left: -5px;
        }
        #search-box-container {
            padding: 0 10px;
            grid-area: search-box;
        }
        #search-box {
            width: 100%;
        }
        mwc-formfield > mwc-checkbox {
            margin-right: -10px;
        }
        #filters-container {
        }
        #unexpected {
            grid-area: unexpected;
        }
        #siblings {
            grid-area: siblings;
        }
        #expected {
            grid-area: expected;
        }
        #exonerated {
            grid-area: exonerated;
        }
        #advanced {
            grid-area: advanced;
        }
        `
        ;

    constructor() {
        super();
    }
}
