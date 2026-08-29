from __future__ import annotations

import importlib.util
import random
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "夜莺B" / "scripts" / "build_random_layout_seed.py"


def load_module():
    spec = importlib.util.spec_from_file_location("nightingale_random_seed", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载：{SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RandomLayoutSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    @staticmethod
    def chain_space():
        return {
            "a": [{"value": "x"}, {"value": "y"}],
            "b": [
                {"value": "m", "condition": [{"element": "a", "op": "是", "value": "x"}]},
                {"value": "n", "condition": [{"element": "a", "op": "是", "value": "y"}]},
            ],
            "c": [
                {"value": "u", "condition": [{"element": "b", "op": "是", "value": "m"}]},
                {"value": "v", "condition": [{"element": "b", "op": "是", "value": "n"}]},
            ],
        }

    def test_three_element_chain_is_legal_for_one_thousand_seeds(self):
        space = self.chain_space()
        for seed in range(1000):
            mapping, selected = self.mod.generate_mapping(
                space, {"a": "stale", "b": "stale", "c": "stale"}, random.Random(seed)
            )
            self.mod.validate_mapping(space, mapping, selected)
            self.assertEqual(mapping["b"], "m" if mapping["a"] == "x" else "n")
            self.assertEqual(mapping["c"], "u" if mapping["b"] == "m" else "v")

    def test_backtracking_recovers_from_upstream_dead_end(self):
        space = {"a": [{"value": "bad"}, {"value": "good"}], "b": [
            {"value": "ok", "condition": [{"element": "a", "op": "是", "value": "good"}]}
        ]}
        for seed in range(20):
            mapping, _ = self.mod.generate_mapping(space, {}, random.Random(seed))
            self.assertEqual(mapping, {"a": "good", "b": "ok"})

    def test_cycle_is_rejected(self):
        space = {
            "a": [{"value": "x", "condition": [{"element": "b", "op": "是", "value": "y"}]}],
            "b": [{"value": "y", "condition": [{"element": "a", "op": "是", "value": "x"}]}],
        }
        with self.assertRaisesRegex(ValueError, "存在环"):
            self.mod.generate_mapping(space, {}, random.Random(1))

    def test_unknown_operator_is_rejected(self):
        space = {"a": [{"value": "x"}], "b": [
            {"value": "y", "condition": [{"element": "a", "op": "大概是", "value": "x"}]}
        ]}
        with self.assertRaisesRegex(ValueError, "未知条件操作符"):
            self.mod.generate_mapping(space, {}, random.Random(1))

    def test_unknown_reference_is_rejected(self):
        space = {"a": [{"value": "x", "condition": [
            {"element": "missing", "op": "是", "value": "y"}
        ]}]}
        with self.assertRaisesRegex(ValueError, "引用未知元素"):
            self.mod.generate_mapping(space, {}, random.Random(1))

    def test_single_choice_replaces_stale_template_value(self):
        mapping, _ = self.mod.generate_mapping(
            {"a": [{"value": "new"}]}, {"a": "stale"}, random.Random(1)
        )
        self.assertEqual(mapping["a"], "new")

    def test_unsatisfiable_space_is_rejected(self):
        space = {"a": [{"value": "x"}], "b": [
            {"value": "y", "condition": [{"element": "a", "op": "不是", "value": "x"}]}
        ]}
        with self.assertRaisesRegex(ValueError, "不存在满足"):
            self.mod.generate_mapping(space, {}, random.Random(1))

    def test_same_seed_is_reproducible(self):
        space = self.chain_space()
        first, _ = self.mod.generate_mapping(space, {}, random.Random(777))
        second, _ = self.mod.generate_mapping(space, {}, random.Random(777))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
