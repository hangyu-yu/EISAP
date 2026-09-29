import contextlib
import io
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile
import unittest
import warnings
from matplotlib import MatplotlibDeprecationWarning
import matplotlib.pyplot as plt

from src.Methods.DRT.DRT import DRT, _parse_tknv_sheet, _tknv_export_frame
from src.Methods.CNLS.Utils.DataReference import resolve_cnls_reference
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

    def test_export_frame_keeps_gamma_and_impedance_axes_separate(self):
        mode_data = {
            "f": np.array([1000.0, 31.62, 1.0, 0.1]),
            "f_gamma": np.array([1000.0, 31.62, 1.0, 0.1]),
            "f_Z": np.array([1000.0, 10.0, 1.0]),
            "g": np.array([0.1, 0.2, 0.3, 0.4]),
            "Re": np.array([1.1, 1.2, 1.3]),
            "Im": np.array([-0.1, -0.2, -0.3]),
            "Residuals": np.array([0.01, 0.02, 0.03]),
        }

        frame = _tknv_export_frame(mode_data)

        self.assertEqual(
            frame.columns.tolist(),
            [
                "Frequency_gamma/Hz",
                "gamma/ohm·s·cm2",
                "Frequency_Z/Hz",
                "Re/ohm·cm2",
                "Im/ohm·cm2",
                "Residuals",
            ],
        )
        self.assertEqual(
            frame["Frequency_gamma/Hz"].dropna().tolist(),
            [1000.0, 31.62, 1.0, 0.1],
        )
        self.assertEqual(
            frame["Frequency_Z/Hz"].dropna().tolist(),
            [1000.0, 10.0, 1.0],
        )

    def test_parse_new_sheet_restores_both_axes_without_warning(self):
        frame = pd.DataFrame(
            {
                "Frequency_gamma/Hz": [1000.0, 31.62, 1.0],
                "gamma/ohm·s·cm2": [0.1, 0.2, 0.3],
                "Frequency_Z/Hz": [1000.0, 10.0, 1.0],
                "Re/ohm·cm2": [1.1, 1.2, 1.3],
                "Im/ohm·cm2": [-0.1, -0.2, -0.3],
                "Residuals": [0.01, 0.02, 0.03],
            }
        )

        parsed, is_legacy = _parse_tknv_sheet(frame)

        self.assertFalse(is_legacy)
        np.testing.assert_allclose(parsed["f"], [1000.0, 31.62, 1.0])
        np.testing.assert_allclose(parsed["f_gamma"], [1000.0, 31.62, 1.0])
        np.testing.assert_allclose(parsed["f_Z"], [1000.0, 10.0, 1.0])

    def test_parse_legacy_sheet_loads_with_ambiguous_axis_warning(self):
        frame = pd.DataFrame(
            {
                "Frequency/Hz": [1000.0, 31.62, 1.0],
                "gamma/ohm·s·cm2": [0.1, 0.2, 0.3],
                "Re/ohm·cm2": [1.1, 1.2, 1.3],
                "Im/ohm·cm2": [-0.1, -0.2, -0.3],
                "Residuals": [0.01, 0.02, 0.03],
            }
        )

        parsed, is_legacy = _parse_tknv_sheet(frame)

        self.assertTrue(is_legacy)
        np.testing.assert_allclose(parsed["f"], frame["Frequency/Hz"])
        np.testing.assert_allclose(parsed["f_gamma"], frame["Frequency/Hz"])
        np.testing.assert_allclose(parsed["f_Z"], frame["Frequency/Hz"])

    def test_import_legacy_workbook_records_affected_sheet(self):
        legacy_frame = pd.DataFrame(
            {
                "Frequency/Hz": [1000.0, 31.62, 1.0],
                "gamma/ohm·s·cm2": [0.1, 0.2, 0.3],
                "Re/ohm·cm2": [1.1, 1.2, 1.3],
                "Im/ohm·cm2": [-0.1, -0.2, -0.3],
                "Residuals": [0.01, 0.02, 0.03],
            }
        )
        resistance_frame = pd.DataFrame(
            {
                "L/ohm·cm2 - DRT_Re": [0.0],
                "Rohm/ohm·cm2 DRT_Re": [0.2],
                "Rp/ohm·cm2 DRT_Re": [1.0],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            drt_dir = Path(temp_dir) / "DRT"
            drt_dir.mkdir()
            workbook = drt_dir / "sample.xlsx"
            with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
                pd.DataFrame({"lambda": [1e-4]}).to_excel(
                    writer, sheet_name="DRT_Parameters", index=False
                )
                legacy_frame.to_excel(writer, sheet_name="Tknv_Re", index=False)
                resistance_frame.to_excel(
                    writer, sheet_name="Resistance_truncated", index=False
                )

            drt = DRT(file_folder=temp_dir, filename="sample.csv")
            with contextlib.redirect_stdout(io.StringIO()):
                imported = drt.import_data_DRT()

        self.assertTrue(imported)
        self.assertTrue(drt.legacy_drt_frequency_warning)
        self.assertEqual(drt.legacy_drt_frequency_sheets, ["Tknv_Re"])
        np.testing.assert_allclose(
            drt.tknv_truncated["Re"]["f_Z"],
            legacy_frame["Frequency/Hz"],
        )

    def test_cnls_uses_gamma_axis_for_drt_and_impedance_axis_for_z(self):
        eis_data = {
            "tknv_truncated": {
                "ReIm": {
                    "f": np.array([777.0, 77.0, 7.0]),
                    "f_gamma": np.array([1000.0, 100.0, 10.0]),
                    "f_Z": np.array([1000.0, 10.0, 1.0]),
                    "g": np.array([0.1, 0.2, 0.3]),
                    "Re": np.array([1.1, 1.2, 1.3]),
                    "Im": np.array([-0.1, -0.2, -0.3]),
                },
                "RL": {},
            }
        }

        reference = resolve_cnls_reference(
            eis_data,
            "smooth_DRT",
            allow_rbf_fallback=False,
        )

        np.testing.assert_allclose(reference["drt_f"], [1000.0, 100.0, 10.0])
        np.testing.assert_allclose(reference["z_f"], [1000.0, 10.0, 1.0])

    def test_drt_plots_use_the_axis_matching_the_plotted_values(self):
        plt.switch_backend("Agg")
        plt.close("all")
        drt = DRT()
        drt.tknv_truncated = {
            "Re": {
                "f": np.array([777.0, 77.0, 7.0]),
                "f_gamma": np.array([1000.0, 100.0, 10.0]),
                "f_Z": np.array([1000.0, 10.0, 1.0]),
                "g": np.array([0.1, 0.2, 0.3]),
                "Re": np.array([1.1, 1.2, 1.3]),
                "Im": np.array([-0.1, -0.2, -0.3]),
            },
            "ReIm": {
                "f": np.array([777.0, 77.0, 7.0]),
                "f_gamma": np.array([1000.0, 100.0, 10.0]),
                "f_Z": np.array([1000.0, 10.0, 1.0]),
                "g": np.array([0.1, 0.2, 0.3]),
            },
        }
        drt.truncated = {
            "f": np.array([1000.0, 10.0, 1.0]),
            "Re": np.array([1.0, 1.1, 1.2]),
            "Im": np.array([-0.1, -0.2, -0.3]),
        }

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", MatplotlibDeprecationWarning)
            drt.DRT_plot("ReIm", figure_name="axis-test")
            gamma_x = plt.figure("ReIm").axes[0].lines[0].get_xdata()
            np.testing.assert_allclose(gamma_x, [1000.0, 100.0, 10.0])

            drt.DRT_EIS_plot(["Re"], figure_name="axis-test")
            impedance_x = plt.figure("DRTRe--axis-test").axes[0].lines[0].get_xdata()
            np.testing.assert_allclose(impedance_x, [1000.0, 10.0, 1.0])


if __name__ == "__main__":
    unittest.main()
