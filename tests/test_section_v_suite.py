import csv
import tempfile
import unittest
from pathlib import Path

from isac_uav.section_v_suite import SectionVSuiteConfig, run_section_v_suite


class SectionVSuiteTest(unittest.TestCase):
    def test_section_v_suite_writes_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_section_v_suite(
                SectionVSuiteConfig(
                    steps=24,
                    detection_monte_carlo=1,
                    seed=4,
                    output_dir=Path(tmp),
                    save_plots=False,
                )
            )

            self.assertTrue(result.summary_csv.exists())
            self.assertTrue(result.report_md.exists())
            with result.summary_csv.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            scenarios = {row["scenario"] for row in rows}
            self.assertEqual(scenarios, {"detection-rmse", "multi", "blockage", "vsc"})
            multi = next(row for row in rows if row["scenario"] == "multi")
            self.assertGreater(float(multi["rmse_x_m"]), 0.0)
            self.assertEqual(multi["paper_rmse_x_m"], "0.350000")
            self.assertNotEqual(multi["delta_rmse_x_m"], "")
            blockage = next(row for row in rows if row["scenario"] == "blockage")
            self.assertIn("No complete numeric RMSE benchmark", blockage["paper_reference"])
            vsc = next(row for row in rows if row["scenario"] == "vsc")
            self.assertEqual(vsc["paper_rmse_vz_mps"], "0.670000")
            report = result.report_md.read_text(encoding="utf-8")
            self.assertIn("Section V 復現報告", report)
            self.assertIn("delta_rmse_*", report)
            self.assertIn("section_v_summary.csv", {path.name for path in result.generated_paths})


if __name__ == "__main__":
    unittest.main()
