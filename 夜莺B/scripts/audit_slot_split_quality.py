# -*- coding: utf-8 -*-
"""审计词位训练集质量：只标记证据，不自动删除或改写切分。"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
DOCS = BASE / "documents"
WORK = BASE / "work"
SPLITS = WORK / "slot_splits"

SURNAME = set("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯管卢莫房裘缪干解应宗丁宣邓郁单杭洪包诸左石崔吉龚程嵇邢裴陆荣翁荀羊甄曲封芮储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全班仰秋仲伊宫宁仇栾甘厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲台从鄂索咸籍赖卓蔺屠蒙池乔阴胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍郤璩桑桂濮牛寿边扈燕冀浦尚农温庄晏柴瞿阎充慕连茹习艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公")
NAME_PREFIX = ("阿", "小", "老")
PLACE_SUFFIX = tuple("省市县区镇村州郡岛河湖湾港桥路街巷沟岭山寺站")
TRANSLIT_CHARS = set("斯特尔克曼夫洛维奇科夫基姆森逊顿堡迪亚尼娅娜莉莎贝德勒")


def read_tsv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def decode(path: Path):
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise UnicodeError(path)


def plain_words(path: Path):
    return {line.strip().split("\t")[0] for line in decode(path).splitlines() if line.strip()}


def character_ranks():
    data = yaml.safe_load((WORK / "analysis_elements.yaml").read_text(encoding="utf-8"))
    # 同一个汉字会因多音资产出现多条；字频应聚合取最大值，不能让冷门读音覆盖常用读音。
    frequencies = {}
    for row in data:
        word = row.get("词", "")
        if len(word) == 1:
            frequencies[word] = max(frequencies.get(word, 0), float(row.get("频率", 0)))
    ordered = sorted(frequencies, key=lambda word: (-frequencies[word], word))
    return {word: rank for rank, word in enumerate(ordered, 1)}


def word_flags(word: str, groups: int, ranks: dict[str, int], trusted: set[str]):
    flags = []
    max_rank = max((ranks.get(char, 99999) for char in word), default=99999)
    rare_count = sum(ranks.get(char, 99999) > 5000 for char in word)
    if groups <= 3:
        flags.append("低来源")
    if rare_count:
        flags.append("含5000后字")
    # 姓氏开头本身毫无证明力（如“完全、陆上”）；只在缺少交叉来源时给弱提示。
    if len(word) == 2 and word[0] in SURNAME and groups <= 3 and word not in trusted:
        flags.append("疑似姓名")
    if word.startswith(NAME_PREFIX):
        flags.append("称谓/专名式前缀")
    if word.endswith(PLACE_SUFFIX):
        flags.append("疑似地名")
    if sum(char in TRANSLIT_CHARS for char in word) >= max(2, len(word) - 1):
        flags.append("疑似音译")
    return flags, max_rank, int(word in trusted)


def main():
    rows = read_tsv(SPLITS / "词位训练集.tsv")
    ranks = character_ranks()
    trusted = plain_words(DOCS / "多词库取交集精练词语三万.txt")
    output = []
    reason_counts = Counter()
    flagged_slots = set()
    for row in rows:
        words = row["two_words"].split()
        groups = int(row["two_groups"] or 0)
        for word in words:
            flags, max_rank, in_trusted = word_flags(word, groups, ranks, trusted)
            for flag in flags:
                reason_counts[flag] += 1
            if flags:
                flagged_slots.add(row["code"])
            output.append({
                "code": row["code"], "reason": row["reason"], "band": row["band"],
                "two_rank": row["two_rank"], "word": word, "two_groups": groups,
                "共同交集词库": in_trusted, "最冷字频序": max_rank,
                "标签数": len(flags), "审计标签": "|".join(flags),
                "处理建议": "人工复核" if flags else "保留",
            })
    output.sort(key=lambda x: (-x["标签数"], x["共同交集词库"], int(x["two_rank"] or 999999), x["word"]))
    out_path = SPLITS / "训练集质量审计.tsv"
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(output[0]), delimiter="\t")
        writer.writeheader(); writer.writerows(output)

    flagged = [x for x in output if x["标签数"]]
    unsupported = [x for x in flagged if not x["共同交集词库"]]
    report = [
        "# 训练集质量审计", "",
        "本审计只标记，不删除、不改写训练／验证／测试切分。标签是复核线索，不等于坏词。", "",
        f"- 训练码位：{len(rows):,}",
        f"- 审计二字词：{len(output):,}",
        f"- 至少一个标签：{len(flagged):,} 词，涉及 {len(flagged_slots):,} 码位",
        f"- 有标签且不在四库共同交集：{len(unsupported):,} 词",
        f"- 四库共同交集支持：{sum(x['共同交集词库'] for x in output):,} 词", "",
        "## 标签计数", "",
    ]
    report += [f"- {name}：{count:,}" for name, count in reason_counts.most_common()]
    report += ["", "## 优先复核样例", ""]
    for item in unsupported[:40]:
        report.append(f"- {item['word']}（位 {item['code']}，词序 {item['two_rank']}，来源 {item['two_groups']}；{item['审计标签']}）")
    report += ["", "建议先复核‘多个标签且无共同交集支持’的词；单个姓名/地名标签不应自动淘汰。", ""]
    (SPLITS / "训练集质量审计报告.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
