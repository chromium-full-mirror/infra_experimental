import { PrpcClient } from '@chopsui/prpc-client';
import { computed, observable } from 'mobx';
import { Invocation, QueryTestExonerationsResponse, QueryTestResultsResponse, TestExoneration, TestResult } from '../types/resultdb';

export interface Test {
    id: string;
    outputs: TestOutput[];
}

export type TestOutput = TestResult | TestExoneration;

export function isTestResult(testOutput: TestOutput): testOutput is TestResult {
    return (testOutput as TestResult).resultId !== undefined;
}

export class TestInvocation {
    @observable.shallow
    private _testResults: TestResult[] = [];
    public get testResults() { return this._testResults; }

    @observable.shallow
    private _testExonerations: TestExoneration[] = [];
    public get testExonerations() { return this._testExonerations; }

    @observable.ref
    private _invocation: Invocation | null = null;
    public get invocation() { return this._invocation; }

    @computed
    public get tests() {
        const ret: Test[] = [];
        let lastTestId = '';
        let testResultPivot = 0;
        let testExonerationPivot = 0;
        while (testResultPivot < this.testResults.length || testExonerationPivot < this.testExonerations.length) {
            if (testResultPivot < this.testResults.length && this.testResults[testResultPivot].testId === lastTestId) {
                ret[ret.length - 1].outputs.push(this.testResults[testResultPivot]);
                testResultPivot += 1;
            } else if (testExonerationPivot < this.testExonerations.length && this.testExonerations[testExonerationPivot].testId === lastTestId) {
                ret[ret.length - 1].outputs.push(this.testExonerations[testExonerationPivot]);
                testExonerationPivot += 1;
            } else {
                lastTestId = testResultPivot < this.testResults.length ? this.testResults[testResultPivot].testId : this.testExonerations[testExonerationPivot].testId;
                ret.push({
                    id: lastTestId,
                    outputs: [],
                });
            }
        }
        return ret;
    }

    private testResultPageToken?: string | null;
    private testExonerationPageToken?: string | null;

    constructor(public readonly invocationName: string, private readonly resultDbPrpcClient: PrpcClient) {
        this.loadInvocation();
        this.loadTestResults();
        this.loadTestExonerations();
    }

    private async loadInvocation() {
        const res = await this.resultDbPrpcClient!.call(
            'luci.resultdb.rpc.v1.ResultDB',
            'GetInvocation',
            {name: this.invocationName},
        ) as Invocation;
        this._invocation = res;
    }

    private async loadTestResults() {
        if (this.testResultPageToken === null) {
            return;
        }
        const pageToken = this.testResultPageToken;
        this.testResultPageToken = null;
        const res = await this.resultDbPrpcClient!.call(
            'luci.resultdb.rpc.v1.ResultDB',
            'QueryTestResults',
            {invocations: [this.invocationName], pageToken},
        ) as QueryTestResultsResponse;
        this._testResults.push(...res.testResults);
        this.testResultPageToken = res.nextPageToken || null;
        await this.loadTestResults();
    }

    private async loadTestExonerations() {
        if (this.testExonerationPageToken === null) {
            return;
        }
        const pageToken = this.testExonerationPageToken;
        this.testExonerationPageToken = null;
        const res = await this.resultDbPrpcClient!.call(
            'luci.resultdb.rpc.v1.ResultDB',
            'QueryTestExonerations',
            {invocations: [this.invocationName], pageToken},
        ) as QueryTestExonerationsResponse;
        this._testExonerations.push(...res.testExonerations);
        this.testExonerationPageToken = res.nextPageToken || null;
        await this.loadTestExonerations();
    }
}
