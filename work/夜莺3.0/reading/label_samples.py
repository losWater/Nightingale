"""g2pW 标注 sample_all 抽出的全部位置（批=1），复用 pass2.jsonl 已有结果；断点续跑。
输出 out/labels.jsonl：{"g","c","s","i","py","single","g2pw","conf"}"""
import json, os, sys, time
from pathlib import Path
import numpy as np, onnxruntime
from g2pw import G2PWConverter
from g2pw.dataset import TextDataset

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'reading'))
from annotate import norm

G = 'news wiki zhihu forum webnovel classic'.split()
OUT = ROOT / 'reading/out/labels.jsonl'

cache = {}
for l in open(ROOT / 'reading/out/pass2.jsonl', encoding='utf-8'):
    j = json.loads(l)
    cache[(j['s'], j['i'])] = (j['g2pw'], j['conf'])

jobs = []
for g in G:
    for c, items in json.load(open(ROOT / f'reading/out/{g}.sample.json', encoding='utf-8'))['sample'].items():
        for s, i, py, single in items:
            jobs.append(dict(g=g, c=c, s=s, i=i, py=py, single=single))

conv = G2PWConverter(model_dir=str(ROOT / 'models/G2PWModel/'), style='pinyin',
                     enable_non_tradional_chinese=True, num_workers=0, batch_size=1)
so = onnxruntime.SessionOptions()
so.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
so.intra_op_num_threads = int(os.environ.get('G2PW_THREADS', 6))
sess = onnxruntime.InferenceSession(str(ROOT / 'models/G2PWModel/g2pw.onnx'), sess_options=so)
polyset = set(conv.chars)


def label(s, i):
    ts = conv._convert_s2t(s)
    if ts[i] not in polyset:
        return None, None
    ds = TextDataset(conv.tokenizer, conv.labels, conv.char2phonemes, conv.chars, [ts], [i],
                     use_mask=conv.config.use_mask, use_char_phoneme=conv.config.use_char_phoneme,
                     window_size=conv.config.window_size, for_train=False)
    b = ds.create_mini_batch([ds[0]])
    probs = sess.run([], {k: b[k].numpy() for k in ('input_ids', 'token_type_ids', 'attention_mask',
                                                      'phoneme_mask', 'char_ids', 'position_ids')})[0][0]
    k = int(np.argmax(probs))
    lab = conv.labels[k]
    if conv.config.use_char_phoneme:
        lab = lab.split(' ')[1]
    return norm(conv.style_convert_func(lab)), round(float(probs[k]), 4)


if __name__ == '__main__':
    done = sum(1 for _ in open(OUT)) if OUT.exists() else 0
    print('总任务', len(jobs), '已完成', done, '缓存', len(cache), flush=True)
    t0, hit = time.time(), 0
    with open(OUT, 'a', encoding='utf-8') as f:
        for n, j in enumerate(jobs[done:], done + 1):
            key = (j['s'], j['i'])
            if key in cache:
                hit += 1
                j['g2pw'], j['conf'] = cache[key]
            else:
                j['g2pw'], j['conf'] = label(*key)
            f.write(json.dumps(j, ensure_ascii=False) + '\n')
            if n % 5000 == 0:
                f.flush()
                r = (n - done) / (time.time() - t0)
                print(n, f'{r:.1f}/秒', '缓存命中', hit, f'剩余约 {(len(jobs) - n) / r / 3600:.1f} 小时', flush=True)
    print('完成', flush=True)
