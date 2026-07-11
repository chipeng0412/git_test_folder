from __future__ import annotations

from dataclasses import dataclass, field
import itertools
from pathlib import Path
import math

import numpy as np

from .ekf import ExtendedKalmanFilter
from .geometry import VSC, VSCNetwork, build_adjacent_vsc_pair, build_vsc, measurement_function
from .handover import BlockageState, choose_vsc_index, select_pbs
from .measurement import Measurement, build_measurement_from_full, generate_measurement
from .music_measurement import (
    MusicMeasurementGrids,
    generate_multi_target_music_measurements,
    generate_music_measurement,
)
from .plots import plot_pbs_history, plot_tracking_3d, plot_tracking_components, plot_vsc_top_view
from .signal_music import RadarConfig
from .trajectory import Trajectory, simulate_trajectory


@dataclass(frozen=True)
class ExperimentConfig:
    scenario: str = "multi"
    steps: int = 180
    dt: float = 0.2
    seed: int = 7
    num_uavs: int = 2
    measurement_source: str = "analytic"
    output_dir: Path = Path("outputs")
    save_plots: bool = True


@dataclass(frozen=True)
class ExperimentResult:
    config: ExperimentConfig
    true_states: np.ndarray
    estimated_states: np.ndarray
    pbs_history: np.ndarray
    vsc_history: np.ndarray
    pbs_label_history: np.ndarray
    rmse_position: np.ndarray
    rmse_velocity: np.ndarray
    figure_paths: tuple[Path, ...] = field(default_factory=tuple)
    single_bs_estimated_states: np.ndarray | None = None
    single_bs_rmse_position: np.ndarray | None = None
    single_bs_rmse_velocity: np.ndarray | None = None


def run_tracking_experiment(config: ExperimentConfig) -> ExperimentResult:
    vsc_network = build_adjacent_vsc_pair() if config.scenario == "vsc" else None
    vsc = vsc_network.vscs[0] if vsc_network is not None else build_vsc()
    rng = np.random.default_rng(config.seed + 1000)
    trajectories = _build_trajectories(config)
    num_tracks = len(trajectories)
    if config.measurement_source not in {"analytic", "music"}:
        raise ValueError("measurement_source must be 'analytic' or 'music'")

    true_states = np.stack([trajectory.states for trajectory in trajectories], axis=0)
    filters = [_init_filter(true_states[i, 0], vsc, config.dt) for i in range(num_tracks)]

    estimated = np.zeros_like(true_states)
    pbs_history = np.zeros((num_tracks, config.steps), dtype=int)
    vsc_history = np.zeros((num_tracks, config.steps), dtype=int)
    pbs_label_history = np.empty((num_tracks, config.steps), dtype=object)
    for i, ekf in enumerate(filters):
        active_vsc = _active_vsc(vsc_network, vsc, 0)
        estimated[i, 0] = ekf.state
        pbs_history[i, 0] = select_pbs(ekf.state, active_vsc)
        pbs_label_history[i, 0] = _pbs_label_for_time(active_vsc, pbs_history[i, 0])

    for t in range(1, config.steps):
        predicted_states: list[np.ndarray] = []
        pbs_indices: list[int] = []
        blockages: list[BlockageState] = []
        active_vscs: list[VSC] = []

        for tracker_id, ekf in enumerate(filters):
            predicted = ekf.predict()
            boundary_pbs_index = select_pbs(predicted, vsc)
            vsc_history[tracker_id, t] = _vsc_for_time(
                config.scenario,
                t,
                predicted,
                boundary_pbs_index,
                vsc_history[tracker_id, t - 1],
                vsc,
            )
            active_vsc = _active_vsc(vsc_network, vsc, vsc_history[tracker_id, t])
            blockage = _blockage_for(config.scenario, t, predicted, active_vsc)
            pbs_index = select_pbs(predicted, active_vsc, blockage)
            predicted_states.append(predicted.copy())
            pbs_indices.append(pbs_index)
            blockages.append(blockage)
            active_vscs.append(active_vsc)
            pbs_history[tracker_id, t] = pbs_index
            pbs_label_history[tracker_id, t] = _pbs_label_for_time(active_vsc, pbs_index)

        candidate_grid = _generate_candidate_grid(
            true_states[:, t, :],
            blockages,
            active_vscs,
            pbs_indices,
            rng,
            config,
            time_index=t,
        )
        assignment = _assign_measurements(predicted_states, candidate_grid, active_vscs, pbs_indices)

        for tracker_id, ekf in enumerate(filters):
            chosen = candidate_grid[tracker_id][assignment[tracker_id]]
            active_vsc = active_vscs[tracker_id]
            ekf.measurement_fn = lambda state, pbs_index, active_vsc=active_vsc: measurement_function(
                state, active_vsc, pbs_index
            )
            ekf.update(chosen.observed, chosen.active_indices, pbs_indices[tracker_id])
            estimated[tracker_id, t] = ekf.state

    rmse_position, rmse_velocity = _rmse(true_states, estimated)
    single_bs_estimated = _run_single_bs_baseline(true_states, vsc, config, rng)
    single_bs_rmse_position = None
    single_bs_rmse_velocity = None
    if single_bs_estimated is not None:
        single_bs_rmse_position, single_bs_rmse_velocity = _rmse(true_states, single_bs_estimated)
    figure_paths = _save_figures(
        config,
        vsc,
        vsc_network,
        true_states,
        estimated,
        single_bs_estimated,
        pbs_history,
        vsc_history,
        pbs_label_history,
    )
    return ExperimentResult(
        config=config,
        true_states=true_states,
        estimated_states=estimated,
        pbs_history=pbs_history,
        vsc_history=vsc_history,
        pbs_label_history=pbs_label_history,
        rmse_position=rmse_position,
        rmse_velocity=rmse_velocity,
        figure_paths=figure_paths,
        single_bs_estimated_states=single_bs_estimated,
        single_bs_rmse_position=single_bs_rmse_position,
        single_bs_rmse_velocity=single_bs_rmse_velocity,
    )


