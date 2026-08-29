# -*- coding: utf-8 -*-
"""用 v0.4 的读音/频率骨架和夜莺 B 的新拆分生成 chai 冒烟元素表。"""
from pathlib import Path
from copy import deepcopy
from collections import defaultdict
import csv
import yaml
from b_roots import head, tail, resolve

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
WORK = BASE / "work"
STROKE_ELEMENTS = {"横": "1", "竖": "2", "撇": "3", "点": "4", "捺": "4", "折": "5"}
PINKY_KEYS = set("qazp")
PINKY_STRENGTH = 2.5
# 五笔画固定在 H/U/P/D/V 后不可由布局消除的字词碰撞：
# 万 wjhv ↔ 晚会/挽回；川 iruu ↔ 传输/传书。
# 它们作为固定结构基线另行审计，不进入可调硬碰撞罚分。
FIXED_HARD_COLLISION_CODES = {"wjhv", "iruu", "yuhh"}

def splits():
    out = {}
    for line in (WORK / "analysis.tsv.splits.tsv").read_text(encoding="utf-8").splitlines():
        char, sep, raw = line.partition("\t")
        if sep and len(char) == 1 and raw.strip(): out[char] = raw.split()
    return out

def blocks(path):
    block = []
    for line in path.open(encoding="utf-8"):
        if line.startswith("- 词: ") and block:
            yield "".join(block); block = []
        block.append(line)
    if block: yield "".join(block)

def word_tier(rank):
    if rank <= 2000: return 1.0
    if rank <= 10000: return 0.5
    if rank <= 30000: return 0.2
    return 0.05

def collision_targets():
    path = WORK / "lexicon" / "目标词库_四码位.tsv"
    targets = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            soft = 0.0
            two_rank = int(row["two_top_rank"]) if row["two_top_rank"] else None
            four_rank = int(row["four_top_rank"]) if row["four_top_rank"] else None
            if two_rank is not None: soft += word_tier(two_rank)
            if four_rank is not None: soft += word_tier(four_rank) * 0.25
            targets[row["code"]] = {
                "soft": soft,
                "hard": (two_rank is not None and two_rank <= 10000
                         and row["code"] not in FIXED_HARD_COLLISION_CODES),
                # 分层硬保护：前 2000 二字词避让前 3500 字；其余前 10000
                # 二字词只避让前 1500 字。固定结构基线不进入硬罚分。
                "hard_character_top": (
                    0 if row["code"] in FIXED_HARD_COLLISION_CODES or two_rank is None
                    else 3500 if two_rank <= 2000
                    else 1500 if two_rank <= 10000
                    else 0
                ),
            }
    return targets

