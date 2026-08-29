from __future__ import annotations

import subprocess
import sys
import unittest
import re
import shutil
import uuid
import os
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "夜莺B" / "scripts" / "audit_cross_collision.py"
TEST_TMP = ROOT / "tests" / ".tmp"


def element(
    word: str, frequency: int, order: int | None = None, short_length: int | None = None
) -> dict:
    item = {
        "词": word,
        "元素序列": [{"element": "x", "index": 0}] * 4,
        "频率": frequency,
    }
    if order is not None:
        item["排序序号"] = order
    if short_length is not None:
        item["简码长度"] = short_length
    return item


class CrossCollisionAuditTests(unittest.TestCase):
    def run_audit(
        self,
        *,
        targets: dict,
        elements: list[dict],
        rows: list[tuple],
        global_top: int = 0,
        tiers: list[dict] | None = None,
        expect_error: str | None = None,
    ):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        base = TEST_TMP / f"case-{uuid.uuid4().hex}"
        base.mkdir()
        try:
            output = base / "output"
            output.mkdir()
            config = {
                "encoder": {
                    "max_length": 4,
                    "select_keys": ["_", ";"],
                    "auto_select_length": 4,
                },
                "optimization": {
                    "objective": {
                        "character_word_collision": {
                            "weight": 1.0,
                            "hard_penalty": 1000.0,
                            "hard_character_top": global_top,
                            "character_tiers": tiers or [{"top": 10, "factor": 1.0}],
                            "targets": targets,
                        }
                    }
                },
            }
            (output / "config.yaml").write_text(
                yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )
            (output / "code.txt").write_text(
                "\n".join("\t".join(map(str, row)) for row in rows) + "\n", encoding="utf-8"
            )
            elements_path = base / "elements.yaml"
            elements_path.write_text(
                yaml.safe_dump(elements, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(output), "--elements", str(elements_path)],
                text=True,
                encoding="utf-8",
                capture_output=True,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            if expect_error is not None:
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(expect_error, result.stderr)
                return None
            if result.returncode != 0:
                self.fail(f"audit failed:\nSTDOUT={result.stdout}\nSTDERR={result.stderr}")
            hard = re.search(r"独立硬碰撞:\s*(\d+)", result.stdout)
            soft = re.search(r"独立软碰撞:\s*([\d.]+)", result.stdout)
            if hard is None:
                self.fail(f"missing hard metric:\n{result.stdout}")
            return {"hard": int(hard.group(1)), "soft": float(soft.group(1)) if soft else None}
        finally:
            shutil.rmtree(base)

    def test_global_hard_top_is_used_when_target_has_no_override(self):
        result = self.run_audit(
            global_top=1,
            targets={"abcd": {"soft": 1.0, "hard": True}},
            elements=[element("甲", 100)],
            rows=[("甲", "abcd", 0, "abcd", 0)],
        )
        self.assertEqual(result["hard"], 1)

    def test_explicit_target_top_applies_even_when_hard_flag_is_false(self):
        result = self.run_audit(
            global_top=0,
            targets={"abcd": {"soft": 1.0, "hard": False, "hard_character_top": 1}},
            elements=[element("甲", 100)],
            rows=[("甲", "abcd", 0, "abcd", 0)],
        )
        self.assertEqual(result["hard"], 1)

    def test_explicit_sort_order_matches_libchai(self):
        result = self.run_audit(
            targets={"abcd": {"soft": 1.0, "hard": True, "hard_character_top": 1}},
            elements=[element("甲", 1000, 1), element("乙", 1, 0)],
            rows=[("甲", "abcd", 0, "abcd", 0), ("乙", "wxyz", 0, "wxyz", 0)],
        )
        self.assertEqual(result["hard"], 0)

    def test_real_short_code_exempts_the_full_code_slot(self):
        result = self.run_audit(
            targets={"abcd": {"soft": 1.0, "hard": True, "hard_character_top": 1}},
            elements=[element("甲", 100)],
            rows=[("甲", "abcd", 0, "abc", 0)],
        )
        self.assertEqual(result["hard"], 0)

    def test_no_short_fallback_ignores_recorded_short_rank(self):
        result = self.run_audit(
            targets={"abcd": {"soft": 1.0, "hard": True, "hard_character_top": 1}},
            elements=[element("甲", 100)],
            rows=[("甲", "abcd", 0, "abcd", 1)],
        )
        self.assertEqual(result["hard"], 1)

    def test_explicit_four_key_secondary_short_candidate_is_exempt(self):
        result = self.run_audit(
            targets={"abcd": {"soft": 1.0, "hard": True, "hard_character_top": 1}},
            elements=[element("甲", 100, short_length=4)],
            rows=[("甲", "abcd", 0, "abcd", 1)],
        )
        self.assertEqual(result["hard"], 0)

    def test_partial_explicit_order_is_rejected(self):
        self.run_audit(
            targets={},
            elements=[element("甲", 100, 0), element("乙", 90)],
            rows=[("甲", "abcd", 0, "abc", 0), ("乙", "efgh", 0, "efg", 0)],
            expect_error="启用排序序号后必须全量标注",
        )

    def test_character_after_word_is_rejected(self):
        self.run_audit(
            targets={},
            elements=[element("甲乙", 100), element("甲", 90)],
            rows=[("甲乙", "abcd", 0, "abc", 0), ("甲", "efgh", 0, "efg", 0)],
            expect_error="单字必须连续位于所有多字词之前",
        )

    def test_malformed_code_row_is_rejected(self):
        self.run_audit(
            targets={},
            elements=[element("甲", 100)],
            rows=[("甲", "abcd", 0, "abc")],
            expect_error="应有5列",
        )

    def test_unsorted_character_tiers_are_rejected(self):
        self.run_audit(
            targets={},
            elements=[element("甲", 100)],
            rows=[("甲", "abcd", 0, "abc", 0)],
            tiers=[{"top": 10, "factor": 1.0}, {"top": 5, "factor": 0.5}],
            expect_error="必须按top严格升序",
        )


if __name__ == "__main__":
    unittest.main()
