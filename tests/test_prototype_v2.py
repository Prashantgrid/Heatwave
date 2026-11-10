import unittest
import numpy as np
from prototype_v2 import sim, sim2
from heatwave.credibility import gaussian_posterior
from scripts.export_v2_events import severity_bins


class RevisedPrototypeTests(unittest.TestCase):
    def test_joint_posterior_matches_independent_reference(self):
        pf = sim.make_portfolio(np.random.default_rng(100))
        s = sim2.prior_cov(pf)
        m, factor = sim2.posterior(pf, 1.)
        expected_m, expected_p = gaussian_posterior(pf['mu_book'], s, pf['Hhat'], np.diag(pf['par']['s_twin']**2))
        np.testing.assert_allclose(m, expected_m)
        np.testing.assert_allclose(factor @ factor.T, expected_p + 1e-9 * np.eye(pf['N']), atol=1e-9)
        off_diagonal = expected_p - np.diag(np.diag(expected_p))
        self.assertGreater(np.max(off_diagonal), 0)

    def test_repeat_failures_count_as_one_distinct_site(self):
        fail = np.array([[True, False], [True, True], [False, True]])
        np.testing.assert_array_equal(sim._distinct_sites(np.array([0, 0, 1]), fail, 3), [2, 1, 0])

    def test_extreme_heatwave_is_not_dropped_from_bins(self):
        peaks = np.array([3., 5., 21.])
        baseline = np.array([[True, False], [True, True], [True, True]])
        treatment = np.array([[False, False], [True, False], [True, True]])
        rows = severity_bins(peaks, baseline, treatment)
        self.assertEqual(sum(r['events'] for r in rows), 3)
        self.assertEqual(rows[-1]['events'], 1)
        self.assertEqual(rows[-1]['class_failures'], 2)
        self.assertEqual(rows[-1]['net_reduction_fraction'], 0)

    def test_funding_compare_reuses_identical_physical_loss_target(self):
        r = sim2.experiment_v2(100, years=50)
        a = r['funding']['class op | class model']
        b = r['funding']['class op | twin model']
        self.assertEqual(a['true_var'], b['true_var'])
        self.assertEqual(r['model']['cc']['act'], r['model']['tc']['act'])
        self.assertEqual(r['truth']['class_op']['act'], r['model']['tc']['act'])


if __name__ == '__main__':
    unittest.main()
