from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "work" / "夜莺0.85" / "scripts" / "build_v085_bingling_table.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_v085_bingling_table", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BinglingTableTests(unittest.TestCase):
    def test_order_frequency_and_rare_band(self):
        mod = load_module()
        rows, skipped = mod.build(
            [("甲", "bb"), ("首", "aa"), ("次", "aa"), ("僻", "aa"), ("$ddcmd(x)", "aa")],
            {"僻"},
            [("aa", 2, "！")],
        )
        self.assertEqual(skipped, 1)
        self.assertEqual(rows, [
            ("aa", "首", 9999),
            ("aa", "！", 9998),
            ("aa", "次", 9997),
            ("aa", "僻", 11),
            ("bb", "甲", 9999),
        ])

    def test_render_is_crlf_with_header_and_rules(self):
        mod = load_module()
        text = mod.render([("aa", "首", 9999)], "260902")
        self.assertIn("Version=0.9.1|260902\r\n", text)
        self.assertIn("PhraseRule=3\r\npa2=w11w12w21w22\r\npa3=w11w21w31\r\npe4=w11w21w31r11\r\n[CODETABLE]\r\n", text)
        self.assertTrue(text.endswith("aa\t首\t9999\r\n"))
        self.assertNotIn("\n", text.replace("\r\n", ""))


if __name__ == "__main__":
    unittest.main()
