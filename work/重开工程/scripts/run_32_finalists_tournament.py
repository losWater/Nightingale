#!/usr/bin/env python3
"""可恢复地运行15个新卡池，连同旧C11/C07形成32强并完成终局稳定性赛码。"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


TZ = timezone(timedelta(hours=10))
CARDS = list(range(1, 17))


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="minutes")


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def run(command: list[str], cwd: Path, log: Path) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"\n[{now()}] RUN {json.dumps(command, ensure_ascii=False)}\n")
        stream.flush()
        result = subprocess.run(command, cwd=cwd, text=True, encoding="utf-8", errors="replace",
                                stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"命令失败({result.returncode})，见{log}: {command}")


def manifest_complete(suite: Path) -> bool:
    path = suite / "manifest.json"
    if not path.is_file():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("status") == "complete" and len(data.get("cards", [])) == 16 and all(
        item.get("status") == "complete" and item.get("output_directory")
        and (Path(item["output_directory"]) / "code.txt").is_file()
        and (Path(item["output_directory"]) / "metric.json").is_file()
        for item in data["cards"]
    )


def metrics(suite: Path, group: int, scripts: Path, elements: Path, log: Path) -> None:
    manifest = json.loads((suite / "manifest.json").read_text(encoding="utf-8"))
    if not (suite / "finalization_report.md").is_file():
        run([sys.executable, str(scripts / "finalize_card_suite.py"), "--suite", str(suite)], scripts.parent, log)
    if not (suite / "core_metrics.json").is_file():
        command = [sys.executable, str(scripts / "report_smoke_core_metrics.py"), "--elements", str(elements)]
        for item in manifest["cards"]:
            command += ["--run", f"G{group}C{int(item['card']):02d}={item['output_directory']}"]
        command += ["--output-json", str(suite / "core_metrics.json"),
                    "--output-md", str(suite / "core_metrics.md")]
        run(command, scripts.parent, log)
    if not (suite / "postdraw_extras.json").is_file():
        command = [sys.executable, str(scripts / "report_postdraw_handfeel_extras.py"), "--elements", str(elements)]
        for item in manifest["cards"]:
            command += ["--candidate", f"G{group}C{int(item['card']):02d}={Path(item['output_directory']) / 'code.txt'}"]
        command += ["--output-json", str(suite / "postdraw_extras.json"),
                    "--output-md", str(suite / "postdraw_extras.md")]
        run(command, scripts.parent, log)
    if not (suite / "pareto.json").is_file():
        run([sys.executable, str(scripts / "select_pareto_candidates.py"),
             "--metrics", str(suite / "core_metrics.json"), "--elements", str(elements),
             "--output-json", str(suite / "pareto.json"), "--output-md", str(suite / "pareto.md")],
            scripts.parent, log)


def tables(suite: Path, scripts: Path, elements: Path, log: Path) -> Path:
    output = suite / "test_tables_all16"
    flat = output / "普通单字码表集合"
    if len(list(flat.glob("*.txt"))) != 16:
        if output.exists():
            quarantined = suite / f"test_tables_不完整_{datetime.now(TZ).strftime('%Y%m%d_%H%M%S')}"
            output.replace(quarantined)
        run([sys.executable, str(scripts / "build_candidate_single_char_tables.py"),
             "--suite", str(suite), "--elements", str(elements), "--output", str(output),
             "--cards", *map(str, CARDS), "--jobs", "16"], scripts.parent, log)
    if len(list(flat.glob("*.txt"))) != 16:
        raise RuntimeError(f"{suite}: 普通单字表不是16份")
    return flat


def stability(flat: Path, output: Path, bundle: Path, written: Path, dialogue: Path,
              schema_box: Path, log: Path) -> None:
    if (output / "stability_raw.json").is_file():
        return
    if output.exists():
        output.replace(output.with_name(output.name + f"_不完整_{datetime.now(TZ).strftime('%Y%m%d_%H%M%S')}"))
    run(["node", str(bundle), "--candidate-dir", str(flat), "--written", str(written),
         "--dialogue", str(dialogue), "--output-dir", str(output), "--block-han", "5000",
         "--bootstrap", "2000"], schema_box, log)


def select_two(suite: Path, group: int) -> list[dict]:
    core = json.loads((suite / "core_metrics.json").read_text(encoding="utf-8"))
    stable = json.loads((suite / "分段稳定性" / "stability_raw.json").read_text(encoding="utf-8"))
    balanced = stable["profileScores"]["均衡"]
    eligible = []
    for card in CARDS:
        short = f"C{card:02d}"
        metric = core[f"G{group}C{card:02d}"]
        if int(metric["layers"]["300"]["effective_full_duplication"]) == 0:
            eligible.append((short, float(balanced[short]), metric))
    eligible.sort(key=lambda item: (-item[1], item[0]))
    if len(eligible) < 2:
        raise RuntimeError(f"第{group}轮硬门禁后不足2卡")
    manifest = json.loads((suite / "manifest.json").read_text(encoding="utf-8"))
    by_card = {int(x["card"]): x for x in manifest["cards"]}
    winners = []
    for short, score, metric in eligible[:2]:
        card = int(short[1:])
        item = by_card[card]
        winners.append({"group": group, "card": card, "seed": int(item["seed"]),
                        "source_name": short, "stability_score": score,
                        "output_directory": item["output_directory"],
                        "table": str(next((suite / "test_tables_all16" / "普通单字码表集合").glob(f"{short}_*.txt"))),
                        "front6000_three_code": int(metric["layers"]["6000"]["three_code_count"]),
                        "front1500_effective_full_duplication": int(metric["front1500_effective_full_duplication"]),
                        "short_pair_equivalence": float(metric["short_pair_equivalence"]),
                        "full_duplication": float(metric["full_duplication"]),
                        "short_duplication": float(metric["short_duplication"])})
    report = {"schema_version": 1, "generated_at": now(), "eligible": len(eligible),
              "winners": winners, "balanced_ranking": [{"candidate": x[0], "score": x[1]} for x in eligible]}
    save(suite / "组内出线.json", report)
    lines = [f"# 新增第{group}轮出线", "", f"- 合资格：{len(eligible)}。", "",
             "|名次|卡|seed|稳定性|前6000三码|前1500有效重|简码当量|", "|---:|---|---:|---:|---:|---:|---:|"]
    for rank, item in enumerate(winners, 1):
        lines.append(f"|{rank}|{item['source_name']}|{item['seed']}|{item['stability_score']:.3f}|{item['front6000_three_code']}|{item['front1500_effective_full_duplication']}|{item['short_pair_equivalence']:.6f}|")
    (suite / "组内出线.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return winners


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--master", type=Path, required=True)
    parser.add_argument("--elements", type=Path, required=True)
    parser.add_argument("--chai", type=Path, required=True)
    parser.add_argument("--distribution", type=Path, required=True)
    parser.add_argument("--equivalence", type=Path, required=True)
    parser.add_argument("--schema-box", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--written", type=Path, required=True)
    parser.add_argument("--dialogue", type=Path, required=True)
    parser.add_argument("--old-suite", type=Path, required=True)
    args = parser.parse_args()
    for name in ("root", "master", "elements", "chai", "distribution", "equivalence",
                 "schema_box", "bundle", "written", "dialogue", "old_suite"):
        setattr(args, name, getattr(args, name).resolve())
    scripts = Path(__file__).resolve().parent
    args.root.mkdir(parents=True, exist_ok=True)
    state_path, log = args.root / "无人值守状态.json", args.root / "无人值守总日志.txt"
    state = {"schema_version": 1, "status": "running", "updated_at": now(), "completed_groups": [], "winners": []}
    save(state_path, state)
    all_winners = []
    for group in range(1, 16):
        seed = 820001 + group * 10000
        suite = args.root / f"组{group}_seed{seed}"
        if not (suite / "manifest.json").is_file():
            run([sys.executable, str(scripts / "build_random_card_suite.py"), "--master", str(args.master),
                 "--elements", str(args.elements), "--output-dir", str(suite), "--count", "16",
                 "--seed-start", str(seed)], scripts.parent, log)
        if not manifest_complete(suite):
            run([sys.executable, str(scripts / "run_card_suite.py"), "--suite", str(suite),
                 "--chai", str(args.chai), "--elements", str(args.elements),
                 "--distribution", str(args.distribution), "--equivalence", str(args.equivalence),
                 "--jobs", "16"], scripts.parent, log)
        if not manifest_complete(suite):
            raise RuntimeError(f"第{group}轮退火未完整")
        metrics(suite, group, scripts, args.elements, log)
        flat = tables(suite, scripts, args.elements, log)
        stability(flat, suite / "分段稳定性", args.bundle, args.written, args.dialogue, args.schema_box, log)
        winners = select_two(suite, group)
        all_winners.extend(winners)
        state.update(updated_at=now(), completed_groups=list(range(1, group + 1)), winners=all_winners)
        save(state_path, state)

    final = args.root / "最终32强"
    flat = final / "普通单字码表集合"
    flat.mkdir(parents=True, exist_ok=True)
    identities = []
    old_manifest = json.loads((args.old_suite / "cards" / "manifest.json").read_text(encoding="utf-8"))
    old_by_card = {int(x["card"]): x for x in old_manifest["cards"]}
    old_tables = args.old_suite / "test_batch_0058" / "普通单字码表集合"
    sources = [
        {"kind": "旧擂主", "source": "0054-C11", "seed": 820011, "table": str(next(old_tables.glob("C11_*.txt"))), "output_directory": old_by_card[11]["output_directory"]},
        {"kind": "旧擂主", "source": "0054-C07", "seed": 820007, "table": str(next(old_tables.glob("C07_*.txt"))), "output_directory": old_by_card[7]["output_directory"]},
        *[{"kind": "新增出线", "source": f"G{x['group']}-{x['source_name']}", **x} for x in all_winners],
    ]
    if len(sources) != 32:
        raise RuntimeError(f"终局来源应为32，实际{len(sources)}")
    for index, item in enumerate(sources, 1):
        final_name = f"C{index:02d}"
        target = flat / f"{final_name}_{item['source']}_seed_{item['seed']}_纯单字试用表.txt"
        shutil.copyfile(item["table"], target)
        identities.append({"final": final_name, **item, "final_table": str(target)})
    save(final / "身份映射.json", {"schema_version": 1, "generated_at": now(), "candidates": identities})
    stability(flat, final / "分段稳定性", args.bundle, args.written, args.dialogue, args.schema_box, log)
    stable = json.loads((final / "分段稳定性" / "stability_raw.json").read_text(encoding="utf-8"))
    balanced = stable["profileScores"]["均衡"]
    ranking = sorted(balanced.items(), key=lambda x: (-float(x[1]), x[0]))
    by_final = {x["final"]: x for x in identities}
    result = [{"rank": rank, "final": name, "score": score, "source": by_final[name]["source"],
               "seed": by_final[name]["seed"]} for rank, (name, score) in enumerate(ranking, 1)]
    save(final / "最终排名.json", {"schema_version": 1, "generated_at": now(), "ranking": result})
    lines = ["# 夜莺0.8三十二强终局稳定性排名", "", "|名次|终局编号|来源|seed|均衡得分|", "|---:|---|---|---:|---:|"]
    lines += [f"|{x['rank']}|{x['final']}|{x['source']}|{x['seed']}|{x['score']:.3f}|" for x in result]
    (final / "最终排名.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    state.update(status="complete", updated_at=now(), final_ranking=result)
    save(state_path, state)


if __name__ == "__main__":
    main()
