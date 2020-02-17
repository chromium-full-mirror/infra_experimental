import { customElement, html, css } from "lit-element";
import { MobxLitElement } from "@adobe/lit-mobx";
import { observable, computed } from "mobx";
import { groupBy } from 'lodash';
import { repeat } from "lit-html/directives/repeat";
import '@material/mwc-icon';
import { Test } from "../../view-models/test-invocation";
import './test-nav-tree-node';
import { TestNavTreeNode } from "../../view-models/test-nav-tree";

@customElement('tr-test-nav-tree')
export class TestNavTreeElement extends MobxLitElement {
    @observable.ref
    public testIds: string[] = [];

    @observable.ref
    public node?: TestNavTreeNode;

    protected render() {
        return html`
        <div id="header">${this.node!.logicalBranchName}</div>
        <div id="body" style="overflow-y: auto; height: 100%;">
            <div id="content">
                ${repeat(this.node!.logicalChildren, (node) => node.logicalBranchName, (node) => html`
                <tr-test-nav-tree-node
                    .depth=${0}
                    .node=${node}
                >
                </tr-test-nav-tree-node>
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
