"""生成夜桜「普通单字表」（夜莺2.5 同格式：字\\t码，按码排序，同码按候选序；含符号表）。

内容：
- 8105 核心字全部读音：全码 + 简码（一二简=固定沿用2.5；三简=引擎退火时自动分配，暂定）。
- 扩展字（2.5 单字表中 8105 以外的字）：2.5 正式全码的音节（小鹤→自然码）+ 新布局首末根键；无简码。
- 符号表：沿用 2.5 原码。
- 手动三简（可选，环境变量 YZ_MANUAL 指向 data/inputs/3.0手动调整.json）：指定三码只给指定字，原占位字退回全码。
- 二简字补三码：有二简的读音，若其全码前三码在整张表里没有任何字，就把该字也放上去（二码、三码同字）。
同码候选序：
- 简码位：按引擎候选位。
- 全码位：无简码读音在前、有简码读音让位在后（有简让全）；各自按读音频率降序；扩展字排在核心字之后；符号最后。
不含：2.5 容错码（按旧布局设计）；特殊二简 by莺 eh鹤 en嗯 jv剧 xv绪（待作者裁定）。

用法：python build/make_plain_table.py <方案运行目录> <输出目录>
"""
import json, os, sys, collections
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode

N25 = Path.home() / 'Nightingale/夜莺2.5'
INP = ROOT / 'build/out' / os.environ.get('YZ_INP', 'n30')   # 2026-10-02：默认改用 n30（formal 为旧自然码赛，条目已不对齐）
L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)


