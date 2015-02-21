import math
# import statistics # needs v3.4

class AsciiHistogram:
    def __init__(self, v_min=0, v_max=7200, n_buckets=60):
        self.vals = []
        self.v_min = v_min
        self.v_max = v_max
        self.n_buckets = n_buckets

    def add(self,val):
        self.vals.append(val)

    def percentile(self,ile):
        self.vals.sort()
        index = int (((ile / 100.0) * len(self.vals)) + 0.5)
        return self.vals[index - 1]

    def stats(self):
        n = len(self.vals)
        if (n == 0): return {'n':0, 'mean':0, 'stddev':0, '90%ile':0}
        # mean = statistics.mean(self.vals)
        # stddev = statistics.stdev(self.vals)
        mean = 0
        for val in self.vals: mean += val
        mean /= n
        diff_squares = 0
        for val in self.vals: diff_squares += (val - mean)**2
        stddev = math.sqrt(diff_squares / n)
        percentile_90 = self.percentile(90)
        return {'n':n, 'mean':mean, 'stddev':stddev, '90%ile':percentile_90}

    def pick_bucket(self, val):
        """Decide which bucket the given value would fall into.
        Bucket zero is underflow; buckets 1..N are the defined buckets; and
        bucket N+1 is overflow. (Thus n_buckets=10 may yield 12 buckets)
        """
        unit_val = 1.0 * (val - self.v_min) / (self.v_max - self.v_min)
        bucket = int(math.floor(unit_val * self.n_buckets)) + 1
        # Clip underflow / overflow
        if bucket<0: bucket = 0
        if bucket>(self.n_buckets+1): bucket = self.n_buckets+1
        return bucket

    def fill_buckets(self):
        bkts = [0] * (self.n_buckets + 2)
        for val in self.vals: bkts[self.pick_bucket(val)] += 1
        return bkts

    def bucket_count_to_char(self, count, total):
        if (count == 0 or total == 0): return ' '
        percent = 100.0 * count / total
        if (percent < 0.5): return '.'
        # [01234 56789 ABCDE FGHIJ KLMNO] - 25 chars
        # [abcdefghij klmnopqrst uvwxyzABCD EFGHIJKLMN OPQRSTUVWX] - 50 chars
        char_num = int(percent / 2.0)
        if (char_num<26):
            return chr(ord('a') + char_num)
        else:
            return chr(ord('A') + char_num - 26)

    def buckets_to_string(self, bkts):
        # Map each bucket to its (integer) percent of all values
        total = sum(bkts)
        chars = map(lambda v: self.bucket_count_to_char(v,total), bkts)
        # (underflow, *chars, overflow) = bkts
        overflow = chars.pop()
        underflow = chars[0]
        del chars[0]
        hist = ''.join(chars)
        if bkts[0]>0:
            return "[%s|%s|%s]" % (underflow, hist, overflow)
        else:
            return "[%s|%s]" % (hist, overflow)

    def to_string(self):
        hist = self.buckets_to_string(self.fill_buckets())
        stats = self.stats()

        return ("%s n=% 5d, mean=% 5d, stddev=% 5d, 90%%ile=% 5d" %
                (hist, stats['n'], stats['mean'],
                 stats['stddev'], stats['90%ile']))

    def __str__(self):
        return self.to_string()
