from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import csv

from .detection_experiment import DetectionRmseConfig, run_detection_rmse_experiment
from .experiments import ExperimentConfig, run_tracking_experiment
from .reproduction_suite import write_figure_reproduction_map


@dataclass(frozen=True)
class SectionVSuiteConfig:
    steps: int = 180
    dt: float = 0.2
    seed: int = 7
    detection_monte_carlo: int = 8
    measurement_source: str = "analytic"
    output_dir: Path = Path("outputs")
    save_plots: bool = True


@dataclass(frozen=True)
class SectionVSuiteResult:
    summary_csv: Path
    figure_map: Path
    report_md: Path
    generated_paths: tuple[Path, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PaperTrackingBenchmark:
    rmse_position: tuple[float, float, float]
    rmse_velocity: tuple[float, float, float]
    source: str


PAPER_TRACKING_BENCHMARKS: dict[str, PaperTrackingBenchmark] = {
    "multi": PaperTrackingBenchmark(
        rmse_position=(0.35, 0.39, 0.43),
        rmse_velocity=(0.98, 1.27, 0.51),
        source="Paper Fig. 8 text: average RMSE over 10 two-UAV trajectories.",
    ),
    "vsc": PaperTrackingBenchmark(
        rmse_position=(0.32, 0.37, 0.52),
        rmse_velocity=(1.12, 1.46, 0.67),
        source="Paper Fig. 13 text: RMSE over the full cross-VSC tracking process.",
    ),
}


def run_section_v_suite(config: SectionVSuiteConfig) -> SectionVSuiteResult:
    """Run the current Section V reproduction set and write a compact summary."""

    config.output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    rows: list[dict[str, str]] = []

    detection = run_detection_rmse_experiment(
        DetectionRmseConfig(
            monte_carlo=config.detection_monte_carlo,
            seed=config.seed,
            output_dir=config.output_dir,
            save_csv=True,
            save_figure=config.save_plots,
        )
    )
    if detection.csv_path is not None:
        generated.append(detection.csv_path)
    if detection.figure_path is not None:
        generated.append(detection.figure_path)
    rows.append(
        {
            "figure_group": "Fig. 6",
            "scenario": "detection-rmse",
            "measurement_source": "music",
            "steps": "",
            "dt": "",
            "seed": str(config.seed),
            "rmse_x_m": "",
            "rmse_y_m": "",
            "rmse_z_m": "",
            "rmse_vx_mps": "",
            "rmse_vy_mps": "",
            "rmse_vz_mps": "",
            "single_bs_rmse_x_m": "",
            "single_bs_rmse_y_m": "",
            "single_bs_rmse_z_m": "",
            "single_bs_rmse_vx_mps": "",
            "single_bs_rmse_vy_mps": "",
            "single_bs_rmse_vz_mps": "",
            **_empty_benchmark_fields(),
            "artifacts": _join_paths(path for path in (detection.csv_path, detection.figure_path) if path is not None),
            "notes": f"SNR RMSE sweep; monte_carlo={config.detection_monte_carlo}",
        }
    )

    scenario_to_figures = {
        "multi": "Fig. 7-9",
        "blockage": "Fig. 10-11",
        "vsc": "Fig. 12-13",
    }
    for scenario, figure_group in scenario_to_figures.items():
        tracking = run_tracking_experiment(
            ExperimentConfig(
                scenario=scenario,
                steps=config.steps,
                dt=config.dt,
                seed=config.seed,
                num_uavs=2 if scenario == "multi" else 1,
                measurement_source=config.measurement_source,
                output_dir=config.output_dir,
                save_plots=config.save_plots,
            )
        )
        generated.extend(tracking.figure_paths)
        benchmark_fields = _benchmark_fields(scenario, tracking.rmse_position, tracking.rmse_velocity)
        rows.append(
            {
                "figure_group": figure_group,
                "scenario": scenario,
                "measurement_source": config.measurement_source,
                "steps": str(config.steps),
                "dt": f"{config.dt:g}",
                "seed": str(config.seed),
                "rmse_x_m": f"{tracking.rmse_position[0]:.6f}",
                "rmse_y_m": f"{tracking.rmse_position[1]:.6f}",
                "rmse_z_m": f"{tracking.rmse_position[2]:.6f}",
                "rmse_vx_mps": f"{tracking.rmse_velocity[0]:.6f}",
                "rmse_vy_mps": f"{tracking.rmse_velocity[1]:.6f}",
                "rmse_vz_mps": f"{tracking.rmse_velocity[2]:.6f}",
                **_single_bs_fields(tracking.single_bs_rmse_position, tracking.single_bs_rmse_velocity),
                **benchmark_fields,
                "artifacts": _join_paths(tracking.figure_paths),
                "notes": _tracking_notes(scenario),
            }
        )

    summary_csv = config.output_dir / "section_v_summary.csv"
    _write_summary(summary_csv, rows)
    generated.append(summary_csv)
    figure_map = write_figure_reproduction_map(Path("notes") / "figure_reproduction_map.md")
    report_md = write_section_v_report(Path("notes") / "section_v_report.md", rows, config)
    return SectionVSuiteResult(
        summary_csv=summary_csv,
        figure_map=figure_map,
        report_md=report_md,
        generated_paths=tuple(generated),
    )


def write_section_v_report(path: Path, rows: list[dict[str, str]], config: SectionVSuiteConfig) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Section V 復現報告",
        "",
        "這份報告由 `python main.py --scenario section-v` 自動生成，目的是把本地 Python 復現結果整理成可閱讀的中文筆記。",
        "",
        "## 運行設定",
        "",
        f"- tracking steps: `{config.steps}`",
        f"- measurement interval dt: `{config.dt}` s",
        f"- seed: `{config.seed}`",
        f"- tracking measurement source: `{config.measurement_source}`",
        f"- detection Monte Carlo: `{config.detection_monte_carlo}`",
        "",
        "## 圖表對照",
        "",
        "| 論文圖 | 場景 | 本地 RMSE x/y/z | 本地 RMSE vx/vy/vz | single-BS baseline | 論文 RMSE x/y/z | 論文 RMSE vx/vy/vz | delta 重點 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(_report_table_row(row))

    lines.extend(
        [
            "",
            "## 解讀",
            "",
            "- Fig. 6 對應 detection RMSE vs SNR；本地預設 Monte Carlo 次數較小，用於 smoke reproduction，不應直接宣稱等同論文的 `N_MC=10000`。",
            "- Fig. 7-9 的 `multi` 場景可直接和論文 Fig. 8 的平均 RMSE 文字數值比較；`delta_rmse_*` 是本地 RMSE 減去論文 RMSE。`single-BS baseline` 用固定 BS1 的 PBS 四維量測，對照論文中單站追蹤失效的觀察。",
            "- Fig. 10-11 的 `blockage` 場景目前能復現三段 blockage 行為和 PBS handover，但論文文字沒有列完整 RMSE benchmark，因此報告保留定性對照。",
            "- Fig. 12-13 的 `vsc` 場景已使用 active VSC 幾何更新量測與 EKF；仍用幾何近似 sector beam switching。",
            "",
            "## 來源文件",
            "",
            "- 數值 CSV：`outputs/section_v_summary.csv`",
            "- 圖表地圖：`notes/figure_reproduction_map.md`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_summary(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "figure_group",
        "scenario",
        "measurement_source",
        "steps",
        "dt",
        "seed",
        "rmse_x_m",
        "rmse_y_m",
        "rmse_z_m",
        "rmse_vx_mps",
        "rmse_vy_mps",
        "rmse_vz_mps",
        "single_bs_rmse_x_m",
        "single_bs_rmse_y_m",
        "single_bs_rmse_z_m",
        "single_bs_rmse_vx_mps",
        "single_bs_rmse_vy_mps",
        "single_bs_rmse_vz_mps",
        "paper_rmse_x_m",
        "paper_rmse_y_m",
        "paper_rmse_z_m",
        "paper_rmse_vx_mps",
        "paper_rmse_vy_mps",
        "paper_rmse_vz_mps",
        "delta_rmse_x_m",
        "delta_rmse_y_m",
        "delta_rmse_z_m",
        "delta_rmse_vx_mps",
        "delta_rmse_vy_mps",
        "delta_rmse_vz_mps",
        "paper_reference",
        "artifacts",
        "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _report_table_row(row: dict[str, str]) -> str:
    local_pos = _triplet(row, "rmse_x_m", "rmse_y_m", "rmse_z_m", "m")
    local_vel = _triplet(row, "rmse_vx_mps", "rmse_vy_mps", "rmse_vz_mps", "m/s")
    single_bs = _single_bs_summary(row)
    paper_pos = _triplet(row, "paper_rmse_x_m", "paper_rmse_y_m", "paper_rmse_z_m", "m")
    paper_vel = _triplet(row, "paper_rmse_vx_mps", "paper_rmse_vy_mps", "paper_rmse_vz_mps", "m/s")
    delta = _delta_summary(row)
    return (
        f"| {row['figure_group']} | {row['scenario']} | {local_pos} | {local_vel} | {single_bs} | "
        f"{paper_pos} | {paper_vel} | {delta} |"
    )


def _triplet(row: dict[str, str], a: str, b: str, c: str, unit: str) -> str:
    values = [row.get(a, ""), row.get(b, ""), row.get(c, "")]
    if any(value == "" for value in values):
        return "-"
    return f"{values[0]} / {values[1]} / {values[2]} {unit}"


def _delta_summary(row: dict[str, str]) -> str:
    values = [
        row.get("delta_rmse_x_m", ""),
        row.get("delta_rmse_y_m", ""),
        row.get("delta_rmse_z_m", ""),
        row.get("delta_rmse_vx_mps", ""),
        row.get("delta_rmse_vy_mps", ""),
        row.get("delta_rmse_vz_mps", ""),
    ]
    if any(value == "" for value in values):
        reference = row.get("paper_reference", "")
        return reference or "-"
    return " / ".join(values)


def _single_bs_summary(row: dict[str, str]) -> str:
    pos = _triplet(row, "single_bs_rmse_x_m", "single_bs_rmse_y_m", "single_bs_rmse_z_m", "m")
    vel = _triplet(row, "single_bs_rmse_vx_mps", "single_bs_rmse_vy_mps", "single_bs_rmse_vz_mps", "m/s")
    if pos == "-" and vel == "-":
        return "-"
    return f"pos {pos}; vel {vel}"


def _join_paths(paths) -> str:
    return ";".join(str(path) for path in paths)


def _empty_benchmark_fields() -> dict[str, str]:
    return {
        "paper_rmse_x_m": "",
        "paper_rmse_y_m": "",
        "paper_rmse_z_m": "",
        "paper_rmse_vx_mps": "",
        "paper_rmse_vy_mps": "",
        "paper_rmse_vz_mps": "",
        "delta_rmse_x_m": "",
        "delta_rmse_y_m": "",
        "delta_rmse_z_m": "",
        "delta_rmse_vx_mps": "",
        "delta_rmse_vy_mps": "",
        "delta_rmse_vz_mps": "",
        "paper_reference": "",
    }


def _single_bs_fields(rmse_position, rmse_velocity) -> dict[str, str]:
    if rmse_position is None or rmse_velocity is None:
        return {
            "single_bs_rmse_x_m": "",
            "single_bs_rmse_y_m": "",
            "single_bs_rmse_z_m": "",
            "single_bs_rmse_vx_mps": "",
            "single_bs_rmse_vy_mps": "",
            "single_bs_rmse_vz_mps": "",
        }
    return {
        "single_bs_rmse_x_m": f"{rmse_position[0]:.6f}",
        "single_bs_rmse_y_m": f"{rmse_position[1]:.6f}",
        "single_bs_rmse_z_m": f"{rmse_position[2]:.6f}",
        "single_bs_rmse_vx_mps": f"{rmse_velocity[0]:.6f}",
        "single_bs_rmse_vy_mps": f"{rmse_velocity[1]:.6f}",
        "single_bs_rmse_vz_mps": f"{rmse_velocity[2]:.6f}",
    }


def _benchmark_fields(scenario: str, rmse_position, rmse_velocity) -> dict[str, str]:
    benchmark = PAPER_TRACKING_BENCHMARKS.get(scenario)
    if benchmark is None:
        fields = _empty_benchmark_fields()
        fields["paper_reference"] = "No complete numeric RMSE benchmark is stated in the paper text for this scenario."
        return fields

    paper_values = benchmark.rmse_position + benchmark.rmse_velocity
    local_values = tuple(float(value) for value in rmse_position) + tuple(float(value) for value in rmse_velocity)
    delta = tuple(local - paper for local, paper in zip(local_values, paper_values))
    return {
        "paper_rmse_x_m": f"{paper_values[0]:.6f}",
        "paper_rmse_y_m": f"{paper_values[1]:.6f}",
        "paper_rmse_z_m": f"{paper_values[2]:.6f}",
        "paper_rmse_vx_mps": f"{paper_values[3]:.6f}",
        "paper_rmse_vy_mps": f"{paper_values[4]:.6f}",
        "paper_rmse_vz_mps": f"{paper_values[5]:.6f}",
        "delta_rmse_x_m": f"{delta[0]:.6f}",
        "delta_rmse_y_m": f"{delta[1]:.6f}",
        "delta_rmse_z_m": f"{delta[2]:.6f}",
        "delta_rmse_vx_mps": f"{delta[3]:.6f}",
        "delta_rmse_vy_mps": f"{delta[4]:.6f}",
        "delta_rmse_vz_mps": f"{delta[5]:.6f}",
        "paper_reference": benchmark.source,
    }


def _tracking_notes(scenario: str) -> str:
    if scenario == "multi":
        return "Two-UAV tracking and PBS handover without blockage."
    if scenario == "blockage":
        return "Scripted one-SBS, PBS, and two-SBS blockage intervals."
    if scenario == "vsc":
        return "Adjacent VSC buffer handover with active VSC measurement geometry."
    return ""
