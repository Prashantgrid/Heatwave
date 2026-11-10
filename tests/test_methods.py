import unittest
import numpy as np
from heatwave.credibility import gaussian_posterior
from heatwave.risk import empirical_tail, funding_shortfall


class CredibilityTests(unittest.TestCase):
    def test_scalar_conjugate_result(self):
        m, c = gaussian_posterior([5], [[9]], [8], [[4]])
        self.assertAlmostEqual(m[0], 5 + 9 / 13 * 3)
        self.assertAlmostEqual(c[0, 0], 36 / 13)

    def test_spatial_posterior_matches_precision_identity(self):
        s = np.array([[9., 5.], [5., 9.]])
        r = np.diag([4., 4.])
        m, c = gaussian_posterior([0, 0], s, [3, -1], r)
        precision = np.linalg.inv(s) + np.linalg.inv(r)
        np.testing.assert_allclose(c, np.linalg.inv(precision))
        np.testing.assert_allclose(m, np.linalg.solve(precision, np.linalg.solve(r, [3, -1])))
        self.assertGreater(c[0, 1], 0)

    def test_perfect_information_and_no_information_limits(self):
        s = np.array([[9., 5.], [5., 9.]])
        m, c = gaussian_posterior([1, 2], s, [3, 4], np.zeros((2, 2)))
        np.testing.assert_allclose(m, [3, 4])
        np.testing.assert_allclose(c, np.zeros((2, 2)), atol=1e-10)
        m, c = gaussian_posterior([1, 2], s, [3, 4], np.eye(2) * 1e12)
        np.testing.assert_allclose(m, [1, 2], atol=1e-9)
        np.testing.assert_allclose(c, s, atol=1e-9)

    def test_negative_covariance_rejected(self):
        with self.assertRaises(ValueError):
            gaussian_posterior([0], [[1]], [0], [[-1]])


class TailTests(unittest.TestCase):
    def test_atom_at_quantile_does_not_dilute_tail(self):
        # Quantile=0. Integrating only the upper 20% gives (100+0)/2=50.
        result = empirical_tail([0] * 9 + [100], .8)
        self.assertEqual(result["var"], 0)
        self.assertAlmostEqual(result["es"], 50)

    def test_fractional_tail_mass(self):
        self.assertAlmostEqual(empirical_tail([0, 10, 20, 30], .625)["es"], 80 / 3)

    def test_lower_capital_increases_held_out_shortfall(self):
        x = [0, 10, 20, 100]
        adequate = funding_shortfall(x, 20, 80)
        optimistic = funding_shortfall(x, 20, 10)
        self.assertEqual(adequate["shortfall_probability"], 0)
        self.assertEqual(optimistic["shortfall_probability"], .25)
        self.assertEqual(optimistic["expected_unfunded_loss"], 17.5)


if __name__ == "__main__":
    unittest.main()
