import { customElement, html, css } from "lit-element";
import { MobxLitElement } from "@adobe/lit-mobx";
import { observable } from "mobx";
import { groupBy } from 'lodash';
import { repeat } from "lit-html/directives/repeat";
import '@material/mwc-icon';
import { classMap } from "lit-html/directives/class-map";
import { styleMap } from "lit-html/directives/style-map";
import { Test } from "../../view-models/test-invocation";


@customElement('tr-test-nav-node')
export class TestNavNodeElement extends MobxLitElement {
    @observable.ref
    public depth: number = 0;

    @observable.ref
    public tests: Test[] = [];

    @observable.ref
    public branchName: string = '';

    @observable.ref
    public pathName: string = '';

    @observable.ref
    private expanded = true;
    @observable.ref
    private selected = false;

    protected render() {
        let branchExt = '';
        let entries = Object.entries(groupBy(this.tests, (test) => /^([a-zA-Z0-9_-])*?([^a-zA-Z0-9_-]|$)/.exec(test.id.slice(this.pathName.length))![0]));
        while (entries.length === 1) {
            const subbranch = entries[0][0];
            if (subbranch === '') {
                return html`
                <div 
                    class=${classMap({
                        'expandable-header': true,
                        selected: this.selected,
                    })}
                    style=${styleMap({
                        'padding-left': `${this.depth * 10}px`,
                    })}
                    @click=${(e: MouseEvent) => {
                        if (e.ctrlKey) {
                            this.selected = !this.selected;
                        } else {
                            this.expanded = !this.expanded;
                        }
                    }}
                >
                    <span class="one-line-content branch-name" style="grid-column: 1/3;">&nbsp;&nbsp;${this.branchName + this.tests[0].id.slice(this.pathName.length)}</span>
                </div>
                `
            }

            branchExt += subbranch;
            entries = Object.entries(groupBy(this.tests, (test) => {
                const key = /^([a-zA-Z0-9_-])*?([^a-zA-Z0-9_-]|$)/.exec(test.id.slice(this.pathName.length + branchExt.length))![0];
                return key;
            }));
        }

        return html`
        <div
            class=${classMap({
                'expandable-header': true,
                selected: this.selected,
            })}
            style=${styleMap({
                'padding-left': `${this.depth * 10}px`,
            })}
            @click=${(e: MouseEvent) => {
                if (e.ctrlKey) {
                    this.selected = !this.selected;
                } else {
                    this.expanded = !this.expanded;
                }
            }
        }>
            <mwc-icon class="expand-toggle">
                ${this.expanded ? 'expand_more' : 'chevron_right'}
            </mwc-icon>
            <span class="one-line-content branch-name">${this.branchName + branchExt}&lrm;</span>
        </div>
        <div id="body">
            <div id="content-ruler" style=${styleMap({left: `${this.depth * 10}px`})}></div>
            <div id="content" class=${classMap({hidden: !this.expanded})}>
                ${repeat(entries, ([k]) => k, ([k, v]) => html`
                <tr-test-nav-node
                    .depth=${this.depth + 1}
                    .branchName=${k}
                    .pathName=${this.pathName + branchExt + k}
                    .tests=${v}
                >
                </tr-test-nav-node>
                `)}
            </div>
        </div>
        `;
    }

    static styles = css`
    .hidden {
        display: none;
    }
    mwc-icon {
        --mwc-icon-size: 1em;
    }

    .expandable-header {
        display: grid;
        grid-template-columns: 24px 1fr;
        grid-template-rows: 24px;
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
    .expandable-header.selected {
        background-color: #66ccff;
    }

    .branch-name {
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }

    #body {
        display: grid;
        grid-template-columns: 24px 1fr;
        grid-gap: 5px;
    }
    #content-ruler {
        position: relative;
        border-left: 1px solid;
        border-color: #DDDDDD;
        width: 1px;
        height: 100%;
        margin-left: 11.5px;
        grid-column: 1;
        grid-row: 1;
    }
    #content {
        grid-column: 1/3;
        grid-row: 1;
    }
    `;
}
