"""Small exactness checks; these are correctness tests, not timing evidence."""

from fractions import Fraction
from itertools import product
import random
import unittest

from lsw_range import Interval, compile_interval, solve_glucose, solve_intervals


METHODS = ("local", "global", "gap", "reference")


def enumerate_bounds(rows, domain, budgets):
    """Enumerate original-row paths without using solver reductions/helpers."""
    lower, upper = domain
    answers = [[None, None] for _ in budgets]
    for path in product(range(lower, upper + 1), repeat=len(rows)):
        variation = sum(abs(right - left) for left, right in zip(path, path[1:]))
        score = sum(
            row.weight for row, offset in zip(rows, path)
            if row.lower <= offset <= row.upper
        )
        for answer, budget in zip(answers, budgets):
            if variation <= budget:
                answer[0] = score if answer[0] is None else min(answer[0], score)
                answer[1] = score if answer[1] is None else max(answer[1], score)
    return tuple(tuple(answer) for answer in answers)


class ExactnessTests(unittest.TestCase):
    def check_all(self, rows, domain, budgets):
        expected = enumerate_bounds(rows, domain, budgets)
        for method in METHODS:
            with self.subTest(method=method, rows=rows, domain=domain, budgets=budgets):
                result = solve_intervals(rows, domain=domain, budgets=budgets, method=method)
                self.assertEqual(tuple(result.bounds), expected)
        return expected

    def test_empty_input_and_single_state(self):
        self.check_all([], (-2, 2), [0, 1, 4, 0])
        rows = [Interval(-8, 8, 2), Interval(1, 0, 5), Interval(0, 0, 3)]
        self.check_all(rows, (0, 0), [0, 1, 99])

    def test_exhaustive_tiny_interval_sequences(self):
        # Every empty or nonempty interval on a three-state domain, in every
        # order through length three. The oracle keeps all original states.
        alphabet = [Interval(1, 0)] + [
            Interval(lo, hi) for lo in range(-1, 2) for hi in range(lo, 2)
        ]
        for length in range(4):
            for rows in product(alphabet, repeat=length):
                self.check_all(rows, (-1, 1), [0, 1, 2, 5, 1, 0])

    def test_weighted_and_clipped_paths(self):
        generator = random.Random(20261106)
        alphabet = [(-8, 8), (1, 0), (-8, -1), (-1, 0), (0, 0), (1, 8)]
        for _ in range(75):
            rows = [
                Interval(*generator.choice(alphabet), generator.choice([0, 1, 2, 5]))
                for _ in range(generator.randrange(1, 6))
            ]
            self.check_all(rows, (-1, 1), [4, 0, 1, 2, 1])

    def test_rational_weights(self):
        rows = [
            Interval(-1, -1, Fraction(1, 3)),
            Interval(0, 1, Fraction(7, 5)),
            Interval(0, 1, Fraction(2, 7)),
            Interval(-5, 5, Fraction(4, 9)),
        ]
        self.check_all(rows, (-1, 1), [0, 1, 2, 6])

    def test_one_shared_budget_and_free_endpoints(self):
        rows = [Interval(0, 0), Interval(1, 1)]
        expected = self.check_all(rows, (0, 1), [0, 1])
        self.assertEqual(expected, ((1, 1), (0, 2)))
        self.assertEqual(self.check_all([Interval(3, 3)], (0, 3), [0]), ((0, 1),))

    def test_zero_reward_gaps_do_not_reset_budget(self):
        rows = [Interval(0, 0, 2), Interval(0, 1, 0), Interval(1, 1, 3)]
        self.assertEqual(self.check_all(rows, (0, 1), [0, 1]), ((2, 3), (0, 5)))

    def test_fixed_deletion_then_run_contraction(self):
        rows = [
            Interval(0, 0, 2), Interval(-8, 8, 7), Interval(1, 0, 9),
            Interval(0, 0, 3), Interval(1, 1, 4), Interval(1, 1, 5),
        ]
        self.check_all(rows, (0, 1), [0, 1, 2, 5])

    def test_critical_support_keeps_physical_distance(self):
        rows = [Interval(0, 0), Interval(10, 10)]
        self.assertEqual(
            self.check_all(rows, (0, 10), [0, 1, 9, 10]),
            ((0, 1), (0, 1), (0, 1), (0, 2)),
        )
        self.check_all([Interval(0, 9)], (0, 10), [0, 1, 10])

    def test_overlapping_local_windows_share_one_budget_bank(self):
        rows = [
            Interval(-4, -2, 2), Interval(-1, 1, 3),
            Interval(2, 4, 5), Interval(-4, -2, 7),
        ]
        self.check_all(rows, (-4, 4), [0, 1, 2, 4, 1])

    def test_large_coordinate_amplitude_uses_sparse_support(self):
        # An analytic case whose raw domain cannot usefully be enumerated.
        # In four units no path can visit both singleton hit coordinates.
        far = 10**12
        rows = [Interval(-far, -far, 2), Interval(far, far, 3)]
        for method in ("local", "global", "gap"):
            result = solve_intervals(rows, domain=(-far, far), budgets=[0, 1, 4], method=method)
            self.assertEqual(tuple(result.bounds), ((0, 3), (0, 3), (0, 3)))

    def test_budget_one_specialization_and_local_support(self):
        rows = [
            Interval(-5, -1, 2), Interval(0, 4, 3), Interval(-5, -1, 5),
            Interval(0, 4, 7), Interval(-5, 4, 11), Interval(1, 0, 13),
        ]
        expected = enumerate_bounds(rows, (-2, 2), [1, 0, 1])
        for specialize in [False, True]:
            for support in [False, True]:
                result = solve_intervals(
                    rows, domain=(-2, 2), budgets=[1, 0, 1], method="local",
                    specialize_v1=specialize, local_support=support,
                )
                self.assertEqual(tuple(result.bounds), expected)


