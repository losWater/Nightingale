from __future__ import annotations

import importlib.util
import shutil
import sys
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "夜莺B" / "scripts" / "audit_final_short_codes.py"
TEST_TMP = ROOT / "tests" / ".tmp"


def load_module():
    spec = importlib.util.spec_from_file_location("nightingale_short_auditor", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载：{SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FinalShortCodeAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    @staticmethod
    def config():
        return {"encoder": {"select_keys": ["_", ";"],
                            "short_code_schemes": [{"prefix": 3, "count": 2}]}}

    def rows(self, lines):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        directory = TEST_TMP / f"short-audit-{uuid.uuid4().hex}"
        directory.mkdir()
        try:
            path = directory / "code.txt"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return self.mod.load_code(path)
        finally:
            shutil.rmtree(directory)

    def test_reverse_audit_catches_unlisted_character_stealing_two_code(self):
        elements = [{"词": "甲", "简码长度": 2}, {"词": "乙"}]
        rows = self.rows(["甲\tabcd\t0\tabcd\t0", "乙\tabef\t0\tab\t0"])
        result = self.mod.audit(elements, rows, self.config())
        self.assertEqual([x["word"] for x in result["mismatches"]], ["甲", "乙"])

    def test_three_code_winner_is_independently_recomputed(self):
        elements = [{"词": "甲"}, {"词": "乙"}, {"词": "丙"}]
        rows = self.rows(["甲\tabca\t0\tabc\t0", "乙\tabcb\t0\tabc;\t0",
                          "丙\tabcc\t0\tabcc\t0"])
        result = self.mod.audit(elements, rows, self.config())
        self.assertEqual(result["expected"], ["abc", "abc", "abcc"])
        self.assertEqual(result["mismatches"], [])

    def test_natural_three_code_consumes_capacity(self):
        elements = [{"词": "自然"}, {"词": "甲"}, {"词": "乙"}]
        rows = self.rows(["自然\tabc\t0\tabc\t0", "甲\tabca\t0\tabc\t0",
                          "乙\tabcb\t0\tabcb\t0"])
        result = self.mod.audit(elements, rows, self.config())
        self.assertEqual(result["expected"], ["abc", "abc", "abcb"])

    def test_duplicate_word_and_sound_rows_are_not_overwritten(self):
        elements = [{"词": "重"}, {"词": "重"}]
        rows = self.rows(["重\tvsca\t0\tvsc\t0", "重\tvscb\t0\tvsc;\t0"])
        result = self.mod.audit(elements, rows, self.config())
        self.assertEqual(result["reverse"]["vsc"], [0, 1])
        self.assertEqual(result["mismatches"], [])

    def test_malformed_code_row_fails_loudly(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        directory = TEST_TMP / f"short-audit-bad-{uuid.uuid4().hex}"
        directory.mkdir()
        try:
            path = directory / "code.txt"
            path.write_text("甲\tabcd\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "不足5列"):
                self.mod.load_code(path)
        finally:
            shutil.rmtree(directory)

    def test_compat_form_short_code_schemes_are_supported(self):
        config = {"encoder": {"select_keys": ["_", ";"]},
                  "form": {"short_code_schemes": [{"prefix": 3, "count": 2}]}}
        self.assertEqual(self.mod.short_schemes(config)[0][:2], (3, 2))

    def test_conflicting_scheme_locations_fail_loudly(self):
        config = {"encoder": {"select_keys": ["_", ";"],
                              "short_code_schemes": [{"prefix": 3}]},
                  "form": {"short_code_schemes": [{"prefix": 2}]}}
        with self.assertRaisesRegex(ValueError, "冲突"):
            self.mod.short_schemes(config)

    def test_structured_short_code_rule_is_supported(self):
        config = {"encoder": {"select_keys": ["_", ";"], "short_code": [
            {"length_equal": 1, "schemes": [{"prefix": 3, "count": 2}]},
            {"length_equal": 2, "schemes": [{"prefix": 2}]},
        ]}}
        self.assertEqual(self.mod.short_schemes(config)[0][:2], (3, 2))

    def test_frequency_order_not_output_order_decides_three_code(self):
        elements = [{"词": "低", "频率": 1}, {"词": "高", "频率": 10}]
        rows = self.rows(["低\tabca\t0\tabca\t0", "高\tabcb\t0\tabc\t0"])
        result = self.mod.audit(elements, rows, {"encoder": {
            "select_keys": ["_"], "short_code_schemes": [{"prefix": 3}]
        }})
        self.assertEqual(result["expected"], ["abca", "abc"])
        self.assertEqual(result["mismatches"], [])

    def test_explicit_sort_order_overrides_frequency(self):
        elements = [{"词": "低", "频率": 1, "排序序号": 0},
                    {"词": "高", "频率": 10, "排序序号": 1}]
        rows = self.rows(["低\tabca\t0\tabc\t0", "高\tabcb\t0\tabcb\t0"])
        result = self.mod.audit(elements, rows, {"encoder": {
            "select_keys": ["_"], "short_code_schemes": [{"prefix": 3}]
        }})
        self.assertEqual(result["expected"], ["abc", "abcb"])


if __name__ == "__main__":
    unittest.main()
