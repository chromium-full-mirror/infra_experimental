import { customElement, html, css } from "lit-element";
import { MobxLitElement } from "@adobe/lit-mobx";
import { observable, computed } from "mobx";
import { groupBy } from 'lodash';
import { repeat } from "lit-html/directives/repeat";
import '@material/mwc-icon';
import { Test } from "../../view-models/test-invocation";
import './test-nav-node';

@customElement('tr-test-nav-tree')
export class TestNavTreeElement extends MobxLitElement {
    @observable.ref
    public tests: Test[] = [];

    protected render() {
        let branchExt = '';
        let entries = Object.entries(groupBy(this.tests, (test) => /^([a-zA-Z0-9_-])*?([^a-zA-Z0-9_-]|$)/.exec(test.id)![0]));
        while (entries.length === 1) {
            const subbranch = entries[0][0];
            if (branchExt.length + subbranch.length === entries[0][1][0].id.length) {
                break;
            }

            branchExt += subbranch;
            entries = Object.entries(groupBy(this.tests, (test) => {
                const key = /^([a-zA-Z0-9_-])*?([^a-zA-Z0-9_-]|$)/.exec(test.id.slice(branchExt.length))![0];
                return key;
            }));
        }

        return html`
        <div id="header">${branchExt}</div>
        <div id="body" style="overflow-y: auto; height: 100%;">
            <div id="content">
                ${repeat(entries, ([k]) => k, ([k, v]) => html`
                <tr-test-nav-node
                    .depth=${0}
                    .branchName=${k}
                    .pathName=${branchExt + k}
                    .tests=${v}
                >
                </tr-test-nav-node>
                `)}
            </div>
        </div>
        `;
    }

    static styles = css`
    #header {
        background-color: #DDDDDD;
        padding: 2px 5px;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }
    .expandable-header.selected {
        background-color: #66ccff;
    }

    #body {
        display: grid;
        grid-template-columns: 24px 1fr;
        grid-gap: 5px;
    }
    #content {
        grid-column: 1/3;
        grid-row: 1;
    }
    `;
}
