from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

from isac_uav.detection_experiment import DetectionRmseConfig, run_detection_rmse_experiment
from isac_uav.experiments import ExperimentConfig, run_tracking_experiment
from isac_uav.geometry import build_vsc, measurement_function, state_from_position_velocity
from isac_uav.music_measurement import MusicMeasurementGrids, generate_music_measurement
from isac_uav.reproduction_suite import write_figure_reproduction_map
from isac_uav.section_v_suite import SectionVSuiteConfig, run_section_v_suite
from isac_uav.signal_music import (
    RadarConfig,
    TargetParameters,
    estimate_single_target_parameters,
    synthesize_single_target_echo,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="First-stage reproduction for networked ISAC UAV tracking.")
    parser.add_argument(
        "--scenario",
        choices=[
            "multi",
            "blockage",
            "vsc",
            "music",
            "music-measurement",
            "detection-rmse",
            "figure-map",
            "section-v",
        ],
        default="multi",
    )
    parser.add_argument("--steps", type=int, default=180)
    parser.add_argument("--dt", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--measurement-source", choices=["analytic", "music"], default="analytic")
    parser.add_argument("--monte-carlo", type=int, default=8)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.scenario == "music":
        run_music_demo(args.seed)
        return
    if args.scenario == "music-measurement":
        run_music_measurement_demo(args.seed)
        return
    if args.scenario == "detection-rmse":
        run_detection_rmse_demo(args.seed, args.monte_carlo, args.output_dir, args.no_plots)
        return
    if args.scenario == "figure-map":
        path = write_figure_reproduction_map(Path("notes") / "figure_reproduction_map.md")
        print(f"figure map: {path}")
        return
    if args.scenario == "section-v":
        run_section_v_demo(args)
        return
    num_uavs = 2 if args.scenario == "multi" else 1
    result = run_tracking_experiment(
        ExperimentConfig(
            scenario=args.scenario,
            steps=args.steps,
            dt=args.dt,
            seed=args.seed,
            num_uavs=num_uavs,
            measurement_source=args.measurement_source,
            output_dir=args.output_dir,
            save_plots=not args.no_plots,
        )
    )

    print(f"scenario: {result.config.scenario}")
    print(f"measurement source: {result.config.measurement_source}")
    print(
        "position RMSE [x,y,z] m:",
        ", ".join(f"{value:.3f}" for value in result.rmse_position),
    )
    print(
        "velocity RMSE [vx,vy,vz] m/s:",
        ", ".join(f"{value:.3f}" for value in result.rmse_velocity),
    )
    if result.single_bs_rmse_position is not None and result.single_bs_rmse_velocity is not None:
        print(
            "single-BS baseline position RMSE [x,y,z] m:",
            ", ".join(f"{value:.3f}" for value in result.single_bs_rmse_position),
        )
        print(
            "single-BS baseline velocity RMSE [vx,vy,vz] m/s:",
            ", ".join(f"{value:.3f}" for value in result.single_bs_rmse_velocity),
        )
    if result.figure_paths:
        print("figures:")
        for path in result.figure_paths:
            print(f"  {path}")


def run_music_demo(seed: int) -> None:
    config = RadarConfig()
    target = TargetParameters(
        theta=math.radians(75.0),
        phi=math.radians(18.0),
        distance=118.0,
        radial_velocity=14.0,
    )
    echo = synthesize_single_target_echo(target, config, snr_db=35.0, clutter_amplitude=8.0, seed=seed)
    estimate = estimate_single_target_parameters(
        echo,
        config,
        theta_grid=np.deg2rad(np.linspace(65.0, 85.0, 41)),
        phi_grid=np.deg2rad(np.linspace(10.0, 26.0, 33)),
        distance_grid=np.linspace(108.0, 128.0, 81),
        velocity_grid=np.linspace(8.0, 20.0, 73),
    )
    print("scenario: music")
    print(f"theta true/est deg: {math.degrees(target.theta):.2f} / {math.degrees(estimate.theta):.2f}")
    print(f"phi true/est deg: {math.degrees(target.phi):.2f} / {math.degrees(estimate.phi):.2f}")
    print(f"distance true/est m: {target.distance:.2f} / {estimate.distance:.2f}")
    print(f"velocity true/est m/s: {target.radial_velocity:.2f} / {estimate.radial_velocity:.2f}")


def run_music_measurement_demo(seed: int) -> None:
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
        grids=MusicMeasurementGrids(),
        seed=seed,
    )
    print("scenario: music-measurement")
    labels = [
        "theta_pbs",
        "phi_pbs",
        "v_pbs",
        "d_pbs",
        "theta_sbs1",
        "phi_sbs1",
        "v_pbs+v_sbs1",
        "d_pbs+d_sbs1",
        "theta_sbs2",
        "phi_sbs2",
        "v_pbs+v_sbs2",
        "d_pbs+d_sbs2",
    ]
    for index, label in enumerate(labels):
        if "theta" in label or "phi" in label:
            true_value = np.rad2deg(clean[index])
            estimate_value = np.rad2deg(measured[index])
            unit = "deg"
        else:
            true_value = clean[index]
            estimate_value = measured[index]
            unit = "m/s" if label.startswith("v") else "m"
        print(f"{label}: {true_value:.3f} / {estimate_value:.3f} {unit}")


def run_detection_rmse_demo(seed: int, monte_carlo: int, output_dir: Path, no_plots: bool) -> None:
    result = run_detection_rmse_experiment(
        DetectionRmseConfig(
            seed=seed,
            monte_carlo=monte_carlo,
            output_dir=output_dir,
            save_csv=True,
            save_figure=not no_plots,
        )
    )
    print("scenario: detection-rmse")
    print("snr_db, rmse_theta_deg, rmse_phi_deg, rmse_range_m, rmse_velocity_mps")
    for row in zip(
        result.snr_db,
        result.rmse_theta_deg,
        result.rmse_phi_deg,
        result.rmse_range_m,
        result.rmse_velocity_mps,
    ):
        print(", ".join(f"{value:.4f}" for value in row))
    if result.csv_path is not None:
        print(f"csv: {result.csv_path}")
    if result.figure_path is not None:
        print(f"figure: {result.figure_path}")


def run_section_v_demo(args: argparse.Namespace) -> None:
    result = run_section_v_suite(
        SectionVSuiteConfig(
            steps=args.steps,
            dt=args.dt,
            seed=args.seed,
            detection_monte_carlo=args.monte_carlo,
            measurement_source=args.measurement_source,
            output_dir=args.output_dir,
            save_plots=not args.no_plots,
        )
    )
    print("scenario: section-v")
    print(f"summary: {result.summary_csv}")
    print(f"figure map: {result.figure_map}")
    print(f"report: {result.report_md}")
    if result.generated_paths:
        print("artifacts:")
        for path in result.generated_paths:
            print(f"  {path}")


if __name__ == "__main__":
    main()
