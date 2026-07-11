import tempfile
import unittest
from pathlib import Path

from isac_uav.reproduction_suite import figure_reproduction_map, write_figure_reproduction_map


class ReproductionSuiteTest(unittest.TestCase):
    def test_figure_map_covers_section_v_figures(self):
        figures = [item.figure for item in figure_reproduction_map()]
        self.assertEqual(figures, [f"Fig. {index}" for index in range(6, 14)])

    def test_figure_map_writes_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = write_figure_reproduction_map(Path(tmp) / "figure_map.md")
            text = out.read_text(encoding="utf-8")
            self.assertIn("Fig. 6", text)
            self.assertIn("python main.py --scenario multi", text)
            self.assertIn("outputs/vsc_pbs_history.png", text)


if __name__ == "__main__":
    unittest.main()
