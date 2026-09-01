# -*- coding: utf-8 -*-
"""裁决材料：对指定字根（默认=贪心新增的全部）做单根反事实测试。

对每个根 r：从当前 174 根中单独拿掉 r，重拆重评，报告
  ΔJ        裁掉它的代价（越小越该裁）
  新增零阶组 它目前正在救的字
输出 work/adjudication.tsv + 控制台摘要。
"""
import io
import json
import subprocess
import sys
import tempfile
import shutil
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"
CHARSET = BASE / "data/jdhe/简单鹤V1.0纯单版.txt"
BUN = r"C:\Users\asus\.bun\bin\bun.exe"
W_ZERO, W_D1 = 0.6, 0.02

sys.path.insert(0, str(BASE / "scripts"))
from score import load_phonetic_keys, load_entries
from greedy import make_config, load_charset


def analyze(base_cfg, roots, tag, phon, charset, tmpdir):
    cfgp = Path(tmpdir) / f"c_{tag}.yaml"
    outp = Path(tmpdir) / f"o_{tag}.tsv"
    make_config(base_cfg, roots, cfgp)
    r = subprocess.run([BUN, str(BASE / "scripts/assemble.ts"), str(cfgp), str(outp), str(CHARSET)],
                       capture_output=True, timeout=180)
    if r.returncode != 0:
        return None
    entries = load_entries(outp, phon, charset)
    zero = defaultdict(list)
    for ch, pp, r3, r4, freq in entries:
        zero[(pp, r3, r4)].append((freq, ch))
    zg = {k: sorted(v, reverse=True) for k, v in zero.items() if len(v) > 1}
    z_count = sum(len(v) - 1 for v in zg.values())
    total = sum(e[4] for e in entries) or 1
    z_w = sum(f for v in zg.values() for f, _ in v[1:]) / total
    m1, m2 = defaultdict(int), defaultdict(int)
    for ch, pp, r3, r4, freq in entries:
        m1[(pp, r3)] += 1
        m2[(pp, r4)] += 1
    d1 = (sum(c*(c-1) for c in m1.values()) + sum(c*(c-1) for c in m2.values())) / 50 \
        - sum(len(v)*(len(v)-1) for v in zg.values()) / 50
    J = z_w * 10000 + W_ZERO * z_count + W_D1 * d1
    groups = {k: "".join(c for _, c in v) for k, v in zg.items()}
    return {"J": J, "zero": z_count, "zero_w_bp": z_w * 10000, "d1": d1, "groups": groups}


def main():
    base_cfg = yaml.safe_load(open(WORK / "seed.yaml", encoding="utf-8"))
    phon = load_phonetic_keys(WORK / "seed.yaml")
    charset = load_charset()
    roots = [l.strip() for l in open(WORK / "seed_roots.txt", encoding="utf-8") if l.strip()]

    # 贪心新增名单（按采纳顺序）
    added = []
    for l in open(WORK / "greedy_log.tsv", encoding="utf-8"):
        p = l.rstrip("\n").split("\t")
        if len(p) >= 2 and p[1].startswith("+"):
            added.append(p[1][1:])
    added = [c for c in added if c in roots]
    if "--all" in sys.argv:
        added = [c for c in roots if c not in "123456"]
    print(f"当前 {len(roots)} 根；反事实测试 {len(added)} 个贪心新增根")

    tmpdir = tempfile.mkdtemp(prefix="adj_")
    try:
        base = analyze(base_cfg, roots, "full", phon, charset, tmpdir)
        print(f"基线 J={base['J']:.2f} 零阶{base['zero']} 加权{base['zero_w_bp']:.2f}bp\n")

        def run(c):
            res = analyze(base_cfg, [x for x in roots if x != c], f"d{ord(c[0]):x}", phon, charset, tmpdir)
            return c, res

        rows = []
        with ThreadPoolExecutor(max_workers=6) as ex:
            for c, res in ex.map(run, added):
                if not res:
                    rows.append((c, None, None))
                    continue
                dJ = res["J"] - base["J"]
                new_groups = [v for k, v in res["groups"].items() if k not in base["groups"]]
                rows.append((c, dJ, "、".join(sorted(new_groups))))

        rows.sort(key=lambda r: (r[1] is None, r[1] or 0))
        with open(WORK / ("adjudication_all.tsv" if "--all" in sys.argv else "adjudication.tsv"), "w", encoding="utf-8") as f:
            f.write("根\tcodepoint\t裁掉代价ΔJ\t它救着的字\n")
            for c, dJ, saved in rows:
                cp = " ".join(f"U+{ord(x):04X}" for x in c)
                f.write(f"{c}\t{cp}\t{'' if dJ is None else f'{dJ:.2f}'}\t{saved or ''}\n")
        print("裁掉代价从小到大：")
        for c, dJ, saved in rows:
            cp = "/".join(f"U+{ord(x):04X}" for x in c)
            print(f"  {c}({cp}): ΔJ=+{dJ:.2f}  救着: {saved[:60] if saved else '?'}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
