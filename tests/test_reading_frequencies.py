from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "夜莺B" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from reading_frequencies import (  # noqa: E402
    aggregate_syllable_frequencies,
    assert_reading_order,
    normalize_reading_order,
    primary_readings,
    load_readings,
)
from apply_reading_aliases import apply_rules  # noqa: E402


class ReadingFrequencyTests(unittest.TestCase):
    def test_same_character_and_syllable_are_summed(self):
        readings = {"教": [[1_200_000, "jntk"], [300_000, "jnzk"]]}
        self.assertEqual(aggregate_syllable_frequencies(readings)[("教", "jn")], 1_500_000)

    def test_different_syllables_stay_separate(self):
        readings = {"传": [[900_000, "irsq"], [40_000, "vrsq"]]}
        result = aggregate_syllable_frequencies(readings)
        self.assertEqual(result[("传", "ir")], 900_000)
        self.assertEqual(result[("传", "vr")], 40_000)

    def test_row_order_cannot_change_result(self):
        forward = {"好": [[80, "hctk"], [20, "hczk"]]}
        reverse = {"好": list(reversed(forward["好"]))}
        self.assertEqual(
            aggregate_syllable_frequencies(forward),
            aggregate_syllable_frequencies(reverse),
        )

    def test_malformed_frequency_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "非负整数"):
            aggregate_syllable_frequencies({"好": [["80", "hctk"]]})

    def test_short_code_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "至少含两个字符"):
            aggregate_syllable_frequencies({"好": [[80, "h"]]})

    def test_normalization_makes_highest_frequency_primary(self):
        normalized = normalize_reading_order({"嗯": [[0, "ngar"], [157_982, "enar"]]})
        frequency, code = primary_readings(normalized)
        self.assertEqual((frequency["嗯"], code["嗯"]), (157_982, "enar"))

    def test_unsorted_asset_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "未按频率降序"):
            assert_reading_order({"嗯": [[0, "ngar"], [157_982, "enar"]]})

    def test_alias_rebuild_is_pure_and_sorted(self):
        source = {"嗯": [[0, "ngar"]]}
        rules = {"reading_aliases": {"嗯": [{"code": "en", "frequency": 157_982}]}}
        result = apply_rules(source, rules)
        self.assertEqual(source, {"嗯": [[0, "ngar"]]})
        self.assertEqual(result["嗯"], [[157_982, "enar"], [0, "ngar"]])

    def test_ambiguous_suffix_requires_explicit_rule(self):
        source = {"了": [[100, "leoq"], [10, "leoo"]]}
        rules = {"reading_aliases": {"了": [{"code": "ln", "frequency": 1}]}}
        with self.assertRaisesRegex(ValueError, "必须显式指定suffix"):
            apply_rules(source, rules)


if __name__ == "__main__":
    unittest.main()