def default_measurement_covariance() -> np.ndarray:
    angle_sigma = math.radians(0.45)
    pbs_velocity_sigma = 0.85
    pbs_distance_sigma = 0.45
    sbs_velocity_sigma = 1.7
    sbs_distance_sigma = 0.9
    diag = np.asarray(
        [
            angle_sigma**2,
            angle_sigma**2,
            pbs_velocity_sigma**2,
            pbs_distance_sigma**2,
            angle_sigma**2,
            angle_sigma**2,
            sbs_velocity_sigma**2,
            sbs_distance_sigma**2,
            angle_sigma**2,
            angle_sigma**2,
            sbs_velocity_sigma**2,
            sbs_distance_sigma**2,
        ],
        dtype=float,
    )
    return np.diag(diag)


def _generate_experiment_measurement(
    true_state: np.ndarray,
    blockage: BlockageState,
    vsc: VSC,
    pbs_index: int,
    rng: np.random.Generator,
    config: ExperimentConfig,
    time_index: int,
    target_id: int,
) -> Measurement:
    if config.measurement_source == "analytic":
        return generate_measurement(true_state, default_measurement_covariance(), blockage, vsc, pbs_index, rng)

    full = generate_music_measurement(
        true_state,
        vsc,
        pbs_index,
        radar_config=RadarConfig(),
        grids=MusicMeasurementGrids(),
        snr_db=35.0,
        clutter_amplitude=8.0,
        seed=config.seed * 10000 + time_index * 100 + target_id * 10 + pbs_index,
    )
    return build_measurement_from_full(full, blockage, vsc, pbs_index)


def _generate_candidate_grid(
    true_states_at_time: np.ndarray,
    blockages: list[BlockageState],
    vscs: list[VSC],
    pbs_indices: list[int],
    rng: np.random.Generator,
    config: ExperimentConfig,
    time_index: int,
) -> list[list[Measurement]]:
    if config.measurement_source == "analytic":
        return [
            [
                _generate_experiment_measurement(
                    true_states_at_time[target_id],
                    blockages[tracker_id],
                    vscs[tracker_id],
                    pbs_indices[tracker_id],
                    rng,
                    config,
                    time_index=time_index,
                    target_id=target_id,
                )
                for target_id in range(len(true_states_at_time))
            ]
            for tracker_id in range(len(pbs_indices))
        ]

    if len(true_states_at_time) == 1:
        return [
            [
                _generate_experiment_measurement(
                    true_states_at_time[0],
                    blockages[tracker_id],
                    vscs[tracker_id],
                    pbs_indices[tracker_id],
                    rng,
                    config,
                    time_index=time_index,
                    target_id=0,
                )
            ]
            for tracker_id in range(len(pbs_indices))
        ]

    candidate_grid: list[list[Measurement]] = []
    for tracker_id, pbs_index in enumerate(pbs_indices):
        full_measurements = generate_multi_target_music_measurements(
            true_states_at_time,
            vscs[tracker_id],
            pbs_index,
            radar_config=RadarConfig(),
            grids=_music_grids_for_tracking(len(true_states_at_time)),
            snr_db=40.0,
            seed=config.seed * 10000 + time_index * 100 + tracker_id * 10 + pbs_index,
        )
        candidate_grid.append(
            [
                build_measurement_from_full(
                    full_measurements[target_id],
                    blockages[tracker_id],
                    vscs[tracker_id],
                    pbs_index,
                )
                for target_id in range(len(true_states_at_time))
            ]
        )
    return candidate_grid


