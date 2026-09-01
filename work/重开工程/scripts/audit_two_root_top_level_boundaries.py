# -*- coding: utf-8 -*-
"""Compare two-root results with expansions of two top-level Chai parts."""
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

import audit_manual_split_propagation as common


PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "02_规范拆分"
RUN_ROOT = PROJECT / "05_退火实验" / "二根顶层边界核验"
AUDIT_NAME_EQUIVALENTS = {
    "㇒": ["撇"],
    "㇆": ["折"],
    "竖弯钩": ["折"],
    "尔字头": ["⺈"],
}


def main() -> None:
    now = datetime.now(ZoneInfo("Australia/Sydney"))
    run_dir = RUN_ROOT / now.strftime("%Y%m%d_%H%M%S%z")
    run_dir.mkdir(parents=True, exist_ok=False)
    roots = yaml.safe_load(common.ROOTS_PATH.read_text(encoding="utf-8"))
    rules_doc = yaml.safe_load(common.RULES_PATH.read_text(encoding="utf-8"))
    baseline = yaml.safe_load(common.BASELINE_PATH.read_text(encoding="utf-8"))
    rules = rules_doc.get("component_splits") or {}
    chars, splits = common.load_table()
    by_name, labels = common.repertoire_maps(baseline)
    hosts = common.canonical_host_map(roots)
    registered_chars = set()
    visible: dict[str, str] = {}
    for root, attached in roots["roots"].items():
        rr = common.resolve(root, by_name); registered_chars.add(rr); visible[rr] = str(root)
        for item in attached or []:
            ri = common.resolve(item, by_name); registered_chars.add(ri); visible[ri] = str(item)
    for anchored in (roots.get("anchors") or {}).values():
        for item in anchored or []:
            ri = common.resolve(item, by_name); registered_chars.add(ri); visible[ri] = str(item)

    cfg = common.compile_config(baseline, roots, rules, by_name)
    cfg_path, charset_path, result_path = run_dir / "config.yaml", run_dir / "charset.txt", run_dir / "result.json"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    charset_path.write_text("\n".join(chars) + "\n", encoding="utf-8")
    cp = subprocess.run(["bun", str(common.RUNNER_PATH), str(cfg_path), str(charset_path), str(result_path)], cwd=common.ROOT, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (run_dir / "stderr.txt").write_text(cp.stderr, encoding="utf-8")
    if cp.returncode:
        raise RuntimeError(cp.stderr)
    payload = json.loads(result_path.read_text(encoding="utf-8"))

    def expand(raw_part: str) -> tuple[list[str] | None, str]:
        display = visible.get(raw_part, labels.get(raw_part, raw_part))
        if display in AUDIT_NAME_EQUIVALENTS:
            return AUDIT_NAME_EQUIVALENTS[display], display
        if raw_part in registered_chars:
            return [display], display
        if raw_part in splits:
            return splits[raw_part], display
        return None, display

    rows = []
    counts = {"aligned": 0, "mismatch": 0, "unresolved": 0}
    for char in chars:
        if len(splits[char]) != 2 or char in registered_chars:
            continue
        top = payload.get("top_level", {}).get(char) or {}
        parts = top.get("parts") or []
        if top.get("type") != "compound" or len(parts) != 2:
            continue
        left, left_name = expand(parts[0])
        right, right_name = expand(parts[1])
        expected = None if left is None or right is None else left + right
        if expected is None:
            state = "unresolved"
        elif [hosts.get(x, x) for x in expected] == [hosts.get(x, x) for x in splits[char]]:
            state = "aligned"
        else:
            state = "mismatch"
        counts[state] += 1
        if state != "aligned":
            rows.append({
                "汉字": char, "顶层结构": str(top.get("operator", "")),
                "顶层第一部分": left_name, "顶层第二部分": right_name,
                "两部分展开": " ＋ ".join(expected or []),
                "整字最终拆分": " ＋ ".join(splits[char]),
                "状态": state,
            })

    fields = ["汉字", "顶层结构", "顶层第一部分", "顶层第二部分", "两部分展开", "整字最终拆分", "状态"]
    with (OUT / "二根顶层边界核验.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    result = {
        "run_time": now.isoformat(timespec="minutes"), "counts": counts,
        "checked": sum(counts.values()),
        "inputs": {str(p.relative_to(common.ROOT)): common.sha256(p) for p in [common.ROOTS_PATH, common.RULES_PATH, common.TABLE_PATH, common.BASELINE_PATH, common.RUNNER_PATH, Path(__file__)]},
        "exceptions": rows,
    }
    (OUT / "二根顶层边界核验.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# 二根顶层边界核验", "", f"- 检查数：{result['checked']}", f"- 一致：{counts['aligned']}", f"- 不一致候选：{counts['mismatch']}", f"- 无法解析：{counts['unresolved']}", "", "|字|结构|顶层部分|展开|最终拆分|状态|", "|---|---|---|---|---|---|"]
    md.extend(f"|{x['汉字']}|{x['顶层结构']}|{x['顶层第一部分']}／{x['顶层第二部分']}|{x['两部分展开'] or '—'}|{x['整字最终拆分']}|{x['状态']}|" for x in rows)
    (OUT / "二根顶层边界核验.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"checked": result["checked"], **counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
