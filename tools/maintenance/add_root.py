"""Apply an explicitly reviewed root-family plan; preview by default, never recode tables."""
import argparse
from collections import defaultdict
import csv
import datetime
import hashlib
import html
import io
import json
from pathlib import Path
import re
import shutil

from context import load, atomic
from export import extract_json
from edit_split import replace_json
from apply_ledger import FIELDS, load as read_table
from semantics import full_codes, metadata


def transform(page, plan, table, full):
    views = extract_json(page, 'views')
    data = extract_json(views['query'], 'D')
    root = plan['root']
    name, key, group = (root[k] for k in ('根', '键', '组'))
    if not re.fullmatch('[a-z]', key) or not name or any(c in name for c in '+＋\t\n'):
        raise ValueError('无效字根')
    roots = extract_json(views['query'], 'ROOTS')
    if any(r['根'] == name for r in roots):
        raise ValueError('字根已存在，拒绝重复应用')
    if not any(r['键'] == key and r['组'] == group for r in roots):
        raise ValueError('须归并到已有同键字根组')
    sequence = plan['replace_sequence']
    if not sequence:
        raise ValueError('缺少旧拆分序列')
    hits = {}
    for char, entry in data.items():
        names = [r['根'] for r in entry['根']]
        positions = [i for i in range(len(names)-len(sequence)+1)
                     if names[i:i+len(sequence)] == sequence]
        if positions:
            hits[char] = positions
    if set(hits) != set(plan['characters']):
        raise ValueError('扫描结果与人工批准字集不一致：'+str(sorted(hits)))
    changes = []
    for char, positions in hits.items():
        entry = data[char]
        old = entry['新拆']
        for i in reversed(positions):
            entry['根'][i:i+len(sequence)] = [dict(root)]
        entry['新拆'] = ' ＋ '.join(r['根'] for r in entry['根'])
        expected = entry['根'][0]['键'] + entry['根'][-1]['键']
        codes = [c for (t, _), cs in full.items() if t == char for c in cs]
        if not codes or any(c[2:] != expected for c in codes):
            raise ValueError('请先通过台账核实并改码：'+char)
        changes.append((char, old, entry['新拆']))
    # Refresh only affected code displays, including former collision partners.
    slots = defaultdict(list)
    by_char = defaultdict(list)
    for char, code in table:
        slots[code].append(char)
        by_char[char].append(code)
    touched = {c for char in hits for c in by_char[char]}
    touched.update(x['码'] for char in hits for x in data[char]['编码'])
    for char, entry in data.items():
        if char in hits or any(x['码'] in touched for x in entry['编码']):
            entry['编码'] = [{'码': c, '位': slots[c].index(char)+1, '同码': slots[c]}
                             for c in by_char[char]]
    roots.append(dict(root))
    for view in ('query', 'components'):
        views[view] = replace_json(replace_json(views[view], 'D', data), 'ROOTS', roots)
    rows = extract_json(views['text'], 'rows')
    for row in rows:
        if row[0] in hits:
            entry = data[row[0]]
            row[1:] = [entry['新拆'], entry['根'][0]['根'], entry['根'][-1]['根']]
    views['text'] = replace_json(views['text'], 'rows', rows)
    practice_roots = extract_json(views['practice'], 'roots')
    examples = '、'.join(plan['examples'])
    practice_roots.append({**root, '例字': examples})
    views['practice'] = replace_json(views['practice'], 'roots', practice_roots)
    practice_examples = extract_json(views['practice'], 'rootExamples')
    for existing, levels in practice_examples.items():
        for level, items in levels.items():
            kept = []
            for item in items:
                if item['字'] in hits:
                    entry = data[item['字']]
                    if existing not in [r['根'] for r in entry['根']]:
                        continue
                    item['拆分'] = entry['新拆']
                kept.append(item)
            levels[level] = kept
    new_examples = []
    for char in plan['examples']:
        entry = data[char]
        pos = '首根' if entry['根'][0]['根'] == name else '末根' if entry['根'][-1]['根'] == name else '中间根'
        new_examples.append({'字': char, '位置': pos, '拆分': entry['新拆']})
    practice_examples[name] = {str(n): new_examples[:n] for n in (1, 2, 4)}
    views['practice'] = replace_json(views['practice'], 'rootExamples', practice_examples)
    row = '<tr>' + ''.join('<td>'+html.escape(s)+'</td>' for s in (key, name, group, examples)) + '</tr>'
    if views['roots'].count('</tbody>') != 1:
        raise ValueError('字根表结构变化')
    views['roots'] = views['roots'].replace('</tbody>', row+'</tbody>')
    marker = '<dt>'+html.escape(group)+'</dt><dd>'
    if views['image'].count(marker) != 1:
        raise ValueError('字根图分组结构变化')
    views['image'] = views['image'].replace(marker, marker+html.escape(name)+'、')
    pattern = r'(data-search="'+re.escape(key)+r' [^"]*)(")'
    views['image'], count = re.subn(pattern, lambda m: m[1]+' '+html.escape(name)+m[2], views['image'])
    if count != 1:
        raise ValueError('字根图搜索结构变化')
    return replace_json(page, 'views', views), changes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan', type=Path)
    p.add_argument('--root')
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    _, active, _ = load(args.root, writable=args.apply)
    plan = json.loads(args.plan.read_text())
    source = active/'资料/拆分原本.html'
    ledger = active/'记录/修改台账.tsv'
    original, ledger_bytes = source.read_bytes(), ledger.read_bytes()
    table = read_table(active/'主表/单字表.txt')
    updated, changes = transform(original.decode('utf-8-sig'), plan, table, full_codes(table, metadata(active)))
    updated = updated.encode('utf-8-sig')
    print(json.dumps(changes, ensure_ascii=False, indent=2))
    if not args.apply:
        print('预演通过，未写入。'); return
    now = datetime.datetime.now().astimezone()
    batch = 'ROOT-'+now.strftime('%Y%m%d%H%M%S%f')
    rows = list(csv.DictReader(io.StringIO(ledger_bytes.decode('utf-8-sig')), delimiter='\t'))
    records = [('新增字根', '', plan['root']['根'], json.dumps(plan['root'], ensure_ascii=False))]
    records += [('改拆分', char, char, old+' → '+new) for char, old, new in changes]
    for i, (op, old, new, note) in enumerate(records, 1):
        row = dict.fromkeys(FIELDS, '')
        row.update({'问题ID': f'{batch}-{i:02}', '原文摘录': plan['reason'], '状态': '已修复',
                    '目标码表': '拆分原本', '操作': op, '原字词': old, '新字词': new,
                    '备注': note, '处理时间': now.isoformat(timespec='seconds'),
                    '处理结果': '同步查询、部件反查、字根练习、字根表、字根图、完整拆分表；未部署',
                    '修改前SHA256': hashlib.sha256(original).hexdigest(),
                    '修改后SHA256': hashlib.sha256(updated).hexdigest()})
        rows.append(row)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=FIELDS, delimiter='\t', lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
    if source.read_bytes() != original or ledger.read_bytes() != ledger_bytes:
        raise ValueError('文件发生并发修改')
    backup = active/'备份'/batch
    backup.mkdir(parents=True)
    for path in (source, ledger):
        shutil.copy2(path, backup/path.name)
    try:
        atomic(source, updated)
        atomic(ledger, out.getvalue().encode())
    except Exception:
        atomic(source, original); atomic(ledger, ledger_bytes); raise
    print('已备份并记录；未部署。')


if __name__ == '__main__':
    main()
