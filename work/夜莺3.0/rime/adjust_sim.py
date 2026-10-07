"""Rime NB46 手动调整插件的 Python 复刻（与 ~/Library/Rime/lua/yeying_tune_adjust_data.lua 同逻辑），用于重放记录、排查。"""
import collections, sys
from pathlib import Path
R = Path.home() / 'Library/Rime'
base = collections.defaultdict(list); codes = collections.defaultdict(list); freq = {}; core = set()
body = False
for l in open(R / 'yeying_tune.dict.yaml', encoding='utf-8'):
    l = l.rstrip('\n')
    if body:
        p = l.split('\t')
        if len(p) >= 2: base[p[1]].append(p[0]); codes[p[0]].append(p[1])
    elif l == '...': body = True
for l in open(R / 'yeying_tune_freq.txt', encoding='utf-8'):
    t, s, f = l.rstrip('\n').split('\t'); freq[(t, s)] = float(f); core.add(t)
prefix = collections.defaultdict(list)
for t, cs in codes.items():
    if t in core:
        for c in cs:
            if len(c) == 4:
                for L in (1, 2, 3):
                    if t not in prefix[c[:L]]: prefix[c[:L]].append(t)
state = {}
def st(c): return state.setdefault(c, {'order': [], 'removed': set()})
def front(c, x): s = st(c); s['order'] = [v for v in s['order'] if v != x]; s['order'].insert(0, x); s['removed'].discard(x)
def remove_from(c, x): s = st(c); s['order'] = [v for v in s['order'] if v != x]; s['removed'].add(x)
def display(c):
    s = state.get(c); b = base.get(c, [])
    if not s: return list(b)
    out = []
    for t in s['order'] + b:
        if t not in s['removed'] and t not in out: out.append(t)
    return out
def holder(c):
    for t in display(c):
        if t in core: return t
def fulls(t, p): return [c for c in codes.get(t, []) if len(c) == 4 and c.startswith(p)]
def upper(a, s):
    f = fulls(a, s); return f[0][:len(s) + 1] if f and len(s) < 4 else None
def freq_of(t, x): return max([freq.get((t, f[:2]), 0) for f in fulls(t, x)] or [0])
def eligible(t, x): return not any(holder(f[:L]) == t for f in fulls(t, x) for L in range(1, len(x) + 1))
def longer_short(t, x):
    for f in fulls(t, x):
        for L in range(len(x) + 1, 4):
            if holder(f[:L]) == t: return f[:L]
def fill(x, excl):
    if len(x) >= 4 or holder(x): return
    orig = next((t for t in base.get(x, []) if t in core), None)
    if orig and orig not in excl and eligible(orig, x):
        best = orig                     # 先还给码表原占位字
    else:
        cand = [t for t in prefix.get(x, []) if t not in excl and eligible(t, x)]
        if not cand: return
        best = max(cand, key=lambda t: freq_of(t, x))
    y = longer_short(best, x)
    front(x, best); excl.add(best)
    if y: remove_from(y, best); fill(y, excl)
def bump(b, s):
    u = upper(b, s)
    if not u: return
    if len(u) == 4: front(u, b); return
    h = holder(u); front(u, b)
    if h and h != b: remove_from(u, h); bump(h, u)
def apply(code, text, act):
    if act == 'top': front(code, text)
    elif act == 'up':
        t = upper(text, code)
        if not t: return
        remove_from(code, text)
        if len(t) == 4: front(t, text)
        else:
            h = holder(t); front(t, text)
            if h and h != text: remove_from(t, h); bump(h, t)
        fill(code, {text})
    elif act == 'down':
        s = code[:-1]; h = holder(s)
        if len(code) == 4:
            d = [v for v in display(code) if v != text]
            k = next((i for i, v in enumerate(d) if v not in core), len(d))
            st(code)['order'] = d[:k] + [text] + d[k:]
        else: remove_from(code, text)
        front(s, text)
        if h and h != text: remove_from(s, h); bump(h, s)
        if len(code) < 4: fill(code, {text})
if __name__ == '__main__':
    watch = sys.argv[1].split(',') if len(sys.argv) > 1 else ['ui', 'uib', 'uibo', 'uibb', 'uip', 'uipe']
    show = lambda: '  '.join(f'{c}={"".join(display(c)[:3]) or "∅"}' for c in watch)
    print('初始          ', show())
    for l in open(R / 'yeying_tune_adjust.tsv', encoding='utf-8'):
        _, code, text, _, act = l.rstrip('\n').split('\t')
        apply(code, text, act)
        print(f'{code:5}{text}{act:5}', show())
