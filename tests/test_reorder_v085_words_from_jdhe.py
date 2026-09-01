from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "work" / "夜莺0.85" / "scripts" / "reorder_v085_words_from_jdhe.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reorder_v085_words_from_jdhe", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载：{SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


class WordCodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_word_code_rules(self):
        self.assertEqual(self.mod.word_code(["wj", "gg"]), "wjgg")
        self.assertEqual(self.mod.word_code(["qk", "bu", "zi"]), "qbzi")
        self.assertEqual(self.mod.word_code(["ww", "ji", "gs", "gr"]), "wjgg")
        self.assertEqual(self.mod.word_code(["yz", "yi", "uo", "yi", "yi"]), "yyuy")


class ReorderPipelineTests(unittest.TestCase):
    """用最小夹具覆盖：单字守位、裁决词守位、简词随简单鹤/守位、飞键重编、夜莺独有词垫后、短码不动。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        # 综合主表：uixy 试训(词)/莳(字)/实训(词)/蒔(扩展字)；wjgg 危机公关(四码简词)；
        # xujq 绪(字)/许久(裁决词)/酗酒/叙旧；xoqi 秀气(夜莺码 xqqi 的词在简单鹤是飞键 xoqi)；
        # wsm 为什么(三码简词，不得动)；gwni 给你(夜莺独有)。
        cls.combined = write(d / "combined.txt", "\n".join([
            "试训\tuixy", "莳\tuixy", "实训\tuixy", "蒔\tuixy",
            "危机公关\twjgg",
            "绪\txujq", "许久\txujq", "酗酒\txujq", "叙旧\txujq",
            "秀气\txqqi",
            "为什么\twsm",
            "给你\tgwni",
            "重新\tisxb", "宠信\tisxb",
        ]) + "\n")
        cls.single = write(d / "single.txt", "\n".join([
            "莳\tuixy", "蒔\tuixy", "绪\txujq", "试\tuide", "训\txyda", "实\tuiin", "十\tuioo", "循\txyao",
            "玩\twjga", "梗\tggon", "秀\txqwv", "气\tqirr", "修\txqfe", "葺\tqixe",
            "重\tvshz", "重\tishz", "新\txbaa", "给\tgwaa", "你\tniaa", "许\txudp", "久\tjqqq", "酗\txuew",
            "酒\tjqbe", "叙\txugq", "旧\tjqaq",
        ]) + "\n")
        cls.short = write(d / "short.tsv", "词\t简码\t候选位\t级别\n危机公关\twjgg\t1\t4\n为什么\twsm\t1\t3\n")
        cls.ext = write(d / "ext.tsv", "字\t码\t候选位\n蒔\tuixy\t4\n")
        cls.jdhe = write(d / "jdhe.txt", "\n".join([
            "实训\tuixy", "试训\tuixy", "十循\tuixy",
            "玩梗\twjgg", "危机公关\twjgg",
            "许久\txujq", "叙旧\txujq", "酗酒\txujq",
            "秀气\txoqi", "修葺\txoqi",
            "重新\tvsxb",
            "一场\tei",
        ]) + "\n")
        cls.decisions = write(d / "decisions.tsv",
                              "裁决编号\t码\t调整前关键候选\t调整后关键候选\t理由\t状态\nW1\txujq\t绪、许久\t绪、许久\t略\t维持\n")
        cls.fixes = write(d / "fixes.tsv", "词\t当前码\t建议码\n重新\tvsxb\tisxb\n")
        cls.out_combined = d / "out_combined.txt"
        cls.out_short = d / "out_short.tsv"
        cls.summary = d / "summary.json"
        subprocess.run([
            sys.executable, str(SCRIPT),
            "--combined", str(cls.combined), "--single", str(cls.single),
            "--short-words", str(cls.short), "--extension-characters", str(cls.ext),
            "--jdhe-words", str(cls.jdhe), "--word-decisions", str(cls.decisions),
            "--word-code-fixes", str(cls.fixes),
            "--output-combined", str(cls.out_combined), "--output-short-words", str(cls.out_short),
            "--summary", str(cls.summary),
        ], check=True, capture_output=True)
        cls.rows = [line.split("\t") for line in cls.out_combined.read_text(encoding="utf-8").splitlines()]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def bucket(self, code: str) -> list[str]:
        return [text for text, c in self.rows if c == code]

    def test_characters_keep_positions_and_words_follow_jdhe(self):
        self.assertEqual(self.bucket("uixy"), ["实训", "莳", "试训", "蒔", "十循"])

    def test_short_word_follows_jdhe_when_present(self):
        self.assertEqual(self.bucket("wjgg"), ["玩梗", "危机公关"])
        short = self.out_short.read_text(encoding="utf-8").splitlines()
        self.assertIn("危机公关\twjgg\t2\t4", short)
        self.assertIn("为什么\twsm\t1\t3", short)

    def test_decision_words_are_anchored(self):
        self.assertEqual(self.bucket("xujq"), ["绪", "许久", "叙旧", "酗酒"])

    def test_fly_key_words_are_recoded_to_nightingale(self):
        self.assertEqual(self.bucket("xqqi"), ["秀气", "修葺"])
        self.assertEqual(self.bucket("xoqi"), [])

    def test_word_code_fixes_and_existing_codes_win_over_jdhe_codes(self):
        self.assertEqual(self.bucket("isxb"), ["重新", "宠信"])
        self.assertEqual(self.bucket("vsxb"), [])

    def test_short_codes_and_nightingale_only_words_are_untouched(self):
        self.assertEqual(self.bucket("wsm"), ["为什么"])
        self.assertEqual(self.bucket("gwni"), ["给你"])
        self.assertEqual(self.bucket("ei"), [])

    def test_summary_counts(self):
        summary = json.loads(self.summary.read_text(encoding="utf-8"))
        self.assertEqual(summary["combined_rows_before"], 14)
        self.assertEqual(summary["combined_rows_after"], 17)
        self.assertEqual(summary["jdhe"]["jdhe_recoded"], 3)   # 秀气、修葺、重新


if __name__ == "__main__":
    unittest.main()
