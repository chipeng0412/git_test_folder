import math
import unittest

import numpy as np

from isac_uav.signal_music import (
    BISTATIC_SUM,
    RadarConfig,
    TargetParameters,
    apply_mti,
    estimate_angle_music_peaks,
    estimate_delay_doppler_peaks,
    estimate_single_target_parameters,
    match_delay_doppler_svd,
    synthesize_multi_target_echo,
    synthesize_beamformed_delay_doppler,
    synthesize_single_target_echo,
)


class SignalMusicTest(unittest.TestCase):
    def test_mti_removes_static_echo(self):
        static = np.ones((4, 8, 3), dtype=complex)
        dynamic = apply_mti(static)
        self.assertTrue(np.allclose(dynamic, 0.0))

    def test_single_target_music_estimation(self):
        config = RadarConfig(m_subcarriers=64, n_symbols=64, nx_rx=8, nz_rx=8)
        target = TargetParameters(
            theta=math.radians(75.0),
            phi=math.radians(18.0),
            distance=118.0,
            radial_velocity=14.0,
        )
        echo = synthesize_single_target_echo(target, config, snr_db=35.0, clutter_amplitude=8.0, seed=4)
        estimate = estimate_single_target_parameters(
            echo,
            config,
            theta_grid=np.deg2rad(np.linspace(65.0, 85.0, 41)),
            phi_grid=np.deg2rad(np.linspace(10.0, 26.0, 33)),
            distance_grid=np.linspace(108.0, 128.0, 81),
            velocity_grid=np.linspace(8.0, 20.0, 73),
        )

        self.assertLess(abs(math.degrees(estimate.theta - target.theta)), 1.0)
        self.assertLess(abs(math.degrees(estimate.phi - target.phi)), 1.0)
        self.assertLess(abs(estimate.distance - target.distance), 1.0)
        self.assertLess(abs(estimate.radial_velocity - target.radial_velocity), 0.5)

    def test_bistatic_sum_music_estimation(self):
        config = RadarConfig(m_subcarriers=64, n_symbols=64, nx_rx=8, nz_rx=8)
        target = TargetParameters(
            theta=math.radians(82.0),
            phi=math.radians(16.0),
            range_value=255.0,
            velocity_value=-18.0,
        )
        echo = synthesize_single_target_echo(
            target,
            config,
            mode=BISTATIC_SUM,
            snr_db=35.0,
            clutter_amplitude=8.0,
            seed=8,
        )
        estimate = estimate_single_target_parameters(
            echo,
            config,
            theta_grid=np.deg2rad(np.linspace(72.0, 92.0, 41)),
            phi_grid=np.deg2rad(np.linspace(8.0, 24.0, 33)),
            range_grid=np.linspace(245.0, 265.0, 81),
            velocity_grid=np.linspace(-24.0, -12.0, 73),
            mode=BISTATIC_SUM,
        )

        self.assertLess(abs(math.degrees(estimate.theta - target.theta)), 1.0)
        self.assertLess(abs(math.degrees(estimate.phi - target.phi)), 1.0)
        self.assertLess(abs(estimate.range_value - target.range_value), 1.0)
        self.assertLess(abs(estimate.velocity_value - target.velocity_value), 0.5)

    def test_svd_matches_multi_target_delay_doppler_pairs(self):
        config = RadarConfig(m_subcarriers=64, n_symbols=64, nx_rx=8, nz_rx=8)
        targets = [
            TargetParameters(theta=0.0, phi=0.0, range_value=115.0, velocity_value=12.0),
            TargetParameters(theta=0.0, phi=0.0, range_value=145.0, velocity_value=-18.0),
        ]
        echo = synthesize_beamformed_delay_doppler(
            targets,
            config,
            snr_db=45.0,
            amplitudes=np.asarray([1.0, 0.65]),
            seed=11,
        )
        range_grid = np.linspace(105.0, 155.0, 101)
        velocity_grid = np.linspace(-24.0, 18.0, 85)
        tau_grid = 2.0 * range_grid / 299_792_458.0
        fd_grid = 2.0 * config.f0 * velocity_grid / 299_792_458.0
        tau_candidates, fd_candidates, _, _ = estimate_delay_doppler_peaks(
            echo,
            config,
            tau_grid=tau_grid,
            fd_grid=fd_grid,
            n_targets=2,
        )
        matches = match_delay_doppler_svd(echo, config, tau_candidates, fd_candidates, n_targets=2)
        recovered = sorted(
            [
                (
                    round(match.tau * 299_792_458.0 / 2.0, 1),
                    round(match.fd * 299_792_458.0 / (2.0 * config.f0), 1),
                )
                for match in matches
            ]
        )

        self.assertEqual(recovered, [(115.0, 12.0), (145.0, -18.0)])

    def test_multi_target_angle_music_peaks(self):
        config = RadarConfig(m_subcarriers=64, n_symbols=64, nx_rx=8, nz_rx=8)
        targets = [
            TargetParameters(theta=math.radians(62.0), phi=math.radians(14.0), range_value=120.0, velocity_value=12.0),
            TargetParameters(theta=math.radians(82.0), phi=math.radians(22.0), range_value=145.0, velocity_value=-16.0),
        ]
        echo = synthesize_multi_target_echo(
            targets,
            config,
            snr_db=40.0,
            clutter_amplitude=8.0,
            amplitudes=np.asarray([1.0, 0.75]),
            seed=13,
        )
        theta_peaks, phi_peaks, _ = estimate_angle_music_peaks(
            apply_mti(echo),
            config,
            theta_grid=np.deg2rad(np.linspace(55.0, 90.0, 71)),
            phi_grid=np.deg2rad(np.linspace(10.0, 26.0, 65)),
            n_targets=2,
        )
        recovered = sorted((round(math.degrees(theta), 1), round(math.degrees(phi), 1)) for theta, phi in zip(theta_peaks, phi_peaks))

        self.assertEqual(recovered, [(62.0, 14.0), (82.0, 22.0)])


if __name__ == "__main__":
    unittest.main()
