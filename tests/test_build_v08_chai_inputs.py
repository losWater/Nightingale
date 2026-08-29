from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "夜莺B" / "scripts" / "build_v08_chai_inputs.py"


def load_module():
    spec = importlib.util.spec_from_file_location("nightingale_v08_inputs", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载：{SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BuildV08InputsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_only_one_codes_survive(self):
        rows = [{"词": chr(0x4E00 + i), "频率": i,
                 **({"简码长度": 1} if i < 26 else {"简码长度": 2}),
                 "排序序号": i} for i in range(30)]
        chars = [row["词"] for row in rows]
        result, counts = self.mod.build_elements(rows, chars[:26], chars[:28])
        self.assertEqual(sum(x.get("简码长度") == 1 for x in result), 26)
        self.assertFalse(any(x.get("简码长度") == 2 for x in result))
        self.assertTrue(all(x["排序序号"] == i for i, x in enumerate(result)))
        self.assertEqual(counts["removed_level_2"], 4)

    def test_non_character_is_rejected(self):
        rows = [{"词": chr(0x4E00 + i), "简码长度": 1} for i in range(26)]
        rows.append({"词": "词组"})
        with self.assertRaisesRegex(ValueError, "混入非单字"):
            self.mod.build_elements(rows, [row["词"] for row in rows[:26]],
                                    [row["词"] for row in rows])

    def test_exactly_twenty_six_one_codes_are_required(self):
        rows = [{"词": chr(0x4E00 + i), "简码长度": 1} for i in range(25)]
        with self.assertRaisesRegex(ValueError, "恰为26"):
            self.mod.build_elements(rows, [row["词"] for row in rows],
                                    [row["词"] for row in rows])

    def test_measurement_objective_contains_only_character_targets(self):
        objective = self.mod.measurement_objective()
        self.assertEqual(set(objective), {
            "characters_full", "characters_short", "regularization_strength"
        })
        self.assertEqual([x["top"] for x in objective["characters_short"]["tiers"]],
                         [300, 500, 1674, 3527, 6000])
        self.assertTrue(all(value == 0.0 for value in
                            objective["characters_short"]["tiers"][0]["weighted_fingering"]))
        self.assertNotIn("weighted_fingering",
                         objective["characters_short"]["tiers"][-1])
        self.assertEqual(objective["characters_full"]["effective_duplication"], 0.0)
        self.assertTrue(all("effective_duplication" in tier
                            for tier in objective["characters_full"]["tiers"]))

    def test_config_recomputes_two_code_before_three_code(self):
        source = {"encoder": {"short_code": [
            {"length_equal": 1, "schemes": [{"prefix": 3}]},
            {"length_equal": 2, "schemes": [{"prefix": 2}]},
        ]}, "optimization": {"objective": {}, "metaheuristic": None}}
        config = self.mod.build_config(source)
        one_char = next(x for x in config["encoder"]["short_code"]
                        if x.get("length_equal") == 1)
        self.assertEqual(one_char["schemes"], [
            {"prefix": 2, "count": 1}, {"prefix": 3, "count": 1}
        ])
        self.assertEqual(sum(x.get("length_equal") == 1
                             for x in config["encoder"]["short_code"]), 1)


if __name__ == "__main__":
    unittest.main()
