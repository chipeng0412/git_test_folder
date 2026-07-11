from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.constants import c


@dataclass(frozen=True)
class RadarConfig:
    """OFDM/UPA parameters used by the paper's sensing model."""

    m_subcarriers: int = 64
    n_symbols: int = 64
    nx_rx: int = 8
    nz_rx: int = 8
    f0: float = 60e9
    delta_f: float = 380e3
    ts: float = 1e-6

    @property
    def wavelength(self) -> float:
        return c / self.f0

    @property
    def dx(self) -> float:
        return self.wavelength / 2.0

    @property
    def dz(self) -> float:
        return self.wavelength / 2.0

    @property
    def nr(self) -> int:
        return self.nx_rx * self.nz_rx


@dataclass(frozen=True, init=False)
class TargetParameters:
    theta: float
    phi: float
    range_value: float
    velocity_value: float

    def __init__(
        self,
        theta: float,
        phi: float,
        range_value: float | None = None,
        velocity_value: float | None = None,
        distance: float | None = None,
        radial_velocity: float | None = None,
    ) -> None:
        if range_value is None:
            range_value = distance
        if velocity_value is None:
            velocity_value = radial_velocity
        if range_value is None or velocity_value is None:
            raise TypeError("TargetParameters needs range_value/velocity_value or distance/radial_velocity")
        object.__setattr__(self, "theta", theta)
        object.__setattr__(self, "phi", phi)
        object.__setattr__(self, "range_value", float(range_value))
        object.__setattr__(self, "velocity_value", float(velocity_value))

    @property
    def distance(self) -> float:
        return self.range_value

    @property
    def radial_velocity(self) -> float:
        return self.velocity_value


@dataclass(frozen=True)
class MusicEstimate:
    theta: float
    phi: float
    range_value: float
    velocity_value: float

    @property
    def distance(self) -> float:
        return self.range_value

    @property
    def radial_velocity(self) -> float:
        return self.velocity_value


@dataclass(frozen=True)
class DelayDopplerMatch:
    tau: float
    fd: float
    score: float


@dataclass(frozen=True)
class EchoMode:
    """Conversion between paper measurements and delay/Doppler values."""

    delay_distance_factor: float
    doppler_velocity_factor: float


MONOSTATIC = EchoMode(delay_distance_factor=2.0, doppler_velocity_factor=2.0)
BISTATIC_SUM = EchoMode(delay_distance_factor=1.0, doppler_velocity_factor=1.0)


def spatial_directions(theta: float, phi: float) -> tuple[float, float]:
    psi = math.cos(phi) * math.cos(theta)
    omega = math.sin(phi)
    return psi, omega


def upa_steering(psi: float, omega: float, config: RadarConfig) -> np.ndarray:
    ax = np.exp(1j * 2.0 * np.pi * config.f0 * config.dx * psi / c * np.arange(config.nx_rx))
    az = np.exp(1j * 2.0 * np.pi * config.f0 * config.dz * omega / c * np.arange(config.nz_rx))
    return np.kron(ax, az).astype(complex)


def doppler_steering(fd: float, length: int, config: RadarConfig) -> np.ndarray:
    return np.exp(1j * 2.0 * np.pi * fd * config.ts * np.arange(length)).astype(complex)


def delay_steering(tau: float, config: RadarConfig) -> np.ndarray:
    return np.exp(-1j * 2.0 * np.pi * config.delta_f * tau * np.arange(config.m_subcarriers)).astype(complex)


def synthesize_single_target_echo(
    target: TargetParameters,
    config: RadarConfig,
    mode: EchoMode = MONOSTATIC,
    snr_db: float = 30.0,
    clutter_amplitude: float = 10.0,
    seed: int = 0,
) -> np.ndarray:
    """Create a single-BS echo tensor Y[antenna, OFDM symbol, subcarrier].

    This is a compact implementation of the paper's Eq. (11): one moving UAV
    plus one static clutter component. Static clutter has zero Doppler and is
    removed by `apply_mti`.
    """

    rng = np.random.default_rng(seed)
    psi, omega = spatial_directions(target.theta, target.phi)
    array = upa_steering(psi, omega, config)
    tau = mode.delay_distance_factor * target.range_value / c
    fd = mode.doppler_velocity_factor * config.f0 * target.velocity_value / c
    doppler = doppler_steering(fd, config.n_symbols, config)
    delay = delay_steering(tau, config)
    signal = array[:, None, None] * doppler[None, :, None] * delay[None, None, :]

    clutter = np.zeros_like(signal)
    if clutter_amplitude:
        clutter_psi, clutter_omega = spatial_directions(math.radians(70.0), math.radians(8.0))
        clutter_array = upa_steering(clutter_psi, clutter_omega, config)
        clutter_delay = delay_steering(2.0 * 170.0 / c, config)
        clutter = clutter_amplitude * clutter_array[:, None, None] * clutter_delay[None, None, :]

    signal_power = float(np.mean(np.abs(signal) ** 2))
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise = math.sqrt(noise_power / 2.0) * (
        rng.standard_normal(signal.shape) + 1j * rng.standard_normal(signal.shape)
    )
    return signal + clutter + noise


