"""第二遍：g2pW 对第一遍抽出的位置逐条消歧（批=1 最快）。支持断点续跑：结果逐条追加到 out/pass2.jsonl。
每条：{"g": 体裁, "k": "single"/"word", "c": 字, "s": 句, "i": 位置, "dict": 词典读音或null, "g2pw": 去调音节, "conf": 置信度}"""
import json, os, sys, time
from pathlib import Path
import numpy as np, onnxruntime
from g2pw import G2PWConverter
from g2pw.dataset import TextDataset

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'reading'))
from annotate import norm

CAP, VCAP = 200, 15
G = 'news wiki zhihu forum webnovel classic'.split()
OUT = ROOT / 'reading/out/pass2.jsonl'


def jobs():
    for g in G:
        p = json.load(open(ROOT / f'reading/out/{g}.pass1.json', encoding='utf-8'))
        for c, items in p['single_sample'].items():
            for s, i in items[:CAP]:
                yield dict(g=g, k='single', c=c, s=s, i=i, dict=None)
        for c, items in p['vword_sample'].items():
            for s, i, syl in items[:VCAP]:
                yield dict(g=g, k='word', c=c, s=s, i=i, dict=syl)


def main():
    conv = G2PWConverter(model_dir=str(ROOT / 'models/G2PWModel/'), style='pinyin',
                         enable_non_tradional_chinese=True, num_workers=0, batch_size=1)
    so = onnxruntime.SessionOptions()
    so.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = int(os.environ.get('G2PW_THREADS', 6))
    sess = onnxruntime.InferenceSession(str(ROOT / 'models/G2PWModel/g2pw.onnx'), sess_options=so)
    polyset = set(conv.chars)
    done = sum(1 for _ in open(OUT)) if OUT.exists() else 0
    all_jobs = list(jobs())
    print('总任务', len(all_jobs), '已完成', done, flush=True)
    t0 = time.time()
    with open(OUT, 'a', encoding='utf-8') as f:
        for n, j in enumerate(all_jobs[done:], done + 1):
            ts = conv._convert_s2t(j['s'])
            if ts[j['i']] not in polyset:
                j['g2pw'], j['conf'] = None, None
            else:
                ds = TextDataset(conv.tokenizer, conv.labels, conv.char2phonemes, conv.chars, [ts], [j['i']],
                                 use_mask=conv.config.use_mask, use_char_phoneme=conv.config.use_char_phoneme,
                                 window_size=conv.config.window_size, for_train=False)
                b = ds.create_mini_batch([ds[0]])
                probs = sess.run([], {k: b[k].numpy() for k in ('input_ids', 'token_type_ids', 'attention_mask',
                                                                  'phoneme_mask', 'char_ids', 'position_ids')})[0][0]
                k = int(np.argmax(probs))
                lab = conv.labels[k]
                if conv.config.use_char_phoneme:
                    lab = lab.split(' ')[1]
                j['g2pw'], j['conf'] = norm(conv.style_convert_func(lab)), round(float(probs[k]), 4)
            f.write(json.dumps(j, ensure_ascii=False) + '\n')
            if n % 2000 == 0:
                f.flush()
                r = (n - done) / (time.time() - t0)
                print(n, f'{r:.1f}/秒', f'剩余约 {(len(all_jobs) - n) / r / 3600:.1f} 小时', flush=True)


if __name__ == '__main__':
    main()
