"""整句错误分析：切分错误（解码选的切分 ≠ 实际打的切分）与选字错误（切分相同、字选错）；
并统计切分错误里“原本该打的码”和“被误切成的码”的热点。
用法：python tool/sentence/analyze_errors.py <评测输出目录> <套号,...> [方案名,...]
"""
import collections, json, multiprocessing as mp, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_sentence as ES


def work(job):
    name, text, raw, codes = job
    r = ES.G['D'][name].decode(raw)
    top = r[0] if r else None
    got = [(w, raw[p - L:p]) for (w, _, L), p in zip(top['path'], _cum(top['path']))] if top else []
    return name, text, codes, top['text'] if top else '', got


def _cum(path):
    p, out = 0, []
    for _, _, L in path:
        p += L; out.append(p)
    return out


if __name__ == '__main__':
    out = Path(sys.argv[1]); sets = [int(x) for x in sys.argv[2].split(',')]
    names = sys.argv[3].split(',') if len(sys.argv) > 3 else ['虎码', '夜莺C_白名单', '夜莺C_按读音']
    res = json.load(open(out / 'results.json', encoding='utf-8'))
    ES.init()
    chars_of = {}
    for g, chars in ES.clauses(sets, 10 ** 9):
        chars_of.setdefault(''.join(c for c, _ in chars), chars)
    jobs = []
    for g, text, o in res:
        for k in names:
            if o[k][1]:
                chars = chars_of[text]
                if ES.G['S'][k][1] == 'char':
                    codes = [ES.G['S'][k][0].typed(c) for c, _ in chars]
                else:
                    codes = [ES.G['typing']['yy'].typed(c, sy) for c, sy in chars]
                jobs.append((k, text, o[k][2], codes))
    with mp.Pool(8, initializer=ES.init) as pool:
        got = pool.map(work, jobs, chunksize=20)
    stat = collections.defaultdict(collections.Counter)
    seg_true = collections.defaultdict(collections.Counter); seg_got = collections.defaultdict(collections.Counter)
    sel_pair = collections.defaultdict(collections.Counter); ex = collections.defaultdict(list)
    for name, text, codes, top, path in got:
        tc = [sum(map(len, codes[:i + 1])) for i in range(len(codes))]
        gc = []; p = 0
        for w, c in path:
            p += len(c); gc.append(p)
        if tc == gc:
            stat[name]['选字错'] += 1
            for (w, c), ch, cd in zip(path, text, codes):
                if w != ch: sel_pair[name][f'{cd}:{ch}→{w}'] += 1
        else:
            stat[name]['切分错'] += 1
            ts, gs = set(tc), set(gc)
            # 第一个分歧处：实际该打的码与被切成的码
            for i, (w, c) in enumerate(path):
                if gc[i] not in ts or (i and gc[i - 1] not in ts):
                    seg_got[name][c] += 1; break
            k = next((i for i, x in enumerate(tc) if x not in gs), None)
            if k is not None: seg_true[name][codes[k] + ':' + text[k]] += 1
            if len(ex[name]) < 25: ex[name].append(f"{text} → {top}  打 {' '.join(codes)}  切 {' '.join(c for _, c in path)}")
    rep = {}
    for name in names:
        print(f'\n## {name}：错句 {sum(stat[name].values())}，切分错 {stat[name]["切分错"]}，选字错 {stat[name]["选字错"]}')
        print('  切分错时、原本该打的码（字）：', seg_true[name].most_common(25))
        print('  被误切成的码：', seg_got[name].most_common(25))
        print('  选字错（码:原字→误字）：', sel_pair[name].most_common(25))
        for e in ex[name][:12]: print('   ', e)
        rep[name] = {'统计': stat[name], '该打的码': seg_true[name].most_common(200), '误切成': seg_got[name].most_common(200),
                     '选字错': sel_pair[name].most_common(200), '例子': ex[name]}
    json.dump(rep, open(out / 'errors.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