def synthesize_multi_target_echo(
    targets: list[TargetParameters],
    config: RadarConfig,
    mode: EchoMode = MONOSTATIC,
    snr_db: float = 35.0,
    clutter_amplitude: float = 8.0,
    amplitudes: np.ndarray | None = None,
    seed: int = 0,
) -> np.ndarray:
    """Create an antenna-symbol-subcarrier echo tensor for multiple UAVs."""

    rng = np.random.default_rng(seed)
    echo = np.zeros((config.nr, config.n_symbols, config.m_subcarriers), dtype=complex)
    if amplitudes is None:
        amplitudes = np.ones(len(targets), dtype=float)

    for target, amplitude in zip(targets, amplitudes):
        psi, omega = spatial_directions(target.theta, target.phi)
        array = upa_steering(psi, omega, config)
        tau = mode.delay_distance_factor * target.range_value / c
        fd = mode.doppler_velocity_factor * config.f0 * target.velocity_value / c
        doppler = doppler_steering(fd, config.n_symbols, config)
        delay = delay_steering(tau, config)
        echo += complex(amplitude) * array[:, None, None] * doppler[None, :, None] * delay[None, None, :]

    if clutter_amplitude:
        clutter_psi, clutter_omega = spatial_directions(math.radians(70.0), math.radians(8.0))
        clutter_array = upa_steering(clutter_psi, clutter_omega, config)
        clutter_delay = delay_steering(2.0 * 170.0 / c, config)
        echo += clutter_amplitude * clutter_array[:, None, None] * clutter_delay[None, None, :]

    signal_power = float(np.mean(np.abs(echo) ** 2))
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise = math.sqrt(noise_power / 2.0) * (
        rng.standard_normal(echo.shape) + 1j * rng.standard_normal(echo.shape)
    )
    return echo + noise


def apply_mti(echo: np.ndarray) -> np.ndarray:
    """Moving target indicator: subtract adjacent OFDM symbols."""

    return echo[:, :-1, :] - echo[:, 1:, :]


def estimate_angle_music(
    dynamic_echo: np.ndarray,
    config: RadarConfig,
    theta_grid: np.ndarray,
    phi_grid: np.ndarray,
    n_targets: int = 1,
) -> tuple[float, float, np.ndarray]:
    snapshots = dynamic_echo.reshape(config.nr, -1)
    covariance = snapshots @ snapshots.conj().T / snapshots.shape[1]
    noise_space = _noise_space(covariance, n_targets)

    spectrum = np.zeros((len(theta_grid), len(phi_grid)), dtype=float)
    projection = noise_space @ noise_space.conj().T
    for i, theta in enumerate(theta_grid):
        for j, phi in enumerate(phi_grid):
            psi, omega = spatial_directions(float(theta), float(phi))
            steering = upa_steering(psi, omega, config)
            denom = steering.conj().T @ projection @ steering
            spectrum[i, j] = 1.0 / max(abs(denom), 1e-18)

    row, col = np.unravel_index(int(np.argmax(spectrum)), spectrum.shape)
    return float(theta_grid[row]), float(phi_grid[col]), spectrum


