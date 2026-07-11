from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


MeasurementFunction = Callable[[np.ndarray, int], np.ndarray]


@dataclass
class ExtendedKalmanFilter:
    state: np.ndarray
    covariance: np.ndarray
    process_cov: np.ndarray
    measurement_cov: np.ndarray
    dt: float
    measurement_fn: MeasurementFunction

    def predict(self) -> np.ndarray:
        f = constant_velocity_transition(self.dt)
        self.state = f @ self.state
        self.covariance = f @ self.covariance @ f.T + self.process_cov
        self.covariance = _symmetrize(self.covariance)
        return self.state

    def update(self, z: np.ndarray, active_components: np.ndarray, pbs_index: int) -> np.ndarray:
        if len(active_components) == 0:
            return self.state

        h_full = self.measurement_fn(self.state, pbs_index)
        h_active = h_full[active_components]
        jacobian_full = numerical_jacobian(lambda x: self.measurement_fn(x, pbs_index), self.state)
        h_active_jacobian = jacobian_full[active_components, :]
        r_active = self.measurement_cov[np.ix_(active_components, active_components)]

        innovation = z - h_active
        s = h_active_jacobian @ self.covariance @ h_active_jacobian.T + r_active
        k_gain = self.covariance @ h_active_jacobian.T @ np.linalg.pinv(s)
        self.state = self.state + k_gain @ innovation

        identity = np.eye(self.covariance.shape[0])
        i_kh = identity - k_gain @ h_active_jacobian
        self.covariance = i_kh @ self.covariance @ i_kh.T + k_gain @ r_active @ k_gain.T
        self.covariance = _symmetrize(self.covariance)
        return self.state


def constant_velocity_transition(dt: float) -> np.ndarray:
    return np.asarray(
        [
            [1.0, dt, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, dt, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, dt],
            [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )


def numerical_jacobian(fn: Callable[[np.ndarray], np.ndarray], x: np.ndarray, epsilon: float = 1e-5) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    y0 = fn(x)
    jacobian = np.zeros((len(y0), len(x)), dtype=float)
    for j in range(len(x)):
        x1 = x.copy()
        x2 = x.copy()
        x1[j] += epsilon
        x2[j] -= epsilon
        jacobian[:, j] = (fn(x1) - fn(x2)) / (2.0 * epsilon)
    return jacobian


def _symmetrize(matrix: np.ndarray) -> np.ndarray:
    return 0.5 * (matrix + matrix.T)
