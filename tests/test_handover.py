import unittest

import numpy as np

from isac_uav.geometry import build_adjacent_vsc_pair, build_vsc, state_from_position_velocity
from isac_uav.handover import BlockageState, select_pbs


class HandoverTest(unittest.TestCase):
    def test_selects_nearest_unblocked_bs(self):
        vsc = build_vsc()
        state = state_from_position_velocity(np.array([10.0, 0.0, 50.0]), np.zeros(3))
        self.assertEqual(select_pbs(state, vsc), 0)
        self.assertNotEqual(select_pbs(state, vsc, BlockageState.from_indices([0])), 0)

    def test_adjacent_vsc_pair_has_shared_sector(self):
        network = build_adjacent_vsc_pair()
        self.assertEqual(len(network.vscs), 2)
        shared_from_vsc1 = network.vscs[0].base_stations[0]
        shared_from_vsc2 = network.vscs[1].base_stations[2]
        self.assertEqual(shared_from_vsc1.name, "1-1")
        self.assertEqual(shared_from_vsc2.name, "2-3")
        self.assertTrue(np.allclose(shared_from_vsc1.position, shared_from_vsc2.position))


if __name__ == "__main__":
    unittest.main()
