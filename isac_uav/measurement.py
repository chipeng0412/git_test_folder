from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import (
    MEASUREMENT_SIZE,
    VSC,
    component_indices_for_roles,
    measurement_function,
    order_base_stations,
)
from .handover import BlockageState


@dataclass(frozen=True)
class Measurement:
    full: np.ndarray
    observed: np.ndarray
    active_indices: np.ndarray
    active_roles: tuple[str, ...]
    pbs_index: int


def build_measurement_from_full(
    full: np.ndarray,
    blockage_state: BlockageState,
    vsc: VSC,
    pbs_index: int,
) -> Measurement:
    active_roles = active_measurement_roles(vsc, pbs_index, blockage_state)
    active_indices = component_indices_for_roles(active_roles)
    return Measurement(
        full=full,
        observed=full[active_indices],
        active_indices=active_indices,
        active_roles=active_roles,
        pbs_index=pbs_index,
    )


def generate_measurement(
    true_state: np.ndarray,
    noise_cov: np.ndarray,
    blockage_state: BlockageState,
    vsc: VSC,
    pbs_index: int,
    rng: np.random.Generator,
) -> Measurement:
    """Generate a noisy measurement and drop blocked BS components.

    This is the first-stage substitute for the paper's MTI + MUSIC output.
    """

    clean = measurement_function(true_state, vsc, pbs_index)
    noise = rng.multivariate_normal(np.zeros(MEASUREMENT_SIZE), noise_cov)
    full = clean + noise
    return build_measurement_from_full(full, blockage_state, vsc, pbs_index)


def active_measurement_roles(vsc: VSC, pbs_index: int, blockage_state: BlockageState) -> tuple[str, ...]:
    if blockage_state.is_blocked(pbs_index):
        return ()

    ordered = order_base_stations(vsc.base_stations, pbs_index)
    physical_indices = {bs.name: i for i, bs in enumerate(vsc.base_stations)}
    roles: list[str] = ["pbs"]
    for role, bs in (("sbs1", ordered[1]), ("sbs2", ordered[2])):
        if not blockage_state.is_blocked(physical_indices[bs.name]):
            roles.append(role)
    return tuple(roles)