def main():
    seqs = splits(); items = []
    rules = yaml.safe_load((WORK / "拆分规则.yaml").read_text(encoding="utf-8"))
    aliases = rules.get("reading_aliases", {})
    frequency_overrides = rules.get("reading_frequency_overrides", {})
    templates = {}
    emitted_sounds = set()
    old = ROOT / "work" / "optimize" / "elements_v04.yaml"
    for block in blocks(old):
        word = block.splitlines()[0][4:].strip() if block else ""
        if len(word) != 1 or word not in seqs: continue
        item = yaml.safe_load(block)[0]
        sound = item["元素序列"][:2]
        sound_names = tuple(x["element"] for x in sound)
        alias = next((x for x in aliases.get(word, [])
                      if tuple(str(y) for y in x.get("sound", [])) == sound_names), None)
        if alias:
            code = str(alias["code"])
            emitted_sounds.add((word, code))
            if alias.get("anneal", True) is False:
                continue
            item["频率"] = int(frequency_overrides.get(word, {}).get(code,
                                                                    alias.get("frequency", item["频率"])))
        # elements 文件承载最终 abxy；首末部件还须递归到当前根集。
        logical = [head(word)[0], tail(word)[0]]
        shape = [STROKE_ELEMENTS.get(x, resolve(x)) for x in logical]
        item["元素序列"] = sound + [{"element": x, "index": 0} for x in shape]
        items.append(item)
        templates.setdefault(word, item)
    for word, entries in aliases.items():
        if word not in templates:
            raise KeyError(f"读音别名缺少元素模板: {word}")
        for alias in entries:
            code = str(alias["code"])
            if (word, code) in emitted_sounds:
                continue
            if alias.get("anneal", True) is False:
                continue
            item = deepcopy(templates[word])
            sound = alias.get("sound")
            if not sound or len(sound) != 2:
                raise ValueError(f"读音别名必须登记两个声韵元素: {word}")
            item["元素序列"][:2] = [{"element": str(x), "index": 0} for x in sound]
            item["频率"] = int(alias.get("frequency", 0))
            items.append(item)

    # 当前 chai.exe 要求 gb2312 为 u8；只生成兼容副本，不覆盖分析源配置。
    cfg = yaml.safe_load((WORK / "analysis_config.yaml").read_text(encoding="utf-8"))
    for row in cfg.get("data", {}).get("repertoire", {}).values():
        if isinstance(row.get("gb2312"), bool): row["gb2312"] = int(row["gb2312"])
    mapping = cfg["form"]["mapping"]

    # 人工一简优先于常规三码。同一多音字只给当前最高权重读音登记一简；
    # 其余冷读音保留全码，但不会进入常用字层的三码竞争。
    short_assets = yaml.safe_load((WORK / "简码资产.yaml").read_text(encoding="utf-8"))
    one_code = {str(word): str(key) for key, word in short_assets.get("one_code", {}).items()}
    for word, expected_key in one_code.items():
        candidates = [item for item in items if item["词"] == word]
        if not candidates:
            raise KeyError(f"一简字不在元素资产中: {word}")
        chosen = max(candidates, key=lambda item: int(item.get("频率", 0)))
        # 一简键来自全码首键；26项资产均按小鹤声母键登记。
        actual_key = mapping[str(chosen["元素序列"][0]["element"])]
        if actual_key != expected_key:
            raise ValueError(f"一简键不符: {word} 预期 {expected_key}，声码首键为 {actual_key}")
        chosen["简码长度"] = 1

    # 二简：先排除所有人工一简字，再按当前读音自身频率逐音节选最高者。
    # 若音节全为零频，使用人工覆盖；否则仍稳定选择一个，避免空置二简位。
    groups = defaultdict(list)
    for item in items:
        if item["词"] in one_code:
            continue
        sound_code = "".join(str(mapping[str(slot["element"])]) for slot in item["元素序列"][:2])
        groups[sound_code].append(item)
    two_overrides = {str(k): str(v) for k, v in rules.get("two_code_overrides", {}).items()}
    for sound_code, candidates in groups.items():
        override = two_overrides.get(sound_code)
        eligible = [item for item in candidates if item["词"] == override] if override else candidates
        if not eligible:
            raise KeyError(f"二简人工指定不在音节资产中: {sound_code}={override}")
        max(eligible, key=lambda item: int(item.get("频率", 0)))["简码长度"] = 2
    out = WORK / "analysis_elements.yaml"
    out.write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")

    encoder = cfg.get("encoder", {})
    encoder.pop("short_code_schemes", None)
    encoder["short_code"] = [{"length_equal": 1, "schemes": [{"prefix": 3}]}]
    # 构造夜莺 B 的真实退火空间：音码固定，五笔画固定，其余主根开放 26 键；
    # 附属／锚定根在 mapping 中引用宿主，不单独成为决策变量。
    form = cfg["form"]
    mapping = form["mapping"]
    contribution = {}
    total_shape_frequency = 0
    for item in items:
        frequency = int(item.get("频率", 0))
        for slot in item["元素序列"][2:4]:
            element = str(slot["element"])
            contribution[element] = contribution.get(element, 0) + frequency
            total_shape_frequency += frequency
    stroke_keys = {"1": "h", "2": "u", "3": "p", "4": "d", "5": "v"}
    mapping.update(stroke_keys)
    alphabet = form.get("alphabet", "abcdefghijklmnopqrstuvwxyz")
    mapping_space = {}
    for element, arrangement in mapping.items():
        if isinstance(arrangement, dict):
            values = [arrangement]
        elif element.startswith(("szm-", "mzm-")) or element in stroke_keys:
            values = [mapping[element]]
        else:
            values = list(alphabet)
        mapping_space[element] = [
            {"value": key,
             "score": (PINKY_STRENGTH * contribution.get(element, 0) / total_shape_frequency
                       if isinstance(key, str) and key in PINKY_KEYS and len(values) > 1 else 0.0)}
            for key in values
        ]
    form["mapping_space"] = mapping_space
    cfg["generated_mapping_space"] = mapping_space

    # 已敲定的单字目标；短测只缩短步数，不改变相对权重。
    cfg["optimization"] = {
        "objective": {
            "characters_full": {
                "duplication": 200,
                "pair_equivalence": 10,
                "tiers": [
                    {"top": 1500, "duplication": 100, "duplication_squared": 100},
                    {"top": 3500, "duplication": 50, "duplication_squared": 30},
                    {"top": 6000, "duplication": 30, "duplication_squared": 10},
                ],
            },
            "characters_short": {
                "duplication": 200,
                "pair_equivalence": 10,
                "tiers": [
                    {"top": 1500, "duplication": 100, "duplication_squared": 50,
                     "levels": [{"length": 3, "frequency": -50}]},
                    {"top": 3500, "duplication": 50, "duplication_squared": 15,
                     "levels": [{"length": 3, "frequency": -20}]},
                ],
            },
            "character_word_collision": {
                "weight": 0.05,
                "hard_penalty": 1000,
                "hard_character_top": 1500,
                "character_tiers": [
                    {"top": 1500, "factor": 1.0},
                    {"top": 3500, "factor": 0.5},
                    {"top": 5000, "factor": 0.2},
                ],
                "targets": collision_targets(),
            },
        },
        "metaheuristic": {
            "algorithm": "SimulatedAnnealing",
            "parameters": {"t_max": 0.003, "t_min": 1.0e-6, "steps": 20000},
            "report_after": 0.99,
            "update_interval": 5000,
        },
    }
    compat = WORK / "analysis_config_compat.yaml"
    compat.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    print(f"elements: {len(items)} -> {out}")
    print(f"compat config -> {compat}")

if __name__ == "__main__": main()
