"""Derive smoke-test key sequences from the package's own dictionaries.

No version-specific codes are hard-coded here: every check is read from the
*.dict.yaml files inside the package being verified, so the same verifier works
for every release (Mac and Windows share this module).
"""
from pathlib import Path
import re

CODE = re.compile(r'[a-z]+')


def entries(stage):
    """code -> {text: weight} across every top-level *.dict.yaml in the package."""
    out = {}
    for path in sorted(Path(stage).glob('*.dict.yaml')):
        body = path.read_text(encoding='utf-8').split('\n...\n', 1)
        if len(body) < 2:
            continue
        for line in body[1].splitlines():
            parts = line.split('\t')
            if len(parts) < 2 or line.startswith('#') or not CODE.fullmatch(parts[1]):
                continue
            weight = float(parts[2]) if len(parts) > 2 and re.fullmatch(r'[0-9.]+', parts[2]) else 0.0
            texts = out.setdefault(parts[1], {})
            texts[parts[0]] = max(weight, texts.get(parts[0], 0.0))
    return out


def spread(items, n):
    """n items evenly spaced through a sorted list (deterministic)."""
    if len(items) <= n:
        return items
    return [items[i * len(items) // n] for i in range(n)]


def flavor(schema):
    return next((f for f in ('v5', 'shape', 'single') if schema.endswith('_' + f)), 'shape')


def checks(stage, schema):
    """Return (inputs, commits, sentence, punct):
    commits  = [(keys, expected committed text)] for codes that map to exactly one character;
    sentence = (keys, text) for the V5 model check, or None;
    punct    = [(keys, text)] period-commit checks for the single-character schema."""
    e = entries(stage)
    unique = lambda n: sorted(c for c, t in e.items() if len(c) == n and len(t) == 1 and len(next(iter(t))) == 1)
    picked = spread(unique(4), 12) + spread(unique(3), 4)
    assert len(picked) >= 8, 'too few unique codes found in package dictionaries'
    commits = [(c + '{space}', next(iter(e[c]))) for c in picked]
    sentence = punct = None
    inputs = [k for k, _ in commits]
    if flavor(schema) == 'v5':
        sentence = ('woxihryeyk', '我喜欢夜莺')        # 小鹤双拼整句，与码表版本无关
        inputs += [sentence[0], sentence[0] + '{space}']
    if flavor(schema) == 'single':
        punct = []
        for c in 'abcdefghijklmnopqrstuvwxyz':
            if c in e and len(punct) < 2:
                top = max(e[c].items(), key=lambda kv: kv[1])[0]
                if len(top) == 1:
                    punct.append((c + '.', top + '。'))
        inputs += [k for k, _ in punct]
    return inputs, commits, sentence, punct


def deployed_schemas(stage):
    """部署后用户在切换菜单里能看到的方案：build/default.yaml 列出、且 build/ 里真的编译出了该方案。"""
    text = (Path(stage) / 'build/default.yaml').read_text(encoding='utf-8')
    block = text.split('\nschema_list:\n', 1)[1]
    out = []
    for line in block.splitlines():
        m = re.fullmatch(r'\s+- schema: (\S+)', line)
        if not m: break
        out.append(m.group(1))
    return [s for s in out if (Path(stage) / 'build' / f'{s}.schema.yaml').exists()]   # 列出且真的编译出来了


def deploy_errors(stage):
    """部署/运行日志里的错误；方案列表里列了但没装的方案（missing input schema）不算错。"""
    bad = []
    for log in Path(stage).glob('*ERROR*'):
        for line in log.read_text(errors='replace').splitlines():
            if line.startswith('E') and 'missing input schema' not in line:
                bad.append(line)
    return bad
