import math
import unittest

import pandas as pd

from heatwave.pv_reliability import CapacitorParameters, ThermalParameters, integrate_history


class PVHistoryTests(unittest.TestCase):
    def setUp(self):
        self.thermal = ThermalParameters(0.2, 2.0)
        self.capacitor = CapacitorParameters(60, 1000, 10)
        self.history = pd.DataFrame({
            "timestamp_utc": ["2022-07-17T00:00:00Z", "2022-07-17T01:00:00Z"],
            "duration_h": [1, 1],
            "ambient_c": [40, 40],
            "heat_loss_w": [100, 100],
        })

    def test_constant_reference_temperature_consumes_reference_life(self):
        result = integrate_history(self.history, self.thermal, self.capacitor, 60, 0.20)
        self.assertAlmostEqual(result["component_end_c"].iloc[-1], 60)
        self.assertAlmostEqual(result["life_used_fraction"].iloc[-1], 0.202)

    def test_temperature_uses_load_and_thermal_history(self):
        result = integrate_history(self.history, self.thermal, self.capacitor, 40, 0)
        self.assertAlmostEqual(result["component_end_c"].iloc[0], 60 - 20 * math.exp(-0.5))
        self.assertAlmostEqual(result["component_end_c"].iloc[1], 60 - 20 * math.exp(-1))

    def test_temperature_change_doubles_life_consumption_at_equilibrium(self):
        baseline = integrate_history(self.history, self.thermal, self.capacitor, 60, 0)
        warmer = self.history.assign(ambient_c=self.history["ambient_c"] + 10)
        future = integrate_history(warmer, self.thermal, self.capacitor, 70, 0)
        self.assertAlmostEqual(
            future["life_used_fraction"].iloc[-1],
            2 * baseline["life_used_fraction"].iloc[-1],
        )

    def test_rejects_unobserved_intervals(self):
        history = self.history.copy()
        history.loc[1, "timestamp_utc"] = "2022-07-17T02:00:00Z"
        with self.assertRaisesRegex(ValueError, "contiguous"):
            integrate_history(history, self.thermal, self.capacitor, 40, 0)


if __name__ == "__main__":
    unittest.main()
