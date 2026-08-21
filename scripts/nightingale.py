# -*- coding: utf-8 -*-
"""夜莺码维护工具箱（v0.4 交接版）。用法: python scripts/nightingale.py <命令> [参数]

查询类（只读）:
  chai 字...              查拆分/全部码/简码/各码位排位（含词层）
  has 部件 [head|tail|any] 查含某部件的字（按拆分元素）
  slot 码...              查码位占用（纯单版+字词总表双层）
  word 词                 查词的码与码位
  pua                     列出全部 PUA 私用区部件及标签/就业
  dup [N]                 主码口径全码重码报告（前N，默认6000）
  charword 字             字词冲突体检（保护字测试: 独立频 vs 各码位最高词频）
  free 前缀               列出某前缀下的空码位

改动类（改完自动提示 rebuild）:
  addcode 字 码           加副码（双码并存）
  delcode 字 码           删码（根搬家/幽灵码清理用）
  setmain 字 码           把某码提为主码（影响简码竞争前缀）
  decree 字 码            御旨简码（占主竞争位, 写入 work/御旨.json FORCED）
  decree-extra 字 码      御旨副简码（追加发放, FORCED_EXTRA）
  alt 字 根1 根2...       多拆登记（查码页显示备选拆法）
  replace-split 根 模式... [--where any|head|tail] [--include 字集] [--exclude 字集]
                          批量改拆分（三份数据文件同步），改后需 sync+rebuild

流程类:
  sync                    拆分↔码表对账补码（scripts/sync_readings.py）
  rebuild                 全链重生成（纯单/搜狗/留位/总表/Rime/查码/图/总表md/普查）
  census                  字根就业普查（scripts/root_census.py）
  propose                 择键遍历评估（scripts/propose_root.py，需先编辑其候选表）
"""
import io
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
REL = BASE / "releases/v0.4"

def load_readings():
    return json.load(open(BASE / "work/readings.json", encoding="utf-8"))

def load_splits():
    d = {}
    for line in open(BASE / "work/v04_final.tsv.splits.tsv", encoding="utf-8"):
        c, _, rest = line.rstrip("\n").partition("\t")
        if len(c) == 1 and c not in d:
            d[c] = rest.split(" ")
    return d

def load_pure():
    full = defaultdict(list)
    short = {}
    for line in open(REL / "夜莺码v0.4纯单版.txt", encoding="utf-8"):
        c, _, cd = line.strip().partition("\t")
        full[cd].append(c)
        if c not in short or len(cd) < len(short[c]):
            short[c] = cd
    return full, short

def load_zong():
    slot = defaultdict(list)
    for line in open(REL / "夜莺码v0.4字词总表.txt", encoding="utf-8"):
        w, _, cd = line.strip().partition("\t")
        slot[cd].append(w)
    return slot

def label(r):
    if len(r) == 1 and 0xE000 <= ord(r[0]) <= 0xF8FF:
        NAMES = {0xE900: "学字头", 0xE901: "党字头", 0xE902: "官字腹", 0xE437: "止旁变体",
                 0xE43A: "垂土(里底)", 0xE02A: "丹周框", 0xE055: "扁字框", 0xE0D2: "青字底/俞月",
                 0xE414: "其字头", 0xF000: "禺字底", 0xE0C6: "足旁", 0xE0C8: "车旁(斩)",
                 0xE0D0: "雨头", 0xE029: "先字头", 0xE012: "北丬", 0xE011: "化匕",
                 0xE432: "录彐", 0xE0D6: "风框", 0xE08C: "甬底", 0xE07F: "流巛",
                 0xE050: "带艹", 0xE0B2: "卫卩", 0xE988: "丽半", 0xE0C9: "辣辛", 0xE055: "扁框", 0xE0DA: "鸟去横"}
        return f"{r}[{NAMES.get(ord(r[0]), 'PUA' + hex(ord(r[0]))[2:])}]"
    return r

