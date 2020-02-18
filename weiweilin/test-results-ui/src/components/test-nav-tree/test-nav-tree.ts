import { customElement, html, css } from "lit-element";
import { MobxLitElement } from "@adobe/lit-mobx";
import { observable, computed } from "mobx";
import { groupBy } from 'lodash';
import { repeat } from "lit-html/directives/repeat";
import '@material/mwc-icon';
import { Test } from "../../view-models/test-invocation";
import './test-nav-tree-node';
import { TestNavTreeNode } from "../../view-models/test-nav-tree-node";

@customElement('tr-test-nav-tree')
export class TestNavTreeElement extends MobxLitElement {
    @observable.ref
    public testIds: string[] = [];

    @observable.ref
    public node?: TestNavTreeNode;

    private lastSelectedNode: TestNavTreeNode | null = null;
    private lastShiftSelectedNode: TestNavTreeNode | null = null;
    private nodeClicked = (node: TestNavTreeNode, e: MouseEvent) => {
        if (e.shiftKey && this.lastSelectedNode) {
            if (this.lastShiftSelectedNode) {
                node.setSelectedRange(this.lastShiftSelectedNode, false);
            }

            node.setSelectedRange(this.lastSelectedNode, true);
            this.lastShiftSelectedNode = node;
            return;
        }
        this.lastShiftSelectedNode = null;
        this.lastSelectedNode = node;
        if (e.ctrlKey) {
            node.toggleSelect();
        } else {
            node.toggleSelectExclusive();
        }
    }

    protected render() {
        return html`
        <div id="header">${this.node!.logicalBranchName}</div>
        <div id="body" style="overflow-y: auto; height: 100%;">
            <div id="content">
                ${repeat(this.node!.logicalChildren, (node) => node.logicalBranchName, (node) => html`
                <tr-test-nav-tree-node
                    .depth=${0}
                    .node=${node}
                    .nodeClicked=${this.nodeClicked}
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
