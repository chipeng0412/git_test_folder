import math
import unittest

import numpy as np

from isac_uav.geometry import build_vsc, cart2sph, measurement_function, sph2cart, state_from_position_velocity


class GeometryTest(unittest.TestCase):
    def test_spherical_round_trip(self):
        point = sph2cart(120.0, math.radians(40), math.radians(15))
        distance, theta, phi = cart2sph(point)
        self.assertAlmostEqual(distance, 120.0, places=8)
        self.assertAlmostEqual(theta, math.radians(40), places=8)
        self.assertAlmostEqual(phi, math.radians(15), places=8)

    def test_measurement_ranges_and_radial_velocity_sign(self):
        vsc = build_vsc()
        state = state_from_position_velocity(np.array([120.0, 0.0, 60.0]), np.array([10.0, 0.0, 0.0]))
        measurement = measurement_function(state, vsc, 0)
        self.assertEqual(measurement.shape, (12,))
        self.assertGreaterEqual(measurement[0], 0.0)
        self.assertLessEqual(measurement[0], math.pi)
        self.assertGreater(measurement[1], 0.0)
        self.assertLess(measurement[1], math.pi / 2)
        self.assertLess(measurement[2], 0.0)


if __name__ == "__main__":
    unittest.main()
