import copy
import importlib.util
from pathlib import Path
import re
import sys
import unittest

SCRIPT = Path(__file__).parents[1] / "夜莺B" / "scripts" / "report_v08_full_metrics.py"
SPEC = importlib.util.spec_from_file_location("report_v08_full_metrics", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def valid_metric():
    tier_full = lambda top: {
        "top": top, "duplication": 0, "duplication_squared": 0,
        "effective_duplication": 0, "effective_duplication_squared": 0,
        "levels": None, "fingering": None,
        "weighted_fingering": [0.0] * 8 if top != 6000 else None,
        "phonetic_shape_transition_equivalence": 1.0 if top != 6000 else None,
    }
    tier_short = lambda top: {
        "top": top, "duplication": 0, "duplication_squared": 0,
        "effective_duplication": None, "effective_duplication_squared": None,
        "levels": [{"length": 3, "frequency": top // 2}], "fingering": None,
        "weighted_fingering": [0.0] * 8 if top != 6000 else None,
        "phonetic_shape_transition_equivalence": 1.0 if top != 6000 else None,
    }
    group = {"duplication": 0.0, "effective_duplication": 0.0,
             "key_distribution": None, "key_distribution_loss": None,
             "pair_equivalence": 1.0, "phonetic_shape_transition_equivalence": 1.0,
             "extended_pair_equivalence": None, "fingering": [0.0] * 8, "levels": None}
    full, short = copy.deepcopy(group), copy.deepcopy(group)
    full["tiers"] = [tier_full(top) for top in MODULE.TIER_TOPS]
    short["tiers"] = [tier_short(top) for top in MODULE.TIER_TOPS]
    short["effective_duplication"] = None
    short["levels"] = [{"length": 3, "frequency": 0.5}]
    return {"schema_version": 1, "score": 0.0,
            "metric": {"characters_full": full, "characters_short": short,
                       "words_full": None, "words_short": None,
                       "character_word_collision": None, "auxiliary_two_char": None,
                       "complexity": 0.1}}


class FullMetricContractTests(unittest.TestCase):
    def test_complete_contract_accepts_expected_na_fields(self):
        MODULE.validate_metric(valid_metric())

    def test_contract_fails_loudly_on_incomplete_metrics(self):
        cases = [
            (lambda x: x.update(schema_version=2), "不支持"),
            (lambda x: x["metric"]["characters_short"].update(duplication=None), "为null"),
            (lambda x: x["metric"]["characters_full"]["tiers"].pop(), "必须且只能"),
            (lambda x: x["metric"]["characters_short"]["tiers"][0].update(weighted_fingering=None), "为null"),
        ]
        for mutation, message in cases:
            with self.subTest(message=message):
                data = valid_metric()
                mutation(data)
                with self.assertRaisesRegex(ValueError, re.escape(message)):
                    MODULE.validate_metric(data)


if __name__ == "__main__":
    unittest.main()
