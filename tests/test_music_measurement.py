import unittest

import numpy as np

from isac_uav.geometry import build_vsc, measurement_function, state_from_position_velocity
from isac_uav.music_measurement import (
    MusicMeasurementGrids,
    generate_multi_target_music_measurements,
    generate_music_measurement,
)
from isac_uav.signal_music import RadarConfig


class MusicMeasurementTest(unittest.TestCase):
    def test_music_measurement_matches_table_i_vector(self):
        vsc = build_vsc()
        state = state_from_position_velocity(
            np.array([170.0, -35.0, 82.0]),
            np.array([4.0, 13.0, 0.8]),
        )
        clean = measurement_function(state, vsc, pbs_index=0)
        measured = generate_music_measurement(
            state,
            vsc,
            pbs_index=0,
            radar_config=RadarConfig(),
            grids=MusicMeasurementGrids(
                theta_half_width=np.deg2rad(3.0),
                phi_half_width=np.deg2rad(3.0),
                range_half_width=6.0,
                velocity_half_width=4.0,
                theta_points=13,
                phi_points=13,
                range_points=25,
                velocity_points=33,
            ),
            seed=12,
        )

        angle_error = np.abs(measured[[0, 1, 4, 5, 8, 9]] - clean[[0, 1, 4, 5, 8, 9]])
        range_velocity_error = np.abs(measured[[2, 3, 6, 7, 10, 11]] - clean[[2, 3, 6, 7, 10, 11]])
        self.assertLess(np.rad2deg(angle_error).max(), 0.6)
        self.assertLess(range_velocity_error.max(), 0.6)

    def test_multi_target_music_measurements_match_table_i_vectors(self):
        vsc = build_vsc()
        states = np.asarray(
            [
                state_from_position_velocity(np.array([155.0, -40.0, 78.0]), np.array([3.0, 14.0, 0.7])),
                state_from_position_velocity(np.array([240.0, 70.0, 92.0]), np.array([-8.0, 9.0, -0.4])),
            ]
        )
        clean = np.asarray([measurement_function(state, vsc, pbs_index=0) for state in states])
        measured = generate_multi_target_music_measurements(
            states,
            vsc,
            pbs_index=0,
            radar_config=RadarConfig(n_symbols=256),
            grids=MusicMeasurementGrids(
                theta_half_width=np.deg2rad(0.5),
                phi_half_width=np.deg2rad(0.5),
                theta_points=17,
                phi_points=17,
                range_half_width=8.0,
                velocity_half_width=5.0,
                velocity_points=121,
            ),
            seed=20,
        )

        angle_error = np.abs(measured[:, [0, 1, 4, 5, 8, 9]] - clean[:, [0, 1, 4, 5, 8, 9]])
        range_velocity_error = np.abs(measured[:, [2, 3, 6, 7, 10, 11]] - clean[:, [2, 3, 6, 7, 10, 11]])
        self.assertLess(np.rad2deg(angle_error).max(), 0.6)
        self.assertLess(range_velocity_error.max(), 2.0)


if __name__ == "__main__":
    unittest.main()
