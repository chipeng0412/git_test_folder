from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

import numpy as np

from .plots import plot_detection_rmse
from .signal_music import RadarConfig, TargetParameters, estimate_single_target_parameters, synthesize_single_target_echo


@dataclass(frozen=True)
class DetectionRmseConfig:
    snr_db: tuple[float, ...] = (-15.0, -10.0, -5.0, 0.0, 5.0, 10.0)
    monte_carlo: int = 8
    seed: int = 21
    output_dir: Path = Path("outputs")
    save_csv: bool = True
    save_figure: bool = True


@dataclass(frozen=True)
class DetectionRmseResult:
    snr_db: np.ndarray
    rmse_theta_deg: np.ndarray
    rmse_phi_deg: np.ndarray
    rmse_range_m: np.ndarray
    rmse_velocity_mps: np.ndarray
    csv_path: Path | None = None
    figure_path: Path | None = None


def run_detection_rmse_experiment(config: DetectionRmseConfig) -> DetectionRmseResult:
    radar_config = RadarConfig()
    target = TargetParameters(
        theta=math.radians(75.0),
        phi=math.radians(18.0),
        range_value=118.0,
        velocity_value=14.0,
    )
    snr_values = np.asarray(config.snr_db, dtype=float)
    errors = np.zeros((len(snr_values), config.monte_carlo, 4), dtype=float)

    for snr_index, snr in enumerate(snr_values):
        for run_index in range(config.monte_carlo):
            estimate = estimate_single_target_parameters(
                synthesize_single_target_echo(
                    target,
                    radar_config,
                    snr_db=float(snr),
                    clutter_amplitude=8.0,
                    seed=config.seed * 1000 + snr_index * 100 + run_index,
                ),
                radar_config,
                theta_grid=np.deg2rad(np.linspace(65.0, 85.0, 41)),
                phi_grid=np.deg2rad(np.linspace(10.0, 26.0, 33)),
                range_grid=np.linspace(108.0, 128.0, 81),
                velocity_grid=np.linspace(8.0, 20.0, 73),
            )
            errors[snr_index, run_index] = [
                math.degrees(estimate.theta - target.theta),
                math.degrees(estimate.phi - target.phi),
                estimate.range_value - target.range_value,
                estimate.velocity_value - target.velocity_value,
            ]

    rmse = np.sqrt(np.mean(errors**2, axis=1))
    csv_path = _write_csv(config, snr_values, rmse) if config.save_csv else None
    figure_path = _write_figure(config, snr_values, rmse) if config.save_figure else None
    return DetectionRmseResult(
        snr_db=snr_values,
        rmse_theta_deg=rmse[:, 0],
        rmse_phi_deg=rmse[:, 1],
        rmse_range_m=rmse[:, 2],
        rmse_velocity_mps=rmse[:, 3],
        csv_path=csv_path,
        figure_path=figure_path,
    )


def _write_csv(config: DetectionRmseConfig, snr_values: np.ndarray, rmse: np.ndarray) -> Path:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    path = config.output_dir / "detection_rmse.csv"
    header = "snr_db,rmse_theta_deg,rmse_phi_deg,rmse_range_m,rmse_velocity_mps"
    rows = np.column_stack([snr_values, rmse])
    np.savetxt(path, rows, delimiter=",", header=header, comments="", fmt="%.8f")
    return path


def _write_figure(config: DetectionRmseConfig, snr_values: np.ndarray, rmse: np.ndarray) -> Path:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    path = config.output_dir / "detection_rmse.png"
    plot_detection_rmse(
        snr_values,
        rmse_theta_deg=rmse[:, 0],
        rmse_phi_deg=rmse[:, 1],
        rmse_range_m=rmse[:, 2],
        rmse_velocity_mps=rmse[:, 3],
        out=path,
    )
    return path
