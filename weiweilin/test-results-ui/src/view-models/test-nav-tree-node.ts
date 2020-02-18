import { observable, computed } from "mobx";
import { groupBy } from "lodash";

const FIRST_BRANCH_REGEX = /^([a-zA-Z0-9_-])*?([^a-zA-Z0-9_-]|$)/;


export class TestNavTreeNode {
    public readonly prefix: string;
    public readonly branchName: string;

    public readonly parent: TestNavTreeNode | null;
    public readonly root: TestNavTreeNode;

    @computed
    public get testIds(): string[] {
        if (this.children.length === 0) {
            return [this.prefix]
        }
        return this.children.map((child) => child.testIds).flat();
    }

    @computed
    public get selectedTestIds(): string[] {
        if (this.selected) {
            return this.testIds;
        } else {
            return this.children.map((child) => child.selectedTestIds).flat()
        }
    }

    @computed
    public get descendentSelected(): boolean {
        return this.children.some((child) => child.selected || child.descendentSelected);
    }
    @observable.ref
    private _selected: boolean = false;
    @computed
    public get selected() {
        return this._selected;
    }
    public unselectBranch() {
        if (this._selected) {
            this._selected = false;
        }

        if (this.descendentSelected) {
            for (const child of this.children) {
                child.unselectBranch();
            }
        }
    }

    public setSelectedAll(selected: boolean) {
        this._selected = selected;
        for (const child of this.children) {
            child.setSelectedAll(selected);
        }
    }

    public toggleSelectExclusive() {
        if (this._selected && this.root.selectedTestIds.length === 1) {
            this._selected = false;
            return;
        }

        this.root.unselectBranch();
        this._selected = true;
    }

    public toggleSelect() {
        this._selected = !this._selected;
    }

    public selectRange(node: TestNavTreeNode) {
        if (node.prefix.localeCompare(this.prefix) < 0) {
        }
    }

    @observable.shallow
    public children: TestNavTreeNode[] = [];

    @computed
    public get logicalBranchName() {
        let branchName = this.branchName;
        let pivot: TestNavTreeNode = this;
        while (pivot.children.length === 1) {
            pivot = pivot.children[0];
            branchName += pivot.branchName;
        }
        return branchName;
    }

    @computed
    public get logicalChildren() {
        let pivot: TestNavTreeNode = this;
        while (pivot.children.length === 1) {
            pivot = pivot.children[0];
        }
        return pivot.children;
    }

    public constructor(parent: TestNavTreeNode | null, branchName: string, testIds: string[]) {
        this.parent = parent;
        this.prefix = (this.parent?.prefix || '') + branchName;
        this.branchName = branchName;
        this.root = parent?.root || this;
        if (this.prefix === (testIds[0] || '')) {
            return;
        }
        let entries = Object.entries(groupBy(testIds, (testId) => FIRST_BRANCH_REGEX.exec(testId.slice(this.prefix.length))![0]));
        this.children = entries.map(([branchName, testIds]) => new TestNavTreeNode(this, branchName, testIds));
    }
}
