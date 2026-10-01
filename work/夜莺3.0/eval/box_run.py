"""对一个运行目录跑形码盒子：生成码表 → node 测评 → 返回 JSON。"""
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'eval'))
from make_table import build

def box(elements, code_txt):
    items = build(elements, code_txt)
    with tempfile.TemporaryDirectory() as t:
        tab, out = Path(t) / 't.tsv', Path(t) / 'o.json'
        tab.write_text(''.join(f'{ch}\t{code}\n' for code, _, _, ch, _ in items), encoding='utf-8')
        subprocess.run([str(ROOT / 'tools/node/bin/node'), str(ROOT / 'eval/box/box_eval.mjs'), str(tab), str(out)], check=True)
        return json.load(open(out, encoding='utf-8'))

if __name__ == '__main__':
    print(json.dumps(box(sys.argv[1], sys.argv[2]), ensure_ascii=False)[:500])
