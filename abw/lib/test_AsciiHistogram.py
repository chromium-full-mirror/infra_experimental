#!/usr/bin/env python

# python -m unittest discover -v

import unittest
from pprint import pprint

from AsciiHistogram import AsciiHistogram

class TestAsciiHistogram(unittest.TestCase):
    def test_stats(self):
        ah = AsciiHistogram(n_buckets=10, v_max=100)
        for val in (2,4,6,8): ah.add(val)
        stats = ah.stats()
        self.assertEqual(4, stats['n'])
        self.assertAlmostEqual(5, stats['mean'])
        self.assertAlmostEqual(2.2360679, stats['stddev'], places=6)
        self.assertEqual(8, stats['90%ile'])

    def test_pick_bucket(self):
        ah = AsciiHistogram(n_buckets=10, v_max=100)
        self.assertEqual(1, ah.pick_bucket(0))
        self.assertEqual(1, ah.pick_bucket(1))
        self.assertEqual(1, ah.pick_bucket(9))
        self.assertEqual(2, ah.pick_bucket(10))
        self.assertEqual(10, ah.pick_bucket(99))

        # Hmm. Should 100 be considered valid for final bucket, or overflow ?
        self.assertEqual(11, ah.pick_bucket(100))

        # overflow/underflow
        self.assertEqual(0, ah.pick_bucket(-500))
        self.assertEqual(0, ah.pick_bucket(-5))
        self.assertEqual(11, ah.pick_bucket(111))
        self.assertEqual(11, ah.pick_bucket(1000))

    def test_fill_buckets(self):
        ah = AsciiHistogram(n_buckets=5, v_max=10)
        for val in range(0,10): ah.add(val) # note - [0,10), not [0,10]
        for val in (5,6): ah.add(val)
        ah.add(15) # overflow
        self.assertEqual([0,2,2,3,3,2,1], ah.fill_buckets())

    def test_to_string(self):
        ah = AsciiHistogram(n_buckets=20, v_max=20)
        for v in range(3,17): ah.add(v)
        for v in range(8,12): ah.add(v)
        ah.add(10)
        ah.add(24)
        expected = '[   cccccffhfccccc   |c] n=   20, mean=   10, stddev=    4, 90%ile=   15'
        self.assertEqual(expected, ah.to_string())

if __name__ == '__main__':
    unittest.main()
