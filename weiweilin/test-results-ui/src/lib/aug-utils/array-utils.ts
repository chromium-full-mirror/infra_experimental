declare global {
    interface Array<T> {
        filterMap<V>(filterMapFn: (item: T, i: number, array: T[]) => (V | undefined)): V[];
    }
}
Array.prototype.filterMap = function<V>(filterMapFn: (item: any, i: number, array: any[]) => (V | undefined)) {
    const ret: V[] = [];
    for(let i = 0; i < this.length; ++i) {
        const item = filterMapFn(this[i], i, this);
        if (item !== undefined) {
           ret.push(item);
        }
    }
    return ret;
};

export default Array;
