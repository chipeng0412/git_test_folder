from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np
from scipy.constants import c, degree


STATE_SIZE = 6
MEASUREMENT_SIZE = 12


@dataclass(frozen=True)
class BaseStation:
    """A BS with one sector-facing UPA orientation."""

    name: str
    position: np.ndarray
    alpha: float


@dataclass(frozen=True)
class VSC:
    """Virtual sensing cell composed of three neighboring BS sectors."""

    base_stations: tuple[BaseStation, BaseStation, BaseStation]
    center: np.ndarray
    radius: float
    theta_min: float = 30 * degree
    theta_max: float = 120 * degree
    buffer_theta: float = 5 * degree


@dataclass(frozen=True)
class VSCNetwork:
    """A small network of adjacent VSCs used by the handover experiment."""

    vscs: tuple[VSC, ...]


def build_vsc(
    d_bs: float = 200 * math.sqrt(3),
    h_bs: float = 15.0,
    labels: tuple[str, str, str] = ("BS1", "BS2", "BS3"),
) -> VSC:
    """Build the three-BS VSC used by the first reproduction stage.

    The coordinates follow the user's current `main.py` geometry: BS1 at the
    origin and BS2/BS3 on the right side, separated by +/-30 degrees.
    """

    bs1_pos = np.array([0.0, 0.0, h_bs])
    bs2_pos = np.array([d_bs * math.cos(-30 * degree), d_bs * math.sin(-30 * degree), h_bs])
    bs3_pos = np.array([d_bs * math.cos(30 * degree), d_bs * math.sin(30 * degree), h_bs])
    return _build_vsc_from_positions((bs1_pos, bs2_pos, bs3_pos), labels)


def build_adjacent_vsc_pair(d_bs: float = 200 * math.sqrt(3), h_bs: float = 15.0) -> VSCNetwork:
    """Build two adjacent VSCs with one shared physical BS sector.

    The first VSC is the standard three-BS geometry. The second VSC is placed
    above-left of the first one and shares the first VSC's left BS as its
    bottom-right sector, matching the paper's V-1 / V-3 sector-label idea.
    """

    vsc1 = build_vsc(d_bs=d_bs, h_bs=h_bs, labels=("1-1", "1-2", "1-3"))
    shared = vsc1.base_stations[0].position
    left = shared - np.array([d_bs * math.cos(-30 * degree), d_bs * math.sin(-30 * degree), 0.0])
    top_right = left + np.array([d_bs * math.cos(30 * degree), d_bs * math.sin(30 * degree), 0.0])
    vsc2 = _build_vsc_from_positions((left, top_right, shared), ("2-1", "2-2", "2-3"))
    return VSCNetwork((vsc1, vsc2))


def _build_vsc_from_positions(positions: tuple[np.ndarray, np.ndarray, np.ndarray], labels: tuple[str, str, str]) -> VSC:
    center = sum(positions) / 3.0
    base_stations = (
        BaseStation(labels[0], positions[0], _azimuth_to(center - positions[0])),
        BaseStation(labels[1], positions[1], _azimuth_to(center - positions[1])),
        BaseStation(labels[2], positions[2], _azimuth_to(center - positions[2])),
    )
    return VSC(base_stations=base_stations, center=center, radius=200.0)


def sph2cart(distance: float, theta: float, phi: float, origin: np.ndarray | None = None) -> np.ndarray:
    """Convert paper-style spherical coordinates to Cartesian coordinates."""

    xyz = np.array(
        [
            distance * math.cos(phi) * math.cos(theta),
            distance * math.cos(phi) * math.sin(theta),
            distance * math.sin(phi),
        ],
        dtype=float,
    )
    if origin is not None:
        xyz = xyz + origin
    return xyz


def cart2sph(point: np.ndarray, origin: np.ndarray | None = None) -> tuple[float, float, float]:
    """Convert Cartesian coordinates to paper-style (d, theta, phi)."""

    rel = np.asarray(point, dtype=float) - (np.zeros(3) if origin is None else origin)
    distance = float(np.linalg.norm(rel))
    if distance == 0:
        return 0.0, 0.0, 0.0
    theta = math.atan2(rel[1], rel[0])
    phi = math.asin(float(rel[2] / distance))
    return distance, theta, phi


def dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)))


def position_from_state(state: np.ndarray) -> np.ndarray:
    return np.asarray([state[0], state[2], state[4]], dtype=float)


def velocity_from_state(state: np.ndarray) -> np.ndarray:
    return np.asarray([state[1], state[3], state[5]], dtype=float)


def state_from_position_velocity(position: np.ndarray, velocity: np.ndarray) -> np.ndarray:
    return np.asarray(
        [position[0], velocity[0], position[1], velocity[1], position[2], velocity[2]],
        dtype=float,
    )


def measurement_function(state: np.ndarray, bs_set: VSC | Iterable[BaseStation], pbs_index: int) -> np.ndarray:
    """Map state x=[x,vx,y,vy,z,vz] to the paper's 12-D measurement vector.

    Output order:
    [theta_pbs, phi_pbs, v_pbs, d_pbs,
     theta_sbs1, phi_sbs1, v_pbs+v_sbs1, d_pbs+d_sbs1,
     theta_sbs2, phi_sbs2, v_pbs+v_sbs2, d_pbs+d_sbs2]
    """

    stations = _stations_tuple(bs_set)
    ordered = order_base_stations(stations, pbs_index)
    single = [_single_bs_measurement(state, bs) for bs in ordered]
    pbs = single[0]
    sbs1 = single[1]
    sbs2 = single[2]

    return np.asarray(
        [
            pbs[0],
            pbs[1],
            pbs[2],
            pbs[3],
            sbs1[0],
            sbs1[1],
            pbs[2] + sbs1[2],
            pbs[3] + sbs1[3],
            sbs2[0],
            sbs2[1],
            pbs[2] + sbs2[2],
            pbs[3] + sbs2[3],
        ],
        dtype=float,
    )


def order_base_stations(
    stations: tuple[BaseStation, BaseStation, BaseStation], pbs_index: int
) -> tuple[BaseStation, BaseStation, BaseStation]:
    if not 0 <= pbs_index < len(stations):
        raise IndexError(f"pbs_index must be in [0, {len(stations) - 1}], got {pbs_index}")
    return (stations[pbs_index],) + tuple(bs for i, bs in enumerate(stations) if i != pbs_index)


def component_indices_for_roles(active_roles: Iterable[str]) -> np.ndarray:
    mapping = {
        "pbs": np.arange(0, 4),
        "sbs1": np.arange(4, 8),
        "sbs2": np.arange(8, 12),
    }
    parts = [mapping[role] for role in active_roles]
    if not parts:
        return np.asarray([], dtype=int)
    return np.concatenate(parts).astype(int)


def _single_bs_measurement(state: np.ndarray, bs: BaseStation) -> tuple[float, float, float, float]:
    pos = position_from_state(state)
    vel = velocity_from_state(state)
    rel = pos - bs.position
    distance = float(np.linalg.norm(rel))
    if distance < 1e-12:
        raise ValueError("UAV position coincides with a base station")

    horizontal = np.array([rel[0], rel[1], 0.0], dtype=float)
    horizontal_norm = float(np.linalg.norm(horizontal))
    if horizontal_norm < 1e-12:
        e_p = np.array([math.cos(bs.alpha), math.sin(bs.alpha), 0.0], dtype=float)
    else:
        e_p = horizontal / horizontal_norm

    e_b = np.array([math.cos(bs.alpha), math.sin(bs.alpha), 0.0], dtype=float)
    e_t = rel / distance
    theta = math.acos(float(np.clip(np.dot(e_p, e_b), -1.0, 1.0)))
    phi = math.asin(float(np.clip(rel[2] / distance, -1.0, 1.0)))
    radial_velocity = -float(np.dot(vel, e_t))
    return theta, phi, radial_velocity, distance


def _azimuth_to(vector: np.ndarray) -> float:
    return math.atan2(float(vector[1]), float(vector[0]))


def _stations_tuple(bs_set: VSC | Iterable[BaseStation]) -> tuple[BaseStation, BaseStation, BaseStation]:
    if isinstance(bs_set, VSC):
        return bs_set.base_stations
    stations = tuple(bs_set)
    if len(stations) != 3:
        raise ValueError("This reproduction stage expects exactly three BSs in one VSC")
    return stations  # type: ignore[return-value]
