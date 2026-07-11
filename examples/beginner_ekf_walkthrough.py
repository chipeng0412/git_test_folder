from __future__ import annotations

"""Beginner-friendly EKF walkthrough for the UAV tracking reproduction.

Run from the project root:

    . .venv/bin/activate
    python examples/beginner_ekf_walkthrough.py

This file is intentionally verbose. The production code in `isac_uav/` is more
compact; this example explains the same idea with smaller steps and comments.
"""

from pathlib import Path
import sys

import numpy as np


# When Python runs a file inside `examples/`, it puts `examples/` on sys.path.
# The project package `isac_uav` lives one directory above `examples/`, so we
# add the project root explicitly. This makes the script work with:
# `python examples/beginner_ekf_walkthrough.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from isac_uav.ekf import ExtendedKalmanFilter  # noqa: E402
from isac_uav.experiments import default_measurement_covariance  # noqa: E402
from isac_uav.geometry import (  # noqa: E402
    component_indices_for_roles,
    measurement_function,
    state_from_position_velocity,
)
from isac_uav.geometry import build_vsc  # noqa: E402


def main() -> None:
    # Make numpy print shorter numbers so the terminal output is easier to read.
    np.set_printoptions(precision=3, suppress=True)

    # A random generator makes the artificial measurement noise reproducible.
    # If you change the seed, the noise changes, but the code flow is identical.
    rng = np.random.default_rng(seed=42)

    # Step 1: build the geometry.
    # A VSC contains three base stations. The paper uses these BSs to measure
    # UAV angles, distances, and radial velocities.
    vsc = build_vsc()

    # Step 2: create one true UAV state.
    # The repo stores a UAV state as [x, vx, y, vy, z, vz].
    # This helper lets beginners write position and velocity separately.
    true_position = np.array([150.0, -80.0, 80.0])
    true_velocity = np.array([5.0, 12.0, 0.5])
    true_state = state_from_position_velocity(true_position, true_velocity)

    # Step 3: choose the PBS.
    # Here we keep the example simple and force BS0 to be the primary BS.
    # In the full experiment, `select_pbs()` chooses the nearest unblocked BS.
    pbs_index = 0

    # Step 4: compute the clean 12-D measurement.
    # This is h(x): "if the true UAV state is known, what should the BSs see?"
    clean_measurement = measurement_function(true_state, vsc, pbs_index)

    # Step 5: add artificial measurement noise.
    # The paper obtains measurements through OFDM echo + MTI + MUSIC.
    # In the first-stage reproduction, we replace that signal chain with:
    # clean physics-based measurement + Gaussian noise.
    measurement_cov = default_measurement_covariance()
    noise = rng.multivariate_normal(np.zeros(12), measurement_cov)
    noisy_measurement = clean_measurement + noise

    # Step 6: decide which measurement components are available.
    # With no blockage, PBS + two SBSs are all active, so we use all 12 numbers.
    # If only PBS is available, use: component_indices_for_roles(("pbs",)).
    active_components = component_indices_for_roles(("pbs", "sbs1", "sbs2"))
    observed = noisy_measurement[active_components]

    # Step 7: create an intentionally wrong initial guess.
    # EKF never starts from perfect truth in a real system; it starts with a
    # rough estimate and improves as measurements arrive.
    initial_guess = true_state.copy()
    initial_guess[[0, 2, 4]] += np.array([10.0, -8.0, 4.0])
    initial_guess[[1, 3, 5]] += np.array([2.0, -3.0, 1.0])

    # Step 8: describe how uncertain the initial guess is.
    # Larger diagonal values mean "I am less confident about this variable."
    initial_covariance = np.diag([100.0, 9.0, 100.0, 9.0, 25.0, 4.0])

    # Step 9: describe model noise.
    # The constant-velocity model is not perfect; UAVs can accelerate or turn.
    # Process covariance tells EKF how much model error to tolerate.
    process_covariance = np.diag([0.08, 0.8, 0.08, 0.8, 0.04, 0.3])

    # Step 10: create the EKF object.
    # `measurement_fn` is passed as a small function because EKF should not need
    # to know the details of BS geometry. It only asks: given state, what is h(x)?
    ekf = ExtendedKalmanFilter(
        state=initial_guess,
        covariance=initial_covariance,
        process_cov=process_covariance,
        measurement_cov=measurement_cov,
        dt=0.2,
        measurement_fn=lambda state, pbs: measurement_function(state, vsc, pbs),
    )

    # Print the situation before filtering.
    print("true state [x, vx, y, vy, z, vz]:")
    print(true_state)
    print()
    print("initial EKF guess:")
    print(ekf.state)
    print()
    print("initial position error [x, y, z] meters:")
    print(position_error(ekf.state, true_state))
    print()

    # Step 11: prediction.
    # This uses only motion logic:
    # next_position = current_position + current_velocity * dt
    # next_velocity = current_velocity
    ekf.predict()
    print("after predict, before measurement update:")
    print(ekf.state)
    print()

    # Step 12: update.
    # This compares the actual noisy measurement with the predicted measurement
    # and moves the state estimate toward a more plausible value.
    ekf.update(observed, active_components, pbs_index)

    # Print the result after one EKF correction.
    print("after update with one 12-D measurement:")
    print(ekf.state)
    print()
    print("final position error [x, y, z] meters:")
    print(position_error(ekf.state, true_state))
    print()
    print("final velocity error [vx, vy, vz] m/s:")
    print(velocity_error(ekf.state, true_state))


def position_error(estimated_state: np.ndarray, true_state: np.ndarray) -> np.ndarray:
    # State order is [x, vx, y, vy, z, vz], so positions are indices 0, 2, 4.
    return estimated_state[[0, 2, 4]] - true_state[[0, 2, 4]]


def velocity_error(estimated_state: np.ndarray, true_state: np.ndarray) -> np.ndarray:
    # State order is [x, vx, y, vy, z, vz], so velocities are indices 1, 3, 5.
    return estimated_state[[1, 3, 5]] - true_state[[1, 3, 5]]


if __name__ == "__main__":
    main()
