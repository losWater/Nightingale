"""常驻引擎批量评分：Worker(layout) 只加载一次数据，每次评分几十毫秒。"""
import json, os, re, subprocess, tempfile
from pathlib import Path
import engine_eval as E


class Worker:
    def __init__(self):
        self.d = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
        json.dump(E.BASE, open(Path(self.d) / 'run.json', 'w', encoding='utf-8'), ensure_ascii=False)
        env = dict(E.ENV, NIGHTINGALE_BATCH='1')
        self.p = subprocess.Popen([str(E.ENGINE), 'encode', 'run.json', '-e', str(E.INP / 'elements.yaml'),
                                   '-k', str(E.INP / 'distribution.txt'), '-p', str(E.INP / 'equivalence.txt')],
                                  cwd=self.d, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, bufsize=1)

    def score(self, layout):
        self.p.stdin.write(json.dumps(layout) + '\n'); self.p.stdin.flush()
        s = json.loads(self.p.stdout.readline())
        lines = []
        while True:
            l = self.p.stderr.readline()
            if not l:
                raise RuntimeError('引擎退出')
            if l.startswith('BATCH_END'):
                break
            lines.append(l)
        r = {'total': s['score'], 'move': s['complexity'], 'q': s['score'] - s['complexity']}
        y = [l for l in lines if l.startswith('YOZAKURA exclusive')][-1]
        r['excl'] = json.loads(re.search(r'exclusive=(\[[^\]]*\])', y).group(1))
        r['mutex'] = int(re.search(r'mutex=(\d+)', y).group(1))
        sh = dict(re.findall(r'(\w+)=([0-9.]+)', [l for l in lines if l.startswith('YOZAKURA_SHAPE')][-1]))
        r.update({k: float(v) for k, v in sh.items()})
        r['clash'] = json.loads([l for l in lines if l.startswith('YOZAKURA_CLASH')][-1].split(' ', 1)[1])
        r['gates'] = E.gates(r)
        return r


if __name__ == '__main__':
    import time
    w = Worker()
    c = E.champion(); b = E.META['layout']
    for lay in (c, b, c):
        t = time.time(); r = w.score(lay); print(round(r['total'], 1), r['cost'], r['excl'], r['clash'], r['gates'], round(time.time() - t, 3))
