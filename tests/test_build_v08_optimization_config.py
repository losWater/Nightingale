import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "夜莺B" / "scripts" / "build_v08_optimization_config.py"
SPEC = importlib.util.spec_from_file_location("build_v08_optimization_config", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class OptimizationConfigTest(unittest.TestCase):
    def source(self):
        zero_tiers = [
            {
                "top": top,
                "levels": [{"length": 3, "frequency": 0.0}],
                "weighted_fingering": [0.0] * 8,
            }
            for top in (300, 500, 1500, 6000)
        ]
        return {
            "info": {"name": "baseline"},
            "optimization": {
                "objective": {
                    "characters_short": {"tiers": zero_tiers},
                    "characters_full": {"tiers": [
                        {"top": top, "effective_duplication": 0.0}
                        for top in (300, 500, 1500, 6000)
                    ]},
                },
                "metaheuristic": {
                    "algorithm": "SimulatedAnnealing",
                    "parameters": {"t_max": 1.0, "t_min": 1e-6, "steps": 1000},
                },
            },
        }

    def test_three_code_profile_changes_only_target_level(self):
        result = MOD.build_config(self.source(), "three-code-only", None, None, None)
        level = result["optimization"]["objective"]["characters_short"]["tiers"][3]["levels"][0]
        self.assertEqual(level["frequency"], -100.0)
        meta = result["optimization"]["metaheuristic"]
        self.assertNotIn("parameters", meta)
        self.assertEqual(meta["search_method"], {
            "random_move": 0.90, "random_swap": 0.09, "random_full_key_swap": 0.01
        })

    def test_fixed_temperature_requires_steps(self):
        with self.assertRaisesRegex(ValueError, "必须提供步数"):
            MOD.build_config(self.source(), "three-code-only", None, 0.1, 1e-6)

    def test_move_only_profile_changes_only_search_probabilities(self):
        mixed = MOD.build_config(
            self.source(), "layered-handfeel-v1-fullguard4", 20000, 3.0, 0.01
        )
        move_only = MOD.build_config(
            self.source(), "layered-handfeel-v1-fullguard4", 20000, 3.0, 0.01,
            "move-only",
        )
        self.assertEqual(
            move_only["optimization"]["metaheuristic"]["search_method"],
            {"random_move": 1.0, "random_swap": 0.0, "random_full_key_swap": 0.0},
        )
        mixed["optimization"]["metaheuristic"].pop("search_method")
        move_only["optimization"]["metaheuristic"].pop("search_method")
        self.assertEqual(mixed, move_only)

    def test_layered_handfeel_profile_sets_only_declared_layers(self):
        result = MOD.build_config(
            self.source(), "layered-handfeel-v1", 20000, 3.0, 0.01
        )
        tiers = result["optimization"]["objective"]["characters_short"]["tiers"]
        self.assertEqual(
            [x["levels"][0]["frequency"] for x in tiers],
            [-15.0, -15.0, -15.0, -70.0],
        )
        for tier in tiers[:3]:
            self.assertEqual(tier["weighted_fingering"],
                             [0.0, 100.0, 20.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.assertEqual(tiers[3]["weighted_fingering"], [0.0] * 8)

    def test_heat_profile_keeps_three_code_and_adds_only_weak_transition_weight(self):
        result = MOD.build_config(
            self.source(), "layered-handfeel-heat-v1", 20000, 3.0, 0.01
        )
        tiers = result["optimization"]["objective"]["characters_short"]["tiers"]
        self.assertEqual([x["levels"][0]["frequency"] for x in tiers],
                         [-15.0, -15.0, -15.0, -70.0])
        self.assertEqual(
            [x.get("phonetic_shape_transition_equivalence", 0.0) for x in tiers],
            [2.0, 2.0, 2.0, 0.0],
        )

    def test_heat_v2_reduces_only_heat_weight(self):
        result = MOD.build_config(
            self.source(), "layered-handfeel-heat-v2", 20000, 3.0, 0.01
        )
        tiers = result["optimization"]["objective"]["characters_short"]["tiers"]
        self.assertEqual([x["levels"][0]["frequency"] for x in tiers],
                         [-15.0, -15.0, -15.0, -70.0])
        self.assertEqual(
            [x.get("phonetic_shape_transition_equivalence", 0.0) for x in tiers],
            [0.5, 0.5, 0.5, 0.0],
        )

    def test_layered_v2_moves_toward_three_code_without_heat(self):
        result = MOD.build_config(
            self.source(), "layered-handfeel-v2", 20000, 3.0, 0.01
        )
        tiers = result["optimization"]["objective"]["characters_short"]["tiers"]
        self.assertEqual([x["levels"][0]["frequency"] for x in tiers],
                         [-15.0, -15.0, -15.0, -75.0])
        for tier in tiers[:3]:
            self.assertEqual(tier["weighted_fingering"][1:3], [80.0, 15.0])
            self.assertEqual(tier.get("phonetic_shape_transition_equivalence", 0.0), 0.0)

    def test_fullguard_profiles_change_only_top300_effective_full_duplication(self):
        for profile, expected in (
            ("layered-handfeel-v1-fullguard2", 2.0),
            ("layered-handfeel-v1-fullguard4", 4.0),
            ("layered-handfeel-v1-fullguard8", 8.0),
        ):
            with self.subTest(profile=profile):
                result = MOD.build_config(self.source(), profile, 20000, 3.0, 0.01)
                full = result["optimization"]["objective"]["characters_full"]["tiers"]
                self.assertEqual(
                    [tier["effective_duplication"] for tier in full],
                    [expected, 0.0, 0.0, 0.0],
                )
                short = result["optimization"]["objective"]["characters_short"]["tiers"]
                self.assertEqual(
                    [tier["levels"][0]["frequency"] for tier in short],
                    [-15.0, -15.0, -15.0, -70.0],
                )


if __name__ == "__main__":
    unittest.main()