def cmd_chai(args):
    readings = load_readings()
    splits = load_splits()
    full, short = load_pure()
    zong = load_zong()
    for c in "".join(args):
        if c not in splits and c not in readings:
            print(f"{c}: 不在码表"); continue
        sh = splits.get(c, [])
        print(f"{c} 拆分: {' '.join(label(x) for x in sh)}  简码: {short.get(c, '无')}")
        for f, cd in readings.get(c, []):
            occ = zong.get(cd, [])
            r = (occ.index(c) + 1) if c in occ else "?"
            others = [x for x in occ if x != c][:3]
            print(f"   {cd} 第{r}" + (f" (同位: {','.join(others)})" if others else ""))

def cmd_has(args):
    part = args[0]
    where = args[1] if len(args) > 1 else "any"
    readings = load_readings()
    freq = {c: rs[0][0] for c, rs in readings.items()}
    splits = load_splits()
    out = []
    for c, sh in splits.items():
        if c not in readings or part not in sh:
            continue
        pos = "整" if sh == [part] else ("头" if sh[0] == part else ("尾" if sh[-1] == part else "中"))
        if where == "head" and pos not in ("头", "整"): continue
        if where == "tail" and pos not in ("尾", "整"): continue
        out.append((freq[c], c, pos))
    out.sort(reverse=True)
    print(f"含[{part}]共{len(out)}字:")
    for f, c, pos in out[:60]:
        print(f"  {c} {f//10000}万 [{pos}]")

def cmd_slot(args):
    full, short = load_pure()
    zong = load_zong()
    for cd in args:
        print(f"{cd}: 纯单={full.get(cd, '空')}  总表={zong.get(cd, ['空'])[:8]}")

def cmd_word(args):
    zong = load_zong()
    w = args[0]
    hits = [(cd, ws) for cd, ws in zong.items() if w in ws]
    for cd, ws in hits:
        print(f"{w} @ {cd} 第{ws.index(w)+1} (同位: {[x for x in ws if x != w][:5]})")
    if not hits:
        print(f"{w}: 不在字词总表")

def cmd_pua(args):
    import yaml
    splits = load_splits()
    cfg = yaml.safe_load(open(REL / "夜莺码v0.4键位布局.yaml", encoding="utf-8"))
    use = defaultdict(int)
    ex = defaultdict(list)
    for c, sh in splits.items():
        for r in set(sh):
            if 0xE000 <= ord(r[0]) <= 0xF8FF:
                use[r] += 1
                if len(ex[r]) < 8:
                    ex[r].append(c)
    m = cfg["form"]["mapping"]
    for r in sorted(use, key=lambda x: -use[x]):
        v = m.get(r)
        key = v if isinstance(v, str) else (f"附属→{v['element']}" if v else "未映射!")
        print(f"{label(r)} U+{ord(r[0]):04X} 键[{key}] {use[r]}字: {''.join(ex[r])}")

def cmd_dup(args):
    n = int(args[0]) if args else 6000
    readings = load_readings()
    freq = {c: rs[0][0] for c, rs in readings.items()}
    top = set(sorted(readings, key=lambda c: -freq[c])[:n])
    m = defaultdict(list)
    for c in top:
        cd = readings[c][0][1]
        if len(cd) == 4:
            m[cd].append(c)
    slots = {cd: cs for cd, cs in m.items() if len(cs) > 1}
    tot = sum(freq[c] for c in top)
    burden = sum(sum(freq[x] for x in sorted(cs, key=lambda y: -freq[y])[1:]) for cs in slots.values())
    print(f"前{n} 主码口径: 重码位{len(slots)} 选重负担{burden/tot*100:.3f}%")
    for cd, cs in sorted(slots.items(), key=lambda kv: -max(freq[x] for x in kv[1]))[:20]:
        print(f"  {cd}: {' '.join(sorted(cs, key=lambda y: -freq[y]))}")

