from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FigureReproduction:
    figure: str
    paper_result: str
    command: str
    outputs: tuple[str, ...]
    code_refs: tuple[str, ...]
    status: str
    limitations: str


def figure_reproduction_map() -> tuple[FigureReproduction, ...]:
    """Map paper figures to the current reproduction commands and artifacts."""

    return (
        FigureReproduction(
            figure="Fig. 6",
            paper_result="Detection RMSE of theta, phi, distance, and radial velocity versus SNR.",
            command="python main.py --scenario detection-rmse --monte-carlo 8",
            outputs=("outputs/detection_rmse.csv", "outputs/detection_rmse.png"),
            code_refs=("isac_uav.detection_experiment.run_detection_rmse_experiment", "isac_uav.signal_music"),
            status="implemented",
            limitations="Default Monte Carlo is small for speed; paper uses N_MC=10000 and compares more parameter groups.",
        ),
        FigureReproduction(
            figure="Fig. 7",
            paper_result="Top view of three BS locations and two UAV trajectories.",
            command="python main.py --scenario multi",
            outputs=("outputs/multi_top_view.png",),
            code_refs=("isac_uav.geometry.build_vsc", "isac_uav.trajectory.simulate_trajectory"),
            status="implemented",
            limitations="Geometry is an equilateral VSC preserving the existing project convention; it is rotationally equivalent but not a pixel match to the paper figure.",
        ),
        FigureReproduction(
            figure="Fig. 8",
            paper_result="Two-UAV position and velocity tracking results.",
            command="python main.py --scenario multi",
            outputs=("outputs/multi_position_velocity.png", "outputs/multi_tracking_3d.png"),
            code_refs=("isac_uav.experiments.run_tracking_experiment", "isac_uav.ekf.ExtendedKalmanFilter"),
            status="implemented",
            limitations="Analytic measurements are the default; use --measurement-source music for the slower MUSIC-backed path.",
        ),
        FigureReproduction(
            figure="Fig. 9",
            paper_result="PBS index for UAV1 and UAV2 without blockage.",
            command="python main.py --scenario multi",
            outputs=("outputs/multi_pbs_history.png",),
            code_refs=("isac_uav.handover.select_pbs", "isac_uav.experiments.run_tracking_experiment"),
            status="implemented",
            limitations="PBS selection uses nearest unblocked BS, matching the paper's no-blockage rule.",
        ),
        FigureReproduction(
            figure="Fig. 10",
            paper_result="Tracking under one-SBS, PBS, and two-SBS blockage intervals.",
            command="python main.py --scenario blockage",
            outputs=("outputs/blockage_position_velocity.png", "outputs/blockage_tracking_3d.png"),
            code_refs=("isac_uav.experiments._blockage_for", "isac_uav.measurement.active_measurement_roles"),
            status="implemented",
            limitations="Blockage is scenario-scripted rather than detected from a missed MUSIC peak region.",
        ),
        FigureReproduction(
            figure="Fig. 11",
            paper_result="PBS index under blockage.",
            command="python main.py --scenario blockage",
            outputs=("outputs/blockage_pbs_history.png",),
            code_refs=("isac_uav.handover.select_pbs", "isac_uav.experiments._blockage_for"),
            status="implemented",
            limitations="Uses known blockage state instead of a full echo-detection failure classifier.",
        ),
        FigureReproduction(
            figure="Fig. 12",
            paper_result="Trajectory of one UAV flying across two VSCs.",
            command="python main.py --scenario vsc",
            outputs=("outputs/vsc_top_view.png", "outputs/vsc_tracking_3d.png"),
            code_refs=("isac_uav.handover.choose_vsc_index", "isac_uav.experiments._vsc_for_time"),
            status="implemented",
            limitations="Active VSC geometry is used for measurements and EKF updates; the sector beam pattern itself is still simplified.",
        ),
        FigureReproduction(
            figure="Fig. 13",
            paper_result="PBS/VSC index when the UAV enters and exits the buffer region.",
            command="python main.py --scenario vsc",
            outputs=("outputs/vsc_pbs_history.png",),
            code_refs=("isac_uav.handover.in_vsc_buffer", "isac_uav.handover.choose_vsc_index"),
            status="implemented",
            limitations="PBS history uses paper-style labels such as 1-1 and 2-3; full transceiver-sector beam switching is approximated by active VSC geometry switching.",
        ),
    )


def write_figure_reproduction_map(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = figure_reproduction_map()
    lines = [
        "# 論文圖與復現輸出對照表",
        "",
        "這份文件把論文 Section V 的每張 simulation figure 對應到目前 Python 復現命令、輸出檔與主要代碼位置。",
        "",
        "| 論文圖 | 目前狀態 | 復現命令 | 輸出檔 | 主要代碼 | 當前限制 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.figure,
                    row.status,
                    f"`{row.command}`",
                    "<br>".join(f"`{item}`" for item in row.outputs),
                    "<br>".join(f"`{item}`" for item in row.code_refs),
                    row.limitations,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "整套 Section V smoke run 可以使用 `python main.py --scenario section-v --monte-carlo 2 --steps 60`，會輸出 `outputs/section_v_summary.csv`。",
            "tracking 類場景可以加上 `--measurement-source music`，把 analytic noisy measurement 換成目前的 MTI/MUSIC-backed measurement generator。",
            "MUSIC-backed multi-UAV path 目前仍使用 prediction-gated angle windows，因此應視為中間階段復現，而不是完全等價於論文的無先驗全局多目標角度關聯。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