def main(run_dir, out_dir, scheme='ziranma'):
    run_dir, out_dir = Path(run_dir), Path(out_dir)
    out = sorted(run_dir.glob('output-*'))[0]
    cfg = yaml.load(open(out / 'config.yaml', encoding='utf-8'), Loader=L)
    mapping = cfg['form']['mapping']
    meta = json.load(open(INP / 'meta.json', encoding='utf-8'))
    g_of = {r: g for g, rs in meta['groups'].items() for r in rs}
    splits = json.load(open(os.environ.get('YZ_SPLITS') or ROOT / 'data/baseline/splits.json', encoding='utf-8'))
    splits25 = json.load(open(ROOT / 'data/baseline/splits_2.5.json', encoding='utf-8'))   # 核对扩展字的 2.5 码用
    E = yaml.load(open(INP / 'elements.yaml', encoding='utf-8'), Loader=L)
    n = sum(1 for e in E if e['拼音'] != 'reserved')
    rows = [l.rstrip('\n').split('\t') for l in open(out / 'code.txt', encoding='utf-8')][:n]

    def root_keys(ch):
        rs = splits[ch]
        return mapping[g_of[rs[0][0]]] + mapping[g_of[rs[-1][0]]]

    # ---- 核心字 ----
    slots = collections.defaultdict(list)       # 码 -> [(排序键, 字)]
    core_chars = set()
    two_short = []                              # 二简读音：(候选位, 序号, 字, 全码)
    for i, r in enumerate(rows):
        ch, full, short = r[0], r[1], r[3]
        core_chars.add(ch)
        f = E[i]['频率']
        has_short = bool(short) and len(short) < len(full)
        assert full[2:] == root_keys(ch), (ch, full)
        slots[full].append(((0, 1 if has_short else 0, -f, i), ch))
        if has_short:
            slots[short].append(((0, 0, int(r[4]), i), ch))
            if len(short) == 2:
                two_short.append((int(r[4]), i, ch, full))

    # ---- 扩展字 ----
    all_py = json.load(open(ROOT / 'data/inputs/全音节映射.json', encoding='utf-8'))['小鹤']
    all_py = [*all_py, 'fiao', 'rua', 'chua']         # 音节表缺这三个罕见音节：覅 fiao、挼 rua、歘 chua（2.5 有，2026-10-07 补）
    xh2zr = {}
    for py in all_py:
        xh2zr.setdefault(encode(py, 'xiaohe'), set()).add(encode(py, scheme))
    assert all(len(v) == 1 for v in xh2zr.values())
    xh2zr = {k: v.pop() for k, v in xh2zr.items()}
    old_keys = json.load(open(ROOT / 'data/baseline/root_key.json', encoding='utf-8'))
    ext, skipped = 0, []
    seen = set()
    for l in open(N25 / '主表/单字表.txt', encoding='utf-8-sig'):
        p = l.rstrip('\n').split('\t')
        if len(p) < 2 or len(p[0]) != 1 or p[0] in core_chars or len(p[1]) != 4:
            continue
        ch, code = p[0], p[1]
        if ch not in splits:
            skipped.append(ch); continue
        rs25 = splits25.get(ch, splits[ch])
        if code[2:] != old_keys[rs25[0][0]] + old_keys[rs25[-1][0]]:
            continue                              # 非正式全码（容错等）
        if code[:2] not in xh2zr:
            skipped.append(ch); continue
        new = xh2zr[code[:2]] + root_keys(ch)
        if (ch, new) in seen:
            continue
        seen.add((ch, new))
        slots[new].append(((1, 0, 0, ext), ch))
        ext += 1

    # ---- 符号表 ----
    sym = 0
    for l in open(N25 / '主表/符号表.txt', encoding='utf-8-sig'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 2:
            slots[p[1]].append(((2, 0, 0, sym), p[0]))
            sym += 1

    # ---- 手动三简（可选）----
    manual = os.environ.get('YZ_MANUAL')
    if manual:
        for code2, ch, _ in json.load(open(manual, encoding='utf-8')).get('二简', []):
            idx = next(i for i, r in enumerate(rows) if r[0] == ch and r[1][:2] == code2)   # 该读音
            old = [x for _, x in slots.get(code2, [])]
            slots[code2] = [((0, 0, 0, -1), ch)]
            for c, v in slots.items():
                if len(c) == 4 and c[:2] == code2:
                    slots[c] = [((k[0], 1 if x == ch else (0 if x in old else k[1]), k[2], k[3]), x) if k[0] == 0 else (k, x) for k, x in v]
            two_short[:] = [t for t in two_short if not (t[3][:2] == code2 and t[2] in old)] + [(0, idx, ch, rows[idx][1])]
            print('手动二简', code2, ch, '（原', ''.join(old) or '空', '）')
        for code3, ch, _ in json.load(open(manual, encoding='utf-8'))['三简']:
            assert any(c[:3] == code3 and len(c) == 4 and ch in [x for _, x in v] for c, v in slots.items()), (code3, ch)
            old = [x for _, x in slots.get(code3, [])]
            slots[code3] = [((0, 0, 0, -1), ch)]
            # 全码位的“有简让全”标记跟着改：得三简的字标为有简，失去的标为无简
            for c, v in slots.items():
                if len(c) == 4 and c[:3] == code3:
                    slots[c] = [((k[0], 1 if x == ch else (0 if x in old else k[1]), k[2], k[3]), x) if k[0] == 0 else (k, x) for k, x in v]
            print('手动三简', code3, ch, '（原', ''.join(old) or '空', '）')

    # ---- 二简字补三码（2026-10-02 作者定）：三码位空着才补 ----
    filled = 0
    for _, i, ch, full in sorted(two_short):
        if full[:3] not in slots:
            slots[full[:3]].append(((0, 0, 0, i), ch))
            filled += 1

    out_dir.mkdir(parents=True, exist_ok=True)
    lines = []
    for code in sorted(slots):
        placed = set()       # 同字同码只列一次（如 咯 lo/luo、哼 heng/hng 双拼同码）
        for _, ch in sorted(slots[code]):
            if ch not in placed:
                placed.add(ch)
                lines.append(f'{ch}\t{code}\n')
    tag = '' if scheme == 'ziranma' else '小鹤_'
    path = out_dir / f'夜桜_{tag}{run_dir.name}_普通单字表.txt'
    path.write_text(''.join(lines), encoding='utf-8')
    stat = collections.Counter(len(c) for c in slots for _ in slots[c])
    print('输出', path, '行数', len(lines), '；码长分布', dict(sorted(stat.items())),
          '；扩展字', ext, '；符号', sym, '；二简补三码', filled, '；跳过', len(skipped))
    return path


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'ziranma')
