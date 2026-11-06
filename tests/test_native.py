"""Compile and cross-check the cleaned original native solver when available."""

import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

from lsw_range import Interval
try:
    from .test_exactness import enumerate_bounds
except ImportError:  # ``unittest discover -s tests`` imports top-level modules.
    from test_exactness import enumerate_bounds


NATIVE_METHODS = ("LocalWindows", "LocalWindowsGeneric", "GlobalBudgetBank",
                  "GapComponents", "RunTailFullGThenGather", "ReferenceFullCount")


@unittest.skipUnless(shutil.which("c++"), "a C++17 compiler is optional")
class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.executable = Path(cls.temporary.name) / "lsw-native"
        source = Path(__file__).resolve().parents[1] / "native" / "lsw_range.cpp"
        subprocess.run(["c++", "-std=c++17", "-O2", str(source), "-o", str(cls.executable)],
                       check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_all_native_methods_match_original_path_enumeration(self):
        generator = random.Random(9173)
        cases = [([], (-1, 1)), ([(0, 0), (1, 1)], (0, 1)),
                 ([(-99, 99), (1, 0), (0, 0)], (0, 0)),
                 ([(0, 0), (10, 10)], (0, 10))]
        for _ in range(70):
            rows = [generator.choice([(1, 0), (-1, 1), (-2, 0), (0, 0), (1, 2)])
                    for _ in range(generator.randrange(6))]
            cases.append((rows, (-1, 1)))
        budgets = [4, 0, 1, 2, 1]
        requests, expected = [], []
        for rows, (a, b) in cases:
            truth = enumerate_bounds([Interval(*row) for row in rows], (a, b), budgets)
            for method in NATIVE_METHODS:
                requests.append(f"{method} {len(rows)} {a} {b} {len(budgets)}\n"
                                + " ".join(map(str, budgets)) + "\n"
                                + "\n".join(f"{lo} {hi}" for lo, hi in rows) + "\n")
                expected.append(truth)
        process = subprocess.run([str(self.executable)], input="".join(requests),
                                 capture_output=True, text=True, check=True)
        records = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(len(records), len(expected))
        for record, truth in zip(records, expected):
            self.assertEqual(tuple(map(tuple, record["bounds"])), truth)
            self.assertEqual(record["budgets"], budgets)

    def test_unknown_method_rejected_before_fast_path(self):
        process = subprocess.run([str(self.executable)], input="Unknown 0 0 0 1\n0\n",
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 2)
        self.assertIn("unknown method", process.stderr)


if __name__ == "__main__":
    unittest.main()