class PredicateCompilationTests(unittest.TestCase):
    def assert_membership(self, value, lower, upper, domain, lower_closed, upper_closed):
        interval = compile_interval(
            value, lower, upper, domain,
            lower_closed=lower_closed, upper_closed=upper_closed,
        )
        for offset in range(domain[0], domain[1] + 1):
            corrected = value - offset
            above = lower is None or (corrected >= lower if lower_closed else corrected > lower)
            below = upper is None or (corrected <= upper if upper_closed else corrected < upper)
            self.assertEqual(interval.lower <= offset <= interval.upper, above and below)

    def test_open_closed_fractional_and_unbounded(self):
        for value in [69.5, 70, 70.5, 139.5, 140, 140.5]:
            for lower, upper in [(70, 140), (None, 70), (140, None), (None, None), (70, 70)]:
                for lower_closed, upper_closed in product([False, True], repeat=2):
                    self.assert_membership(value, lower, upper, (-3, 3), lower_closed, upper_closed)

    def test_glucose_matches_direct_original_row_oracle(self):
        values = [69.5, 70, 71, 140, 140.5]
        weights = [1, 0, 2, 3, 4]
        domain = (-1, 1)
        budgets = [0, 1, 3, 1]
        # Direct reward logic, independently compiled into singleton/interval
        # sets by enumerating the tiny domain rather than calling compile_interval.
        rows = []
        for value, weight in zip(values, weights):
            hits = [x for x in range(-1, 2) if 70 < value - x <= 140]
            rows.append(Interval(min(hits), max(hits), weight) if hits else Interval(1, 0, weight))
        expected = enumerate_bounds(rows, domain, budgets)
        for method in METHODS:
            result = solve_glucose(
                values, lower=70, upper=140, lower_closed=False, upper_closed=True,
                weights=weights, domain=domain, budgets=budgets, method=method,
            )
            self.assertEqual(tuple(result.bounds), expected)


class ValidationTests(unittest.TestCase):
    def test_invalid_requests_fail_explicitly(self):
        cases = [
            {"domain": (1, 0), "budgets": [0]},
            {"domain": (0, 1), "budgets": []},
            {"domain": (0, 1), "budgets": [-1]},
            {"domain": (0, 1), "budgets": [0.5]},
            {"domain": (0.5, 1), "budgets": [0]},
            {"domain": (0, 1), "budgets": [0], "method": "unknown"},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, TypeError)):
                solve_intervals([Interval(0, 0)], **kwargs)
        for weight in [-1, float("nan"), float("inf")]:
            with self.subTest(weight=weight), self.assertRaises((ValueError, TypeError)):
                solve_intervals([Interval(0, 0, weight)], domain=(0, 1), budgets=[0])

    def test_weight_length_mismatch(self):
        with self.assertRaises((ValueError, TypeError)):
            solve_glucose([70, 140], lower=70, upper=140, domain=(-1, 1), budgets=[0], weights=[1])


if __name__ == "__main__":
    unittest.main()
