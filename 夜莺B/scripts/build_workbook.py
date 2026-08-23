# -*- coding: utf-8 -*-
"""夜莺B 选根工作表：按音节列常用字及其首位部件链 + 常见偏旁部首覆盖统计。"""
import io, sys, json, zlib, os
from collections import defaultdict, Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
B = "D:/nightingale/"; OUT = B + "夜莺B/work/"
r = json.load(open(B + "work/readings.json", encoding="utf-8")); freq = {c: v[0][0] for c, v in r.items()}
top = sorted(r, key=lambda c: -freq[c]); rank = {c: i for i, c in enumerate(top)}
rep = json.loads(zlib.decompress(open(B + "repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate", "rb").read()))
db = {(chr(e["unicode"]) if e.get("unicode") else e.get("name")): e for e in rep}
def glyph(k):
    e = db.get(k)
    if not e: return None
    gs = e["glyphs"]
    for g in gs:
        if g["type"] == "compound" and "G" in g.get("tags", []): return g
    for g in gs:
        if g["type"] == "compound": return g
    return gs[0] if gs else None
def name(k):
    if len(k) == 1 and 0xE000 <= ord(k) <= 0xF8FF: return db.get(k, {}).get("name", k)
    return k
def head_chain(c, depth=0):
    """首位部件链：最外层第一操作数 → 其第一操作数 → …"""
    g = glyph(c); out = []
    while g and g["type"] == "compound" and depth < 6:
        ops = [o for o in g["operandList"] if o]
        if not ops: break
        h = ops[0]; out.append(h); g = glyph(h); depth += 1
    return out
def all_parts(c, acc, d=0):
    g = glyph(c)
    if not g or g["type"] != "compound" or d > 8: return
    for o in g["operandList"]:
        if o: acc.add(o); all_parts(o, acc, d + 1)
def struct(c):
    g = glyph(c)
    if not g or g["type"] != "compound": return "独体"
    return g.get("operator", "?") + "".join(name(o) for o in g["operandList"] if o)
syl = defaultdict(set)
for c, rs in r.items():
    for f, cd in rs: syl[cd[:2]].add(c)
rows = sorted(syl.items(), key=lambda kv: -sum(1 for c in kv[1] if rank[c] < 3500))
with open(OUT + "音节选根工作表.md", "w", encoding="utf-8") as f:
    f.write("# 夜莺B 音节选根工作表\n\n每音节列前 27 常用字（按字频）。列：字(频万) | 结构(hanzi-chai) | 首位部件链(外→内)。\n"
            "任务：每个音节内挑一层部件当根，使高频字首根互不相同且是人认识的部件；跨音节保持同一部件同一拆法。\n\n")
    for s, cs in rows[:40]:
        cs = sorted(cs, key=lambda c: -freq[c]); common = sum(1 for c in cs if rank[c] < 3500)
        f.write(f"## {s}  字数 {len(cs)}  常用 {common}\n\n| 字 | 结构 | 首位部件链 |\n|---|---|---|\n")
        for c in cs[:27]:
            f.write(f"| {c}({freq[c]//10000}) | {struct(c)} | {' → '.join(name(x) for x in head_chain(c)) or '—'} |\n")
        f.write("\n")
# 常见偏旁部首：统计在前6000字中作首位部件/任意位置的字数与频率
RADICALS = ("亻 刂 氵 扌 艹 辶 阝 忄 钅 衤 礻 犭 纟 饣 竹头 灬 宀 冖 广 疒 尸 户 门 囗 口 土 木 火 日 月 目 田 石 山 女 子 马 鸟 鱼 虫 贝 车 舟 讠 见 页 雨 足 走 身 革 食 金 耳 米 糸 禾 竹 立 穴 衣 示 犬 牛 羊 王 玉 心 手 攵 又 力 刀 几 八 人 儿 匕 卜 厂 厶 工 弓 彳 巾 干 廾 弋 彡 夂 夕 大 小 寸 尢 己 巳 巛 川 方 无 欠 止 歹 殳 毛 氏 气 水 爪 父 片 牙 瓜 用 疋 白 皮 皿 矛 矢 内 臣 自 至 臼 舌 艮 色 血 行 西 角 言 谷 豆 豕 豸 赤 辛 辰 邑 酉 釆 里 长 门 隶 隹 青 非 面 韦 音 骨 高 鬼 黑 鼠 鼻 龙 龟 丁 十 二 亠 冫 凵 匚 勹 卩 丬 廴 尤").split()
seen = set(); rad = []
for x in RADICALS:
    if x not in seen: seen.add(x); rad.append(x)
head_cnt = Counter(); head_f = Counter(); any_cnt = Counter(); any_f = Counter(); ex = defaultdict(list)
for c in top[:6000]:
    acc = set(); all_parts(c, acc); hc = set(head_chain(c))
    for p in acc:
        any_cnt[p] += 1; any_f[p] += freq[c]
        if p in hc: head_cnt[p] += 1; head_f[p] += freq[c]
        if len(ex[p]) < 6: ex[p].append(c)
with open(OUT + "偏旁部首覆盖表.tsv", "w", encoding="utf-8") as f:
    f.write("部首\t首位字数\t首位频(万)\t任意位字数\t任意位频(万)\t例字\n")
    for p in sorted(rad, key=lambda p: -any_f[p]):
        f.write(f"{p}\t{head_cnt[p]}\t{head_f[p]//10000}\t{any_cnt[p]}\t{any_f[p]//10000}\t{''.join(ex[p])}\n")
print("音节", len(rows), "；工作表前40音节；部首表", len(rad), "个")
print("部首覆盖前25：", " ".join(f"{p}{any_cnt[p]}" for p in sorted(rad, key=lambda p: -any_f[p])[:25]))
print("部首在前6000零覆盖：", "".join(p for p in rad if any_cnt[p] == 0))
