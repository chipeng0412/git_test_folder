import unittest

from isac_uav.experiments import ExperimentConfig, run_tracking_experiment


class ExperimentTest(unittest.TestCase):
    def test_short_multi_uav_experiment_runs(self):
        result = run_tracking_experiment(
            ExperimentConfig(scenario="multi", steps=24, dt=0.2, seed=3, save_plots=False)
        )
        self.assertEqual(result.true_states.shape, result.estimated_states.shape)
        self.assertEqual(result.pbs_history.shape, (2, 24))
        self.assertLess(result.rmse_position.mean(), 20.0)

    def test_single_uav_scenario_ignores_default_num_uavs(self):
        result = run_tracking_experiment(
            ExperimentConfig(scenario="blockage", steps=24, dt=0.2, seed=3, save_plots=False)
        )
        self.assertEqual(result.pbs_history.shape, (1, 24))
        self.assertEqual(result.pbs_label_history.shape, (1, 24))

    def test_music_backed_single_uav_tracking_runs(self):
        result = run_tracking_experiment(
            ExperimentConfig(
                scenario="vsc",
                steps=26,
                dt=0.2,
                seed=7,
                measurement_source="music",
                save_plots=False,
            )
        )
        self.assertEqual(result.pbs_history.shape, (1, 26))
        self.assertIn("2-3", set(result.pbs_label_history.ravel()))
        self.assertLess(result.rmse_position.mean(), 3.0)

    def test_vsc_handover_uses_paper_style_sector_labels(self):
        result = run_tracking_experiment(
            ExperimentConfig(scenario="vsc", steps=32, dt=0.2, seed=7, save_plots=False)
        )
        labels = set(result.pbs_label_history.ravel())
        self.assertIn("1-1", labels)
        self.assertIn("2-3", labels)
        switched = result.pbs_label_history[0] == "2-3"
        self.assertTrue(switched.any())
        self.assertTrue((result.vsc_history[0, switched] == 1).all())
        self.assertTrue((result.pbs_history[0, switched] == 2).all())

    def test_music_backed_multi_uav_tracking_runs(self):
        result = run_tracking_experiment(
            ExperimentConfig(
                scenario="multi",
                steps=8,
                dt=0.2,
                seed=3,
                measurement_source="music",
                save_plots=False,
            )
        )
        self.assertEqual(result.pbs_history.shape, (2, 8))
        self.assertLess(result.rmse_position.mean(), 4.0)


if __name__ == "__main__":
    unittest.main()
