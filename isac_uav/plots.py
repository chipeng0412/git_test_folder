from __future__ import annotations

from pathlib import Path
import math
import os

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/codex-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/codex-cache")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
Path(os.environ["XDG_CACHE_HOME"], "fontconfig").mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .geometry import VSC, VSCNetwork


def plot_vsc_top_view(vsc: VSC | VSCNetwork, true_states: np.ndarray, estimated: np.ndarray, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.set_aspect("equal", adjustable="box")
    vscs = vsc.vscs if isinstance(vsc, VSCNetwork) else (vsc,)
    label_counts: dict[tuple[float, float], int] = {}
    for vsc_index, single_vsc in enumerate(vscs):
        line_color = "#0072BD" if vsc_index == 0 else "#D95319"
        for bs in single_vsc.base_stations:
            _draw_hexagon(ax, bs.position[0], bs.position[1], single_vsc.radius, line_color)
            ax.scatter(bs.position[0], bs.position[1], marker="^", s=80, color=line_color)
            key = (round(float(bs.position[0]), 6), round(float(bs.position[1]), 6))
            label_counts[key] = label_counts.get(key, 0) + 1
            offset = 12 * (label_counts[key] - 1)
            ax.text(bs.position[0] + 6, bs.position[1] + 6 + offset, bs.name)

    for i in range(true_states.shape[0]):
        ax.plot(true_states[i, :, 0], true_states[i, :, 2], label=f"UAV{i + 1} true")
        ax.plot(estimated[i, :, 0], estimated[i, :, 2], "--", label=f"UAV{i + 1} EKF")

    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_tracking_components(true_states: np.ndarray, estimated: np.ndarray, dt: float, out: Path) -> None:
    time = np.arange(true_states.shape[1]) * dt
    fig, axes = plt.subplots(2, 3, figsize=(12, 6), sharex=True)
    labels = ["x", "y", "z", "vx", "vy", "vz"]
    true_cols = [0, 2, 4, 1, 3, 5]
    for ax, label, col in zip(axes.ravel(), labels, true_cols):
        for i in range(true_states.shape[0]):
            ax.plot(time, true_states[i, :, col], label=f"UAV{i + 1} true")
            ax.plot(time, estimated[i, :, col], "--", label=f"UAV{i + 1} EKF")
        ax.set_title(label)
        ax.grid(True, alpha=0.25)
    axes[-1, 0].set_xlabel("time (s)")
    axes[-1, 1].set_xlabel("time (s)")
    axes[-1, 2].set_xlabel("time (s)")
    axes[0, 0].legend(loc="best", fontsize=7)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_tracking_3d(true_states: np.ndarray, estimated: np.ndarray, out: Path) -> None:
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    for i in range(true_states.shape[0]):
        ax.plot(true_states[i, :, 0], true_states[i, :, 2], true_states[i, :, 4], label=f"UAV{i + 1} true")
        ax.plot(estimated[i, :, 0], estimated[i, :, 2], estimated[i, :, 4], "--", label=f"UAV{i + 1} EKF")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_zlabel("z (m)")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_pbs_history(
    pbs_history: np.ndarray,
    vsc_history: np.ndarray | None,
    out: Path,
    pbs_label_history: np.ndarray | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(9, 3.5))
    t = np.arange(pbs_history.shape[1])
    if pbs_label_history is None:
        for i in range(pbs_history.shape[0]):
            ax.step(t, pbs_history[i] + 1, where="post", label=f"UAV{i + 1} PBS")
    else:
        labels = list(dict.fromkeys(str(label) for label in pbs_label_history.ravel()))
        label_to_y = {label: index + 1 for index, label in enumerate(labels)}
        for i in range(pbs_label_history.shape[0]):
            y = np.asarray([label_to_y[str(label)] for label in pbs_label_history[i]], dtype=float)
            ax.step(t, y, where="post", label=f"UAV{i + 1} PBS")
        ax.set_yticks(list(label_to_y.values()))
        ax.set_yticklabels(labels)
    if vsc_history is not None:
        for i in range(vsc_history.shape[0]):
            y = vsc_history[i] + 1.0 if pbs_label_history is not None else vsc_history[i] + 1.05
            ax.step(t, y, where="post", linestyle="--", label=f"UAV{i + 1} VSC")
    ax.set_xlabel("time slot")
    ax.set_ylabel("index")
    if pbs_label_history is None:
        ax.set_yticks([1, 2, 3])
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_detection_rmse(
    snr_db: np.ndarray,
    rmse_theta_deg: np.ndarray,
    rmse_phi_deg: np.ndarray,
    rmse_range_m: np.ndarray,
    rmse_velocity_mps: np.ndarray,
    out: Path,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(9, 6), sharex=True)
    series = [
        ("theta RMSE (deg)", rmse_theta_deg),
        ("phi RMSE (deg)", rmse_phi_deg),
        ("range RMSE (m)", rmse_range_m),
        ("velocity RMSE (m/s)", rmse_velocity_mps),
    ]
    for ax, (label, values) in zip(axes.ravel(), series):
        ax.plot(snr_db, values, marker="o", linewidth=1.5)
        ax.set_title(label)
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.25)
    axes[-1, 0].set_xlabel("SNR (dB)")
    axes[-1, 1].set_xlabel("SNR (dB)")
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def _draw_hexagon(ax: plt.Axes, cx: float, cy: float, radius: float, color: str = "#0072BD") -> None:
    angles = np.deg2rad(np.arange(0, 361, 60))
    ax.plot(cx + radius * np.cos(angles), cy + radius * np.sin(angles), color=color, linewidth=0.6)
    for angle in np.deg2rad([60, 180, 300]):
        ax.plot([cx, cx + radius * math.cos(angle)], [cy, cy + radius * math.sin(angle)], color=color, linewidth=0.4)
