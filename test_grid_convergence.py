import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from grid_convergence import analyze

ROOT = Path(__file__).resolve().parent


class GridConvergenceTests(unittest.TestCase):
    def test_second_order_in_random_row_order(self):
        result = analyze([(0.02, 1.03), (0.04, 1.12), (0.01, 1.0075)])
        self.assertAlmostEqual(result["observed_order"], 2)
        self.assertAlmostEqual(result["extrapolated_value"], 1)
        self.assertAlmostEqual(result["fine_gci_absolute"], 0.009375)
        self.assertAlmostEqual(result["fine_gci_percent"], 0.009375 / 1.0075 * 100)

    def test_negative_values_and_zero_reference(self):
        negative = analyze([(4, -1.12), (2, -1.03), (1, -1.0075)])
        self.assertAlmostEqual(negative["extrapolated_value"], -1)
        self.assertGreater(negative["fine_gci_percent"], 0)
        zero = analyze([(4, 5), (2, 1), (1, 0)])
        self.assertAlmostEqual(zero["fine_gci_absolute"], 1.25 / 3)
        self.assertIsNone(zero["fine_gci_percent"])

    def test_diagnostics_omit_estimates(self):
        for values, expected in [
            ((0, 2, 1), "oscillatory"),
            ((0, 2, 3), "differences-not-shrinking"),
            ((0, 0, 1), "repeated-values"),
        ]:
            with self.subTest(expected=expected):
                result = analyze(list(zip((1, 2, 4), values)))
                self.assertEqual(result["status"], expected)
                self.assertIsNone(result["observed_order"])
                self.assertIsNone(result["fine_gci_percent"])

    def test_invalid_grids(self):
        for grids in [
            [(1, 1)],
            [(1, 1), (1, 2), (4, 3)],
            [(1, 1), (2, 2), (5, 3)],
            [(0, 1), (2, 2), (4, 3)],
            [(1, math.nan), (2, 2), (4, 3)],
        ]:
            with self.subTest(grids=grids), self.assertRaises(ValueError):
                analyze(grids)

    def test_cli_json_and_exit_codes(self):
        def cli(path):
            return subprocess.run(
                [sys.executable, str(ROOT / "grid_convergence.py"), str(path), "--json"],
                capture_output=True, text=True, check=False,
            )

        run = cli(ROOT / "example.csv")
        self.assertEqual(run.returncode, 0)
        self.assertAlmostEqual(json.loads(run.stdout)["observed_order"], 2)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.csv"
            path.write_text("spacing,value\n1,0\n2,2\n4,1\n", encoding="utf-8")
            run = cli(path)
            self.assertEqual(run.returncode, 1)
            self.assertEqual(json.loads(run.stdout)["status"], "oscillatory")
            path.write_text("spacing,value\n1,2,3\n", encoding="utf-8")
            run = cli(path)
            self.assertEqual(run.returncode, 2)
            self.assertIn("line 2", run.stderr)
            self.assertFalse(run.stdout)


if __name__ == "__main__":
    unittest.main()
