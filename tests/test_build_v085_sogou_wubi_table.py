from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "work" / "夜莺0.85" / "scripts" / "build_v085_sogou_wubi_table.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_v085_sogou_wubi_table", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SogouWubiTableTests(unittest.TestCase):
    def test_extension_removed_and_quick_inserted_at_rank(self):
        mod = load_module()
        rows = mod.build(
            [("甲", "aa"), ("扩", "aa"), ("词", "aa"), ("乙", "bb")],
            {"扩"},
            [("aa", 2, "！")],
        )
        self.assertEqual(rows, [("aa", "甲"), ("aa", "！"), ("aa", "词"), ("bb", "乙")])


if __name__ == "__main__":
    unittest.main()
