import unittest

import numpy as np

from isac_uav.ekf import ExtendedKalmanFilter
from isac_uav.experiments import default_measurement_covariance
from isac_uav.geometry import build_vsc, measurement_function, state_from_position_velocity


class EkfTest(unittest.TestCase):
    def test_update_moves_state_toward_truth(self):
        vsc = build_vsc()
        truth = state_from_position_velocity(np.array([130.0, -40.0, 70.0]), np.array([3.0, 11.0, 0.5]))
        initial = truth + np.array([8.0, 1.0, -7.0, -1.0, 5.0, 0.5])
        ekf = ExtendedKalmanFilter(
            state=initial.copy(),
            covariance=20.0 * np.eye(6),
            process_cov=0.01 * np.eye(6),
            measurement_cov=default_measurement_covariance(),
            dt=0.2,
            measurement_fn=lambda state, pbs_index: measurement_function(state, vsc, pbs_index),
        )
        before = np.linalg.norm(ekf.state[[0, 2, 4]] - truth[[0, 2, 4]])
        z = measurement_function(truth, vsc, 0)
        ekf.update(z, np.arange(12), 0)
        after = np.linalg.norm(ekf.state[[0, 2, 4]] - truth[[0, 2, 4]])
        self.assertLess(after, before)


if __name__ == "__main__":
    unittest.main()
