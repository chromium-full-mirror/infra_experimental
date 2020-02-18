import { customElement, html, css } from "lit-element";
import { MobxLitElement } from "@adobe/lit-mobx";
import { observable } from "mobx";
import { groupBy } from 'lodash';
import { repeat } from "lit-html/directives/repeat";
import '@material/mwc-icon';
import { classMap } from "lit-html/directives/class-map";
import { styleMap } from "lit-html/directives/style-map";
import { Test } from "../../view-models/test-invocation";
import { TestNavTreeNode } from "../../view-models/test-nav-tree-node";
import '../../lib/components/expandable-entry';

@customElement('tr-test-nav-tree-node')
export class TestNavNodeElement extends MobxLitElement {
    @observable.ref
    public depth: number = 0;

    @observable.ref
    public node?: TestNavTreeNode;

    @observable.ref
    private expanded = true;

    public nodeClicked = (node: TestNavTreeNode, e: MouseEvent) => {};

    protected render() {
        return html`
        <div
            class=${classMap({
                'expandable-header': true,
                selected: this.node!.selected,
            })}
            style=${styleMap({
                'padding-left': `${this.depth * 10}px`,
            })}
        >
            <mwc-icon
                class="expand-toggle"
                style=${styleMap({display: this.node!.logicalChildren.length === 0 ? 'none' : ''})}
                @click=${() => this.expanded = !this.expanded}
            >
                ${this.expanded ? 'expand_more' : 'chevron_right'}
            </mwc-icon>
            <span
                class="one-line-content branch-name"
                style=${styleMap({
                    'grid-column': this.node!.logicalChildren.length === 0 ? '1/3' : '',
                    'padding-left': this.node!.logicalChildren.length === 0 ? '8px' : '',
                })}
                @click=${(e: MouseEvent) => this.nodeClicked(this.node!, e)}
            >${this.node!.logicalBranchName}&lrm;</span>
        </div>
        <div id="body">
            <div id="content-ruler" style=${styleMap({left: `${this.depth * 10}px`})}></div>
            <div id="content" class=${classMap({hidden: !this.expanded})}>
                ${repeat(this.node!.logicalChildren, (node) => node.logicalBranchName, (node) => html`
                <tr-test-nav-tree-node
                    .depth=${this.depth + 1}
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
        user-select: none;
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