def _init_filter(initial_true_state: np.ndarray, vsc: VSC, dt: float) -> ExtendedKalmanFilter:
    initial = initial_true_state.copy()
    initial[[0, 2, 4]] += np.array([2.0, -2.0, 1.5])
    initial[[1, 3, 5]] += np.array([0.5, -0.5, 0.2])
    return ExtendedKalmanFilter(
        state=initial,
        covariance=np.diag([25.0, 4.0, 25.0, 4.0, 16.0, 2.0]),
        process_cov=np.diag([0.08, 0.8, 0.08, 0.8, 0.04, 0.3]),
        measurement_cov=default_measurement_covariance(),
        dt=dt,
        measurement_fn=lambda state, pbs_index: measurement_function(state, vsc, pbs_index),
    )


def _run_single_bs_baseline(
    true_states: np.ndarray,
    vsc: VSC,
    config: ExperimentConfig,
    rng: np.random.Generator,
) -> np.ndarray | None:
    if config.scenario != "multi" or config.measurement_source != "analytic":
        return None

    fixed_pbs_index = 0
    active_indices = np.arange(0, 4, dtype=int)
    filters = [_init_filter(true_states[i, 0], vsc, config.dt) for i in range(true_states.shape[0])]
    estimated = np.zeros_like(true_states)
    for tracker_id, ekf in enumerate(filters):
        estimated[tracker_id, 0] = ekf.state

    noise_cov = default_measurement_covariance()
    for t in range(1, config.steps):
        for tracker_id, ekf in enumerate(filters):
            ekf.predict()
            clean = measurement_function(true_states[tracker_id, t], vsc, fixed_pbs_index)
            noise = rng.multivariate_normal(np.zeros(noise_cov.shape[0]), noise_cov)
            observed = (clean + noise)[active_indices]
            ekf.update(observed, active_indices, fixed_pbs_index)
            estimated[tracker_id, t] = ekf.state
    return estimated


def _music_grids_for_tracking(num_tracks: int) -> MusicMeasurementGrids:
    if num_tracks == 1:
        return MusicMeasurementGrids()
    return MusicMeasurementGrids(
        theta_half_width=math.radians(0.5),
        phi_half_width=math.radians(0.5),
        theta_points=17,
        phi_points=17,
        range_half_width=8.0,
        velocity_half_width=5.0,
        velocity_points=121,
    )


def _build_trajectories(config: ExperimentConfig) -> list[Trajectory]:
    if config.scenario == "vsc":
        starts = [np.array([85.0, 118.0, 80.0])]
        yaws = [math.radians(8.0)]
        pitches = [math.radians(0.5)]
        num_uavs = 1
    elif config.scenario == "blockage":
        starts = [np.array([135.0, -95.0, 78.0])]
        yaws = [math.radians(92.0)]
        pitches = [math.radians(1.0)]
        num_uavs = 1
    else:
        starts = [np.array([135.0, -95.0, 78.0]), np.array([250.0, 85.0, 88.0])]
        yaws = [math.radians(95.0), math.radians(245.0)]
        pitches = [math.radians(1.5), math.radians(-0.5)]
        num_uavs = config.num_uavs

    trajectories = []
    for i in range(num_uavs):
        trajectories.append(
            simulate_trajectory(
                seed=config.seed + i,
                steps=config.steps,
                dt=config.dt,
                initial_position=starts[i % len(starts)],
                initial_yaw=yaws[i % len(yaws)],
                initial_pitch=pitches[i % len(pitches)],
            )
        )
    return trajectories


