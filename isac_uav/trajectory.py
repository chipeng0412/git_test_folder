from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.stats import truncnorm

from .geometry import state_from_position_velocity


@dataclass(frozen=True)
class Trajectory:
    states: np.ndarray
    yaw: np.ndarray
    pitch: np.ndarray
    speed: np.ndarray


def simulate_trajectory(
    seed: int,
    steps: int,
    dt: float,
    initial_position: np.ndarray | None = None,
    initial_yaw: float = math.radians(95.0),
    initial_pitch: float = math.radians(2.0),
    initial_speed: float = 16.0,
    sharp_turn_steps: tuple[int, ...] = (60, 120),
) -> Trajectory:
    """Generate a continuous, mildly random UAV trajectory.

    The yaw, pitch, and speed updates follow the truncated-Gaussian idea in
    Section V-A of the paper. Sharp turns are injected to stress the EKF.
    """

    rng = np.random.default_rng(seed)
    if steps < 2:
        raise ValueError("steps must be at least 2")

    pos = np.zeros((steps, 3), dtype=float)
    vel = np.zeros((steps, 3), dtype=float)
    yaw = np.zeros(steps, dtype=float)
    pitch = np.zeros(steps, dtype=float)
    speed = np.zeros(steps, dtype=float)

    pos[0] = np.asarray(initial_position if initial_position is not None else [140.0, -95.0, 75.0], dtype=float)
    yaw[0] = initial_yaw
    pitch[0] = initial_pitch
    speed[0] = initial_speed
    vel[0] = _velocity_from_angles(speed[0], yaw[0], pitch[0])

    for t in range(1, steps):
        yaw_mu = yaw[t - 1]
        pitch_mu = pitch[t - 1]
        speed_mu = speed[t - 1]

        if t in sharp_turn_steps:
            yaw_mu += math.radians(70.0 if (t // max(sharp_turn_steps[0], 1)) % 2 else -65.0)

        yaw[t] = _trunc_normal(rng, yaw_mu, math.radians(10.0), yaw_mu - math.radians(30.0), yaw_mu + math.radians(30.0))
        pitch[t] = _trunc_normal(
            rng,
            pitch_mu,
            math.radians(5.0),
            max(math.radians(-10.0), pitch_mu - math.radians(20.0)),
            min(math.radians(20.0), pitch_mu + math.radians(20.0)),
        )
        speed[t] = _trunc_normal(rng, speed_mu, 2.0, 12.0, 20.0)
        vel[t] = _velocity_from_angles(speed[t], yaw[t], pitch[t])
        pos[t] = pos[t - 1] + vel[t] * dt

    states = np.vstack([state_from_position_velocity(pos[t], vel[t]) for t in range(steps)])
    return Trajectory(states=states, yaw=yaw, pitch=pitch, speed=speed)


def _trunc_normal(rng: np.random.Generator, mu: float, sigma: float, low: float, high: float) -> float:
    a = (low - mu) / sigma
    b = (high - mu) / sigma
    return float(truncnorm.rvs(a, b, loc=mu, scale=sigma, random_state=rng))


def _velocity_from_angles(speed: float, yaw: float, pitch: float) -> np.ndarray:
    return np.asarray(
        [
            speed * math.cos(pitch) * math.cos(yaw),
            speed * math.cos(pitch) * math.sin(yaw),
            speed * math.sin(pitch),
        ],
        dtype=float,
    )
