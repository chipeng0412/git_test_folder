from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.constants import c

from .geometry import VSC, measurement_function
from .signal_music import (
    BISTATIC_SUM,
    MONOSTATIC,
    EchoMode,
    RadarConfig,
    TargetParameters,
    apply_mti,
    estimate_angle_music,
    estimate_delay_doppler_peaks,
    estimate_single_target_parameters,
    match_delay_doppler_svd,
    synthesize_beamformed_delay_doppler,
    synthesize_multi_target_echo,
    synthesize_single_target_echo,
)


@dataclass(frozen=True)
class MusicMeasurementGrids:
    theta_half_width: float = math.radians(4.0)
    phi_half_width: float = math.radians(4.0)
    range_half_width: float = 8.0
    velocity_half_width: float = 6.0
    theta_points: int = 17
    phi_points: int = 17
    range_points: int = 33
    velocity_points: int = 49


def generate_music_measurement(
    true_state: np.ndarray,
    vsc: VSC,
    pbs_index: int,
    radar_config: RadarConfig,
    grids: MusicMeasurementGrids | None = None,
    snr_db: float = 35.0,
    clutter_amplitude: float = 8.0,
    seed: int = 0,
) -> np.ndarray:
    """Generate the paper's 12-D measurement vector through MTI + MUSIC.

    This is still a single-UAV implementation. It estimates PBS as monostatic
    range/velocity and SBSs as bistatic range-sum/velocity-sum, matching Table I.
    """

    grids = grids or MusicMeasurementGrids()
    clean = measurement_function(true_state, vsc, pbs_index)
    pbs = _estimate_role(clean[0:4], radar_config, grids, MONOSTATIC, snr_db, clutter_amplitude, seed)
    sbs1 = _estimate_role(clean[4:8], radar_config, grids, BISTATIC_SUM, snr_db, clutter_amplitude, seed + 1)
    sbs2 = _estimate_role(clean[8:12], radar_config, grids, BISTATIC_SUM, snr_db, clutter_amplitude, seed + 2)
    return np.asarray([*pbs, *sbs1, *sbs2], dtype=float)


def generate_multi_target_music_measurements(
    true_states: np.ndarray,
    vsc: VSC,
    pbs_index: int,
    radar_config: RadarConfig,
    grids: MusicMeasurementGrids | None = None,
    snr_db: float = 40.0,
    seed: int = 0,
) -> np.ndarray:
    """Generate K Table-I measurement vectors with multi-target SVD matching.

    This advances the signal-chain reproduction by using Algorithm 1 for
    distance-Doppler pairing. Angle estimates still use per-target geometric
    windows; full multi-target 2D angle peak association remains separate work.
    """

    grids = grids or MusicMeasurementGrids()
    clean = np.asarray([measurement_function(state, vsc, pbs_index) for state in true_states], dtype=float)
    measurements = np.zeros_like(clean)
    measurements[:, 0:4] = _estimate_role_multi(clean[:, 0:4], radar_config, grids, MONOSTATIC, snr_db, seed)
    measurements[:, 4:8] = _estimate_role_multi(clean[:, 4:8], radar_config, grids, BISTATIC_SUM, snr_db, seed + 1)
    measurements[:, 8:12] = _estimate_role_multi(clean[:, 8:12], radar_config, grids, BISTATIC_SUM, snr_db, seed + 2)
    return measurements


def _estimate_role(
    role_measurement: np.ndarray,
    radar_config: RadarConfig,
    grids: MusicMeasurementGrids,
    mode: EchoMode,
    snr_db: float,
    clutter_amplitude: float,
    seed: int,
) -> tuple[float, float, float, float]:
    theta, phi, velocity_value, range_value = [float(x) for x in role_measurement]
    target = TargetParameters(theta=theta, phi=phi, range_value=range_value, velocity_value=velocity_value)
    echo = synthesize_single_target_echo(target, radar_config, mode=mode, snr_db=snr_db, clutter_amplitude=clutter_amplitude, seed=seed)
    estimate = estimate_single_target_parameters(
        echo,
        radar_config,
        theta_grid=_grid(theta, grids.theta_half_width, grids.theta_points),
        phi_grid=_grid(phi, grids.phi_half_width, grids.phi_points),
        range_grid=_grid(range_value, grids.range_half_width, grids.range_points),
        velocity_grid=_grid(velocity_value, grids.velocity_half_width, grids.velocity_points),
        mode=mode,
    )
    return estimate.theta, estimate.phi, estimate.velocity_value, estimate.range_value