def cmd_charword(args):
    c = args[0]
    readings = load_readings()
    freq = {ch: rs[0][0] for ch, rs in readings.items()}
    wfreq = {}
    for line in open(BASE / "repos/webchai/packages/hanzi-chai/src/data/dictionary.txt", encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 3 and len(p[0]) >= 2:
            try:
                wfreq[p[0]] = max(wfreq.get(p[0], 0), int(p[2]))
            except ValueError:
                pass
    inword = defaultdict(int)
    for w, f in wfreq.items():
        for ch in set(w):
            inword[ch] += f
    sa = max(0, freq.get(c, 0) - inword.get(c, 0))
    code_wmax = defaultdict(int)
    for line in open(BASE / "work/夜莺码_大词库编码版.txt", encoding="utf-8"):
        p = line.rstrip().split("\t")
        if len(p) >= 2:
            f = wfreq.get(p[0], 0)
            if f > code_wmax[p[1]]:
                code_wmax[p[1]] = f
    print(f"{c}: 总频{freq.get(c,0)//10000}万 独立频{sa//10000}万")
    for f, cd in readings.get(c, []):
        wm = code_wmax.get(cd, 0)
        verdict = "保护字✅首选" if (sa >= wm or wm < 10000) else f"让位（该位最高词频{wm//10000}万）"
        print(f"   {cd}: {verdict}")

def cmd_free(args):
    pre = args[0]
    full, short = load_pure()
    zong = load_zong()
    used = set()
    for cd in list(full) + list(zong):
        if cd.startswith(pre) and len(cd) == len(pre) + 1:
            used.add(cd[-1])
    freeks = [k for k in "abcdefghijklmnopqrstuvwxyz" if k not in used]
    print(f"{pre}? 空位: {' '.join(freeks) or '无'}  已占: {' '.join(sorted(used))}")

def _save_readings(r):
    json.dump(r, open(BASE / "work/readings.json", "w", encoding="utf-8"), ensure_ascii=False)

def cmd_addcode(args):
    c, cd = args[0], args[1]
    r = load_readings()
    if cd in [x[1] for x in r[c]]:
        print("已存在"); return
    r[c] = r[c] + [[r[c][0][0], cd]]
    _save_readings(r)
    print(f"{c} += {cd}（副码）→ 记得 rebuild")

def cmd_delcode(args):
    c, cd = args[0], args[1]
    r = load_readings()
    r[c] = [x for x in r[c] if x[1] != cd]
    _save_readings(r)
    print(f"{c} -= {cd} → 记得 rebuild")

def cmd_setmain(args):
    c, cd = args[0], args[1]
    r = load_readings()
    hit = [x for x in r[c] if x[1] == cd]
    if not hit:
        print("该码不存在，先 addcode"); return
    r[c] = hit + [x for x in r[c] if x[1] != cd]
    _save_readings(r)
    print(f"{c} 主码 → {cd}（简码竞争前缀随之改变）→ 记得 rebuild")

def _decree(c, cd, extra):
    yz = json.load(open(BASE / "work/御旨.json", encoding="utf-8"))
    if extra:
        if [c, cd] not in yz["FORCED_EXTRA"]:
            yz["FORCED_EXTRA"].append([c, cd])
    else:
        yz["FORCED"][c] = cd
    json.dump(yz, open(BASE / "work/御旨.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"御旨{'副' if extra else ''}简码 {c}={cd} 已录 → 记得 rebuild")

def cmd_alt(args):
    c = args[0]
    seq = " ".join(args[1:])
    lines = [l.rstrip("\n") for l in open(BASE / "work/多拆登记.tsv", encoding="utf-8") if l.strip()]
    entry = f"{c}\t{seq}"
    if entry not in lines:
        lines.append(entry)
    open(BASE / "work/多拆登记.tsv", "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print(f"多拆登记 {c} = {seq} → 记得 rebuild（查码页生效）")

def cmd_replace_split(args):
    root = args[0]
    where = "any"
    inc = exc = None
    pat = []
    i = 1
    while i < len(args):
        a = args[i]
        if a == "--where":
            where = args[i + 1]; i += 2
        elif a == "--include":
            inc = set(args[i + 1]); i += 2
        elif a == "--exclude":
            exc = set(args[i + 1]); i += 2
        else:
            pat.append(a); i += 1
    splits = {}
    order = []
    for line in open(BASE / "work/v04_final.tsv.splits.tsv", encoding="utf-8"):
        c, _, rest = line.rstrip("\n").partition("\t")
        if c and c not in splits:
            splits[c] = rest.split(" "); order.append(c)
    n = len(pat)
    changed = {}
    for c in order:
        if len(c) != 1: continue
        if inc is not None and c not in inc: continue
        if exc and c in exc: continue
        sh = splits[c]; ns = []; i2 = 0; ch = False
        while i2 < len(sh):
            if sh[i2:i2 + n] == pat:
                pos = "whole" if (i2 == 0 and i2 + n == len(sh)) else ("head" if i2 == 0 else ("tail" if i2 + n == len(sh) else "mid"))
                ok = (where == "any") or (where == "head" and pos in ("head", "whole")) or (where == "tail" and pos in ("tail", "whole"))
                if ok:
                    ns.append(root); i2 += n; ch = True; continue
            ns.append(sh[i2]); i2 += 1
        if ch:
            changed[c] = (sh, ns); splits[c] = ns
    with open(BASE / "work/v04_final.tsv.splits.tsv", "w", encoding="utf-8", newline="\n") as f:
        for c in order:
            f.write(c + "\t" + " ".join(splits[c]) + "\n")
    lines = []
    for line in open(BASE / "work/v04_final.tsv", encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 2 and len(p[0]) == 1 and p[0] in changed:
            toks = [json.loads(t) for t in p[1].split(" ")]
            pre = [t["element"] for t in toks if t["element"].startswith(("szm-", "mzm-"))]
            p[1] = " ".join(json.dumps({"element": e, "index": 0}, ensure_ascii=False, separators=(",", ":")) for e in pre + changed[p[0]][1])
        lines.append("\t".join(p))
    open(BASE / "work/v04_final.tsv", "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    txt = open(BASE / "work/optimize/elements_v04.yaml", encoding="utf-8").read()
    blocks = txt.split("- 词: ")
    for i3, b in enumerate(blocks[1:], 1):
        w = b.split("\n", 1)[0]
        if w in changed:
            ns = changed[w][1]
            body = b.split("\n"); keep = []
            for j, l in enumerate(body):
                st = l.strip()
                if st.startswith("- element: szm-") or st.startswith("- element: mzm-"):
                    keep.append(l); keep.append(body[j + 1])
            freqline = [l for l in body if l.strip().startswith("频率:")]
            nb = [w, "  元素序列:"] + keep
            for e in (ns[0], ns[-1]):
                nb.append("  - element: " + e); nb.append("    index: 0")
            nb += freqline
            blocks[i3] = "\n".join(nb) + "\n"
    open(BASE / "work/optimize/elements_v04.yaml", "w", encoding="utf-8", newline="\n").write("- 词: ".join(blocks))
    print(f"拆分替换 [{' '.join(pat)}]→{root}: {len(changed)}字: {''.join(changed)}")
    print("→ 若为新根记得先在 yaml 里加映射，然后 sync + rebuild + census")

def run(script):
    subprocess.run([sys.executable, str(BASE / "scripts" / script)], check=False)

def cmd_rebuild(args):
    for sc in ["make_release.py", "make_liuwei.py", "make_words.py", "make_rime.py", "gen_tools.py", "draw_chart.py", "gen_root_table.py", "root_census.py"]:
        print(f"== {sc} ==")
        run(sc)

def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1]
    args = sys.argv[2:]
    table = {
        "chai": cmd_chai, "has": cmd_has, "slot": cmd_slot, "word": cmd_word,
        "pua": cmd_pua, "dup": cmd_dup, "charword": cmd_charword, "free": cmd_free,
        "addcode": cmd_addcode, "delcode": cmd_delcode, "setmain": cmd_setmain,
        "alt": cmd_alt, "replace-split": cmd_replace_split, "rebuild": cmd_rebuild,
        "decree": lambda a: _decree(a[0], a[1], False),
        "decree-extra": lambda a: _decree(a[0], a[1], True),
        "sync": lambda a: run("sync_readings.py"),
        "census": lambda a: run("root_census.py"),
        "propose": lambda a: run("propose_root.py"),
    }
    fn = table.get(cmd)
    if not fn:
        print(f"未知命令 {cmd}\n"); print(__doc__); return
    fn(args)

if __name__ == "__main__":
    main()
