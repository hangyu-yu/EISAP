import numpy as np
import unittest

from src.Methods.DRT.Utils.DRT_tikhonov import DRT_tikhonov
from src.Methods.DRT.Utils.DRT_tknv_pos import DRT_tknv_pos


SOLVERS = [
    ("ordinary", DRT_tikhonov),
    ("positive", DRT_tknv_pos),
]


def _gapped_eis_data():
    full_frequency = np.logspace(4, -2, 12)
    retained_frequency = np.delete(full_frequency, [2, 5, 8])
    omega = 2 * np.pi * retained_frequency
    tau_peak = 1 / (2 * np.pi * 3.0)
    impedance = 0.2 + 1.0 / (1 + 1j * omega * tau_peak)
    return {
        "f": retained_frequency.copy(),
        "Re": impedance.real.copy(),
        "Im": impedance.imag.copy(),
        "omega": omega.copy(),
        "tau": (1 / omega).copy(),
    }


class TikhonovFrequencyAxisTests(unittest.TestCase):
    def test_results_keep_distinct_gamma_and_impedance_axes(self):
        for solver_name, solver in SOLVERS:
            for branch in ("Re", "Im", "ReIm"):
                with self.subTest(solver=solver_name, branch=branch):
                    eis_data = _gapped_eis_data()
                    expected_f_z = eis_data["f"].copy()

                    result = solver(eis_data, {"lambda": 1e-4})[branch]

                    np.testing.assert_allclose(result["f_Z"], expected_f_z)
                    np.testing.assert_allclose(result["f"], result["f_gamma"])
                    self.assertFalse(np.allclose(result["f_gamma"], expected_f_z))

                    eis_data["f"][0] = -1.0
                    np.testing.assert_allclose(result["f_Z"], expected_f_z)


if __name__ == "__main__":
    unittest.main()
