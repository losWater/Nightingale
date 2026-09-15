"""Attach traceable reading inventories; never duplicate glyph frequency by reading."""
from pathlib import Path
from collections import defaultdict, Counter
import ast, csv, hashlib, html, json, re, unicodedata

P = Path(__file__).resolve().parent
W = P.parent
ROOT = W.parents[1]
def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))
def write(name, value):
    (P/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

# Reuse only the two pure parsing functions; do not execute historical rebuilds.
helper = W/'03_字音频率审计/rebuild.py'
tree = ast.parse(helper.read_text(encoding='utf-8-sig'))
scope = {'re': re, 'unicodedata': unicodedata}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('double_code', 'syllable')], type_ignores=[]), str(helper), 'exec'), scope)
dc, norm = scope['double_code'], scope['syllable']
source = P/'试验整字频率.json'
basepath = W/'27_删利根参数0晋级赛/frozen/字音基准.json'
auditpath = W/'03_字音频率审计/分读音字频_审计版.tsv'
wordpath = W/'08_词库与词频重建/二字词60000_鲸凉鹤补全后.jsonl'
lexpath = ROOT/'repos/webchai/packages/hanzi-chai/src/data/dictionary.txt'
rulepath = ROOT/'work/重开工程/03_字音频率/特殊优化权重裁决.json'
src = read(source)
core = {r['字'] for r in src['字表']}
inventory = defaultdict(dict)
def add(ch, py, label, example=None):
    py = norm(py)
    if ch not in core or not re.fullmatch('[a-z]+', py):
        return
    item = inventory[ch].setdefault(py, {'拼音': py, '小鹤双拼': dc(py), '来源': [], '例词': [], '新分音频率': None})
    if label not in item['来源']:
        item['来源'].append(label)
    if example and example not in item['例词'] and len(item['例词']) < 5:
        item['例词'].append(example)
    return item

for r in read(basepath):
    item = add(r['字'], r['拼音'], '现有方案字音集合')
    assert item is not None
    if item['小鹤双拼'] != r['音码']:
        item['音码说明'] = '沿用冻结方案特殊音码；通用转换未覆盖'
        item['小鹤双拼'] = r['音码']
    item['旧表已分配频次'] = r['频率']
