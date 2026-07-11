from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .geometry import BaseStation, VSC, dist, position_from_state


@dataclass(frozen=True)
class BlockageState:
    """Blocked physical BS indices in the current time slot."""

    blocked: frozenset[int] = frozenset()

    @classmethod
    def from_indices(cls, indices: Iterable[int] = ()) -> "BlockageState":
        return cls(frozenset(int(i) for i in indices))

    def is_blocked(self, bs_index: int) -> bool:
        return bs_index in self.blocked


def select_pbs(
    predicted_state: np.ndarray,
    bs_set: VSC | tuple[BaseStation, BaseStation, BaseStation],
    blockage_state: BlockageState | None = None,
) -> int:
    """Select the nearest unblocked BS as PBS.

    If all BSs are blocked, return the nearest BS. The caller can then skip the
    EKF update because no usable measurement exists.
    """

    stations = bs_set.base_stations if isinstance(bs_set, VSC) else bs_set
    blockage_state = blockage_state or BlockageState()
    pos = position_from_state(predicted_state)
    ranked = sorted(range(len(stations)), key=lambda i: dist(pos, stations[i].position))
    for index in ranked:
        if not blockage_state.is_blocked(index):
            return index
    return ranked[0]


def in_vsc_buffer(theta: float, vsc: VSC) -> bool:
    return (vsc.theta_min - vsc.buffer_theta) <= theta <= (vsc.theta_min + vsc.buffer_theta) or (
        vsc.theta_max - vsc.buffer_theta
    ) <= theta <= (vsc.theta_max + vsc.buffer_theta)


def choose_vsc_index(theta: float, current_vsc_index: int, vsc: VSC, time_index: int) -> int:
    """Toy VSC handover: alternate VSCs while the predicted angle is in buffer."""

    if in_vsc_buffer(theta, vsc):
        return current_vsc_index if time_index % 2 == 0 else 1 - current_vsc_index
    if theta < vsc.theta_min:
        return 0
    if theta > vsc.theta_max:
        return 1
    return current_vsc_index
