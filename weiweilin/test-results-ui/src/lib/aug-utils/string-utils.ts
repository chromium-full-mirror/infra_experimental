declare global {
    interface String {
        splitAt(indices: Iterable<number>): Generator<string>;
        splitWith(chars: Iterable<string>): Generator<string>;
    }
}


String.prototype.splitAt = function* splitAt(indices: Iterable<number>): Generator<string> {
    let start = 0;
    for (const i of indices) {
        yield this.slice(start, i);
        start = i;
    }
};

String.prototype.splitWith = function* splitWith(chars: Iterable<string>): Generator<string> {
    const ret = [this];
    for (const char of chars) {
        ret.flatMap((v) => v.split(char));
    }
    return ret;
};

export default String;