with auditpath.open(encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        item = add(r['汉字'], r['拼音'], '字音审计表')
        item['旧表该字待分配频次'] = int(r['该字待分配频率'])
        item['旧表其中历史单字裁决'] = int(r['其中历史单字裁决'])
        item['旧表状态'] = r['状态']

# Lexicon additions are candidates, not automatic new scheme readings.
with lexpath.open(encoding='utf-8-sig') as f:
    for line in f:
        parts = line.rstrip('\n').split('\t')
        if len(parts) > 1 and len(parts[0]) == 1 and len(parts[1].split()) == 1:
            add(parts[0], parts[1], 'Chai单字词典候选')
with wordpath.open(encoding='utf-8-sig') as f:
    for line in f:
        r = json.loads(line)
        py = r.get('主读音') or r.get('采用拼音')
        if not py or len(py.split()) != len(r['词']):
            continue
        for ch, sy in zip(r['词'], py.split()):
            add(ch, sy, '08词库读音候选（含鲸凉鹤补全）', r['词'] + '：' + py)

rows = []
new_readings = []
for original in src['字表']:
    r = dict(original)
    readings = sorted(inventory[r['字']].values(), key=lambda x: ('现有方案字音集合' not in x['来源'], -x.get('旧表已分配频次', 0), x['拼音']))
    assert readings
    for item in readings:
        item['状态'] = '沿用方案读音' if '现有方案字音集合' in item['来源'] else '新增候选，待核后再进入方案'
        if item['状态'].startswith('新增'):
            new_readings.append({'字': r['字'], '整字排名': r['新排名'], **item})
    r['读音信息'] = readings
    r['读音数（含候选）'] = len(readings)
    r['分音状态'] = '尚未分配；各音频率为空，不能当作零频'
    r['未分配到读音的每百万字次数'] = r['每百万核心字预计次数']
    if r['字'] == '谁':
        r['特殊优化规则说明'] = '既有规则：shei/uw不参与竞争，优化权重0；shui/uv取整字频率的1/4。这是退火权重规则，不是自然读音比例；本次仅记录，未应用。'
    rows.append(r)

assert len(rows) == len(core) == 8105
assert [r['每百万核心字预计次数'] for r in rows] == [r['每百万核心字预计次数'] for r in src['字表']]
assert abs(sum(r['每百万核心字预计次数'] for r in rows)-1e6) < 1e-6
assert all(item['新分音频率'] is None for r in rows for item in r['读音信息'])
summary = {'整字数': len(rows), '正频字数': sum(r['每百万核心字预计次数'] > 0 for r in rows), '方案原有字音项': sum('现有方案字音集合' in a['来源'] for r in rows for a in r['读音信息']), '候选补充字音项': len(new_readings), '含多个读音或候选的字': sum(len(r['读音信息']) > 1 for r in rows), '缺少读音字数': 0, '整字频率逐项保持': True, '分音频率状态': '未分配（null，不是0）', '频率合计': sum(r['每百万核心字预计次数'] for r in rows), '无法编码候选': [{'字': r['字'], '拼音': a['拼音']} for r in rows for a in r['读音信息'] if not a['小鹤双拼']]}
write('带音字频核验.json', {**summary, '输入SHA256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (source, basepath, auditpath, wordpath, lexpath, rulepath, helper)}})
write('试验整字频率_带音.json', {'状态': '读音标注版；不是可直接替换退火的分音字频表', '注音口径': '无声调完整音节；ü使用v；小鹤双拼沿用现有转换规则。候选显示不代表已裁定。', '权重': src['权重'], '统计': summary, '特殊优化规则原件': read(rulepath), '字表': rows})
write('补充读音候选.json', new_readings)
def display(r):
    return ' / '.join(a['拼音'] + '(' + (a['小鹤双拼'] or '未编码') + ')' + ('[候选]' if a['状态'].startswith('新增') else '') for a in r['读音信息'])
with (P/'试验整字频率_带音.txt').open('w', encoding='utf-8') as f:
    f.write('字\t新排名\t每百万核心字预计次数（整字）\t拼音及小鹤双拼\t分音状态\n')
    for r in rows:
        f.write(f"{r['字']}\t{r['新排名']}\t{r['每百万核心字预计次数']:.8f}\t{display(r)}\t未分配\n")

esc = lambda x: html.escape(str(x))
page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>多来源字频 · 读音信息</title><style>body{font:16px/1.7 system-ui;background:#f4f7fb;color:#234;margin:24px}main{max-width:1300px;margin:auto}table{border-collapse:collapse;background:white;width:100%}td,th{border:1px solid #ccd;padding:9px;text-align:left}th{background:#dce9f3;position:sticky;top:0}input,button{font:inherit;padding:8px}small{color:#586879}.wrap{overflow:auto}.note{background:#fff3cf;padding:16px}</style><main><h1>多来源字频 · 读音信息</h1><p>保留新整字频率及排名，列出拼音、小鹤双拼与来源。拼音不带声调，ü写作v。</p><p class="note">频率一字只计一次，不重复分给每个音。各音的新频率尚未分配；旧频次仅作证据参考，不按旧比例直接套用。新增读音候选需要核对，不自动进入方案。即便只有一个列出读音，也不据此宣称没有其他读音。</p>'''
page += '<p>' + esc('；'.join(f'{k}：{v}' for k, v in summary.items() if k in ('整字数', '方案原有字音项', '候选补充字音项', '含多个读音或候选的字', '缺少读音字数'))) + '</p>'
page += '<p>谁：保留shei/uw、shui/uv。“shui取整字频率四分之一”是独立优化规则，不是读音频率分配。本次未运行退火。</p><p><a href="试验整字频率_带音.txt">下载带音TXT</a> · <a href="试验整字频率_带音.json">完整来源JSON</a></p><input id="q" placeholder="查字、拼音或双拼" aria-label="查字、拼音或双拼"><label><input id="multi" type="checkbox">仅看多个读音／候选</label><p id="count"></p><div class="wrap"><table><thead><tr><th>排名</th><th>字</th><th>每百万字（整字）</th><th>拼音／双拼</th><th>来源与例词</th></tr></thead><tbody>'
for r in rows:
    details = '<details><summary>查看读音证据</summary>' + ''.join('<p><b>'+esc(a['拼音'])+'</b> '+esc(a['状态'])+'<br>'+esc('；'.join(a['来源']))+'<br><small>'+esc('；'.join(a['例词']))+('<br>旧字幕审计已分配频次：'+esc(a['旧表已分配频次']) if '旧表已分配频次' in a else '')+'</small></p>' for a in r['读音信息'])+'</details>'
    page += '<tr data-multi="'+str(int(len(r['读音信息']) > 1))+'" data-search="'+esc(r['字']+' '+display(r))+'"><td>'+str(r['新排名'])+'</td><td>'+esc(r['字'])+'</td><td>'+f"{r['每百万核心字预计次数']:.4f}"+'</td><td>'+esc(display(r))+'</td><td>'+details+'</td></tr>'
page += '''</tbody></table></div></main><script>const q=document.getElementById('q'),m=document.getElementById('multi'),c=document.getElementById('count');function filter(){let n=0;document.querySelectorAll('tbody tr').forEach(r=>{r.hidden=!(r.dataset.search.includes(q.value.trim().toLowerCase())&&(!m.checked||r.dataset.multi==='1'));if(!r.hidden)n++});c.textContent='显示 '+n+' 字'}q.oninput=filter;m.onchange=filter;filter();</script></html>'''
(P/'带音字频表.html').write_text(page, encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False))