def estimate_angle_music_peaks(
    dynamic_echo: np.ndarray,
    config: RadarConfig,
    theta_grid: np.ndarray,
    phi_grid: np.ndarray,
    n_targets: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    _, _, spectrum = estimate_angle_music(
        dynamic_echo,
        config,
        theta_grid=theta_grid,
        phi_grid=phi_grid,
        n_targets=n_targets,
    )
    indices = _top_2d_peak_indices(spectrum, n_targets)
    theta_peaks = np.asarray([theta_grid[row] for row, _ in indices], dtype=float)
    phi_peaks = np.asarray([phi_grid[col] for _, col in indices], dtype=float)
    return theta_peaks, phi_peaks, spectrum


def beamform_dynamic_echo(dynamic_echo: np.ndarray, theta: float, phi: float, config: RadarConfig) -> np.ndarray:
    psi, omega = spatial_directions(theta, phi)
    steering = upa_steering(psi, omega, config) / math.sqrt(config.nr)
    return np.einsum("a,anm->nm", steering.conj(), dynamic_echo)


def estimate_delay_doppler_music(
    beamformed_echo: np.ndarray,
    config: RadarConfig,
    tau_grid: np.ndarray,
    fd_grid: np.ndarray,
    n_targets: int = 1,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    doppler_cov = beamformed_echo @ beamformed_echo.conj().T / beamformed_echo.shape[1]
    delay_snapshots = beamformed_echo.T
    delay_cov = delay_snapshots @ delay_snapshots.conj().T / delay_snapshots.shape[1]

    doppler_noise = _noise_space(doppler_cov, n_targets)
    delay_noise = _noise_space(delay_cov, n_targets)
    doppler_projection = doppler_noise @ doppler_noise.conj().T
    delay_projection = delay_noise @ delay_noise.conj().T

    doppler_spectrum = np.zeros(len(fd_grid), dtype=float)
    for i, fd in enumerate(fd_grid):
        steering = doppler_steering(float(fd), beamformed_echo.shape[0], config)
        denom = steering.conj().T @ doppler_projection @ steering
        doppler_spectrum[i] = 1.0 / max(abs(denom), 1e-18)

    delay_spectrum = np.zeros(len(tau_grid), dtype=float)
    for i, tau in enumerate(tau_grid):
        steering = delay_steering(float(tau), config)
        denom = steering.conj().T @ delay_projection @ steering
        delay_spectrum[i] = 1.0 / max(abs(denom), 1e-18)

    tau_hat = float(tau_grid[int(np.argmax(delay_spectrum))])
    fd_hat = float(fd_grid[int(np.argmax(doppler_spectrum))])
    return tau_hat, fd_hat, delay_spectrum, doppler_spectrum


def synthesize_beamformed_delay_doppler(
    targets: list[TargetParameters],
    config: RadarConfig,
    mode: EchoMode = MONOSTATIC,
    snr_db: float = 40.0,
    amplitudes: np.ndarray | None = None,
    seed: int = 0,
) -> np.ndarray:
    """Create Ydy in Eq. (20), after angle beamforming, for Algorithm 1 tests."""

    rng = np.random.default_rng(seed)
    n_time = config.n_symbols - 1
    echo = np.zeros((n_time, config.m_subcarriers), dtype=complex)
    if amplitudes is None:
        amplitudes = np.ones(len(targets), dtype=float)

    for target, amplitude in zip(targets, amplitudes):
        tau = mode.delay_distance_factor * target.range_value / c
        fd = mode.doppler_velocity_factor * config.f0 * target.velocity_value / c
        echo += complex(amplitude) * np.outer(
            doppler_steering(fd, n_time, config),
            delay_steering(tau, config),
        )

    signal_power = float(np.mean(np.abs(echo) ** 2))
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise = math.sqrt(noise_power / 2.0) * (
        rng.standard_normal(echo.shape) + 1j * rng.standard_normal(echo.shape)
    )
    return echo + noise


def estimate_delay_doppler_peaks(
    beamformed_echo: np.ndarray,
    config: RadarConfig,
    tau_grid: np.ndarray,
    fd_grid: np.ndarray,
    n_targets: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    _, _, delay_spectrum, doppler_spectrum = estimate_delay_doppler_music(
        beamformed_echo,
        config,
        tau_grid,
        fd_grid,
        n_targets=n_targets,
    )
    tau_indices = _top_peak_indices(delay_spectrum, n_targets)
    fd_indices = _top_peak_indices(doppler_spectrum, n_targets)
    return tau_grid[tau_indices], fd_grid[fd_indices], delay_spectrum, doppler_spectrum


def match_delay_doppler_svd(
    beamformed_echo: np.ndarray,
    config: RadarConfig,
    tau_candidates: np.ndarray,
    fd_candidates: np.ndarray,
    n_targets: int,
) -> list[DelayDopplerMatch]:
    """Match Doppler and delay estimates using the paper's Algorithm 1 idea."""

    u_matrix, _, vh_matrix = np.linalg.svd(beamformed_echo, full_matrices=False)
    remaining_rows = set(range(len(fd_candidates)))
    remaining_cols = set(range(len(tau_candidates)))
    matches: list[DelayDopplerMatch] = []

    for basis_index in range(n_targets):
        basis = np.outer(u_matrix[:, basis_index], vh_matrix[basis_index, :])
        best: tuple[float, int, int] | None = None
        for row in remaining_rows:
            fd_vector = doppler_steering(float(fd_candidates[row]), beamformed_echo.shape[0], config)
            fd_norm = float(np.linalg.norm(fd_vector))
            for col in remaining_cols:
                tau_vector = delay_steering(float(tau_candidates[col]), config)
                tau_norm = float(np.linalg.norm(tau_vector))
                score = abs(fd_vector.conj().T @ basis @ tau_vector.conj()) / (fd_norm * tau_norm)
                if best is None or score > best[0]:
                    best = (float(score), row, col)
        if best is None:
            break
        score, row, col = best
        remaining_rows.remove(row)
        remaining_cols.remove(col)
        matches.append(DelayDopplerMatch(tau=float(tau_candidates[col]), fd=float(fd_candidates[row]), score=score))
    return matches


def estimate_single_target_parameters(
    echo: np.ndarray,
    config: RadarConfig,
    theta_grid: np.ndarray,
    phi_grid: np.ndarray,
    range_grid: np.ndarray | None = None,
    velocity_grid: np.ndarray | None = None,
    mode: EchoMode = MONOSTATIC,
    distance_grid: np.ndarray | None = None,
) -> MusicEstimate:
    if range_grid is None:
        range_grid = distance_grid
    if range_grid is None or velocity_grid is None:
        raise TypeError("estimate_single_target_parameters needs range_grid/velocity_grid")
    dynamic = apply_mti(echo)
    theta_hat, phi_hat, _ = estimate_angle_music(dynamic, config, theta_grid, phi_grid)
    beamformed = beamform_dynamic_echo(dynamic, theta_hat, phi_hat, config)
    tau_grid = mode.delay_distance_factor * range_grid / c
    fd_grid = mode.doppler_velocity_factor * config.f0 * velocity_grid / c
    tau_hat, fd_hat, _, _ = estimate_delay_doppler_music(beamformed, config, tau_grid, fd_grid)
    return MusicEstimate(
        theta=theta_hat,
        phi=phi_hat,
        range_value=tau_hat * c / mode.delay_distance_factor,
        velocity_value=fd_hat * c / (mode.doppler_velocity_factor * config.f0),
    )


def _noise_space(covariance: np.ndarray, n_targets: int) -> np.ndarray:
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    sorted_vectors = eigenvectors[:, order]
    return sorted_vectors[:, n_targets:]


def _top_peak_indices(spectrum: np.ndarray, n_peaks: int) -> np.ndarray:
    order = np.argsort(spectrum)[::-1]
    selected: list[int] = []
    min_separation = max(1, len(spectrum) // 80)
    for index in order:
        if all(abs(int(index) - existing) > min_separation for existing in selected):
            selected.append(int(index))
            if len(selected) == n_peaks:
                break
    if len(selected) < n_peaks:
        selected.extend(int(index) for index in order if int(index) not in selected)
    return np.asarray(selected[:n_peaks], dtype=int)


def _top_2d_peak_indices(spectrum: np.ndarray, n_peaks: int) -> list[tuple[int, int]]:
    flat_order = np.argsort(spectrum.ravel())[::-1]
    selected: list[tuple[int, int]] = []
    row_separation = max(1, spectrum.shape[0] // 40)
    col_separation = max(1, spectrum.shape[1] // 40)
    for flat_index in flat_order:
        row, col = np.unravel_index(int(flat_index), spectrum.shape)
        if all(abs(row - old_row) > row_separation or abs(col - old_col) > col_separation for old_row, old_col in selected):
            selected.append((int(row), int(col)))
            if len(selected) == n_peaks:
                break
    return selected