def _blockage_for(scenario: str, time_index: int, predicted_state: np.ndarray, vsc: VSC) -> BlockageState:
    if scenario != "blockage":
        return BlockageState()
    nearest = select_pbs(predicted_state, vsc)
    if 10 <= time_index <= 40:
        blocked = {1 if nearest != 1 else 0}
    elif 70 <= time_index <= 100:
        blocked = {nearest}
    elif 150 <= time_index <= 180:
        blocked = {i for i in range(3) if i != nearest}
    else:
        blocked = set()
    return BlockageState.from_indices(blocked)


def _vsc_for_time(scenario: str, time_index: int, predicted_state: np.ndarray, pbs_index: int, current: int, vsc: VSC) -> int:
    if scenario != "vsc":
        return current
    theta = measurement_function(predicted_state, vsc, pbs_index)[0]
    return choose_vsc_index(theta, current, vsc, time_index)


def _active_vsc(vsc_network: VSCNetwork | None, fallback_vsc: VSC, active_vsc_index: int) -> VSC:
    if vsc_network is None:
        return fallback_vsc
    return vsc_network.vscs[active_vsc_index]


def _pbs_label_for_time(active_vsc: VSC, pbs_index: int) -> str:
    return active_vsc.base_stations[pbs_index].name


def _assign_measurements(
    predicted_states: list[np.ndarray],
    candidate_grid: list[list[Measurement]],
    vscs: list[VSC],
    pbs_indices: list[int],
) -> tuple[int, ...]:
    n_trackers = len(predicted_states)
    if n_trackers == 1:
        return (0,)

    measurement_cov = default_measurement_covariance()
    score_matrix = np.zeros((n_trackers, n_trackers), dtype=float)
    for tracker_id in range(n_trackers):
        predicted_full = measurement_function(predicted_states[tracker_id], vscs[tracker_id], pbs_indices[tracker_id])
        for target_id in range(n_trackers):
            candidate = candidate_grid[tracker_id][target_id]
            if len(candidate.active_indices) == 0:
                score_matrix[tracker_id, target_id] = 1e12
                continue
            diff = candidate.observed - predicted_full[candidate.active_indices]
            r_active = measurement_cov[np.ix_(candidate.active_indices, candidate.active_indices)]
            score_matrix[tracker_id, target_id] = float(diff.T @ np.linalg.pinv(r_active) @ diff)

    best_assignment: tuple[int, ...] | None = None
    best_score = float("inf")
    for assignment in itertools.permutations(range(n_trackers)):
        score = sum(score_matrix[tracker_id, target_id] for tracker_id, target_id in enumerate(assignment))
        if score < best_score:
            best_score = score
            best_assignment = assignment
    assert best_assignment is not None
    return best_assignment


def _rmse(true_states: np.ndarray, estimated: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pos_error = estimated[:, :, [0, 2, 4]] - true_states[:, :, [0, 2, 4]]
    vel_error = estimated[:, :, [1, 3, 5]] - true_states[:, :, [1, 3, 5]]
    return np.sqrt(np.mean(pos_error**2, axis=(0, 1))), np.sqrt(np.mean(vel_error**2, axis=(0, 1)))


def _save_figures(
    config: ExperimentConfig,
    vsc: VSC,
    vsc_network: VSCNetwork | None,
    true_states: np.ndarray,
    estimated: np.ndarray,
    single_bs_estimated: np.ndarray | None,
    pbs_history: np.ndarray,
    vsc_history: np.ndarray,
    pbs_label_history: np.ndarray,
) -> tuple[Path, ...]:
    if not config.save_plots:
        return ()
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = [
        out / f"{_output_stem(config)}_top_view.png",
        out / f"{_output_stem(config)}_position_velocity.png",
        out / f"{_output_stem(config)}_tracking_3d.png",
        out / f"{_output_stem(config)}_pbs_history.png",
    ]
    if single_bs_estimated is not None:
        paths.append(out / f"{_output_stem(config)}_single_bs_baseline.png")
    plot_vsc_top_view(vsc_network or vsc, true_states, estimated, paths[0])
    plot_tracking_components(true_states, estimated, config.dt, paths[1])
    plot_tracking_3d(true_states, estimated, paths[2])
    plot_pbs_history(
        pbs_history,
        vsc_history if config.scenario == "vsc" else None,
        paths[3],
        pbs_label_history if config.scenario == "vsc" else None,
    )
    if single_bs_estimated is not None:
        plot_tracking_components(true_states, single_bs_estimated, config.dt, paths[4])
    return tuple(paths)


def _output_stem(config: ExperimentConfig) -> str:
    if config.measurement_source == "analytic":
        return config.scenario
    return f"{config.scenario}_{config.measurement_source}"