def _estimate_role_multi(
    role_measurements: np.ndarray,
    radar_config: RadarConfig,
    grids: MusicMeasurementGrids,
    mode: EchoMode,
    snr_db: float,
    seed: int,
) -> np.ndarray:
    n_targets = role_measurements.shape[0]
    targets = [
        TargetParameters(
            theta=float(row[0]),
            phi=float(row[1]),
            velocity_value=float(row[2]),
            range_value=float(row[3]),
        )
        for row in role_measurements
    ]
    echo = synthesize_beamformed_delay_doppler(
        targets,
        radar_config,
        mode=mode,
        snr_db=snr_db,
        amplitudes=np.linspace(1.0, 0.7, n_targets),
        seed=seed,
    )
    angle_echo = synthesize_multi_target_echo(
        targets,
        radar_config,
        mode=mode,
        snr_db=snr_db,
        clutter_amplitude=8.0,
        amplitudes=np.linspace(1.0, 0.7, n_targets),
        seed=seed + 100,
    )
    angle_estimates = _estimate_angles_in_gates(
        apply_mti(angle_echo),
        role_measurements[:, 0:2],
        radar_config,
        grids,
        n_targets,
    )
    range_grid = _multi_grid(role_measurements[:, 3], grids.range_half_width, max(grids.range_points, 81))
    velocity_grid = _multi_grid(role_measurements[:, 2], grids.velocity_half_width, max(grids.velocity_points, 81))
    tau_grid = mode.delay_distance_factor * range_grid / c
    fd_grid = mode.doppler_velocity_factor * radar_config.f0 * velocity_grid / c
    tau_candidates, fd_candidates, _, _ = estimate_delay_doppler_peaks(
        echo,
        radar_config,
        tau_grid=tau_grid,
        fd_grid=fd_grid,
        n_targets=n_targets,
    )
    matches = match_delay_doppler_svd(echo, radar_config, tau_candidates, fd_candidates, n_targets=n_targets)
    matched_range_velocity = np.asarray(
        [
            [
                match.fd * c / (mode.doppler_velocity_factor * radar_config.f0),
                match.tau * c / mode.delay_distance_factor,
            ]
            for match in matches
        ],
        dtype=float,
    )
    order = _assign_range_velocity(role_measurements[:, 2:4], matched_range_velocity)
    estimated = np.zeros_like(role_measurements)
    for target_index, match_index in enumerate(order):
        estimated[target_index, 0:2] = angle_estimates[target_index]
        estimated[target_index, 2:4] = matched_range_velocity[match_index]
    return estimated


def _grid(center: float, half_width: float, points: int) -> np.ndarray:
    return np.linspace(center - half_width, center + half_width, points)


def _multi_grid(values: np.ndarray, half_width: float, points: int) -> np.ndarray:
    return np.linspace(float(np.min(values) - half_width), float(np.max(values) + half_width), points)


def _assign_range_velocity(clean: np.ndarray, estimated: np.ndarray) -> list[int]:
    remaining = set(range(len(estimated)))
    order: list[int] = []
    scales = np.maximum(np.std(clean, axis=0), np.asarray([1.0, 1.0]))
    for target in clean:
        best = min(remaining, key=lambda index: float(np.linalg.norm((estimated[index] - target) / scales)))
        remaining.remove(best)
        order.append(best)
    return order


def _estimate_angles_in_gates(
    dynamic_echo: np.ndarray,
    angle_centers: np.ndarray,
    radar_config: RadarConfig,
    grids: MusicMeasurementGrids,
    n_targets: int,
) -> np.ndarray:
    estimates = np.zeros_like(angle_centers)
    for index, (theta, phi) in enumerate(angle_centers):
        theta_hat, phi_hat, _ = estimate_angle_music(
            dynamic_echo,
            radar_config,
            theta_grid=_grid(float(theta), grids.theta_half_width, max(grids.theta_points, 17)),
            phi_grid=_grid(float(phi), grids.phi_half_width, max(grids.phi_points, 17)),
            n_targets=n_targets,
        )
        estimates[index] = [theta_hat, phi_hat]
    return estimates
