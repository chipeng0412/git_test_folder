import unittest
from pathlib import Path
import tempfile

from isac_uav.detection_experiment import DetectionRmseConfig, run_detection_rmse_experiment


class DetectionExperimentTest(unittest.TestCase):
    def test_detection_rmse_experiment_runs(self):
        result = run_detection_rmse_experiment(
            DetectionRmseConfig(
                snr_db=(-10.0, 10.0),
                monte_carlo=2,
                seed=5,
                save_csv=False,
            )
        )
        self.assertEqual(result.snr_db.shape, (2,))
        self.assertEqual(result.rmse_theta_deg.shape, (2,))
        self.assertLess(result.rmse_range_m[-1], 1.0)

    def test_detection_rmse_writes_csv_and_figure(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_detection_rmse_experiment(
                DetectionRmseConfig(
                    snr_db=(10.0,),
                    monte_carlo=1,
                    seed=6,
                    output_dir=Path(tmp),
                    save_csv=True,
                )
            )
            self.assertIsNotNone(result.csv_path)
            self.assertIsNotNone(result.figure_path)
            self.assertTrue(result.csv_path.exists())
            self.assertTrue(result.figure_path.exists())

    def test_detection_rmse_can_write_csv_without_figure(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_detection_rmse_experiment(
                DetectionRmseConfig(
                    snr_db=(10.0,),
                    monte_carlo=1,
                    seed=7,
                    output_dir=Path(tmp),
                    save_csv=True,
                    save_figure=False,
                )
            )
            self.assertIsNotNone(result.csv_path)
            self.assertIsNone(result.figure_path)
            self.assertTrue(result.csv_path.exists())


if __name__ == "__main__":
    unittest.main()
