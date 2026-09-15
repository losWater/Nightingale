# -*- coding: utf-8 -*-
"""重放：起点 + 裁定（按序号，跳过已撤回）+ 无理码表核对 → 单字表。
冲突检测（有状态，随批次推进）先于写入：
  阻塞：删不存在的行 / 加已存在的行 / 同批重复操作 / 反转前批操作而未标 覆盖:true
  任一出现 → 全部列出并中止，不产出表。
输出与当前纯单字表逐条比对，差异必须为 0。"""
import io, sys, os, json, glob, hashlib, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__))
B = 'E:/夜莺2.0/work/夜莺2.0'

def load(p):
    s = set()
    for l in open(p, encoding='utf-8-sig', errors='replace').read().splitlines():
        q = l.rstrip('\r').split('\t')
        if len(q) >= 2 and len(q[0]) == 1 and q[1].strip().isalpha():
            s.add((q[0], q[1].strip()))
    return s

start = load(H + '/起点/普通纯单字表.txt')
files = sorted(glob.glob(H + '/裁定/*.json'))
batches = [json.load(open(f, encoding='utf-8')) for f in files]
active = sorted([b for b in batches if b.get('状态') == '生效'], key=lambda b: b['序号'])
skipped = [b['批次'] for b in batches if b.get('状态') != '生效']

# —— 有状态检测 ——
sim = set(start)
history = {}          # (字,码) -> (序号, 批次, op)
conflicts = []
covered = []          # 已标覆盖的反转（记录，不阻塞）
for b in active:
    n, name = b['序号'], b['批次']
    seen = collections.Counter((o['字'], o['码']) for o in b['操作'])
    for k, v in seen.items():
        if v > 1:
            conflicts.append({'批': name, '类型': '同批重复操作', '字': k[0], '码': k[1]})
    for o in b['操作']:
        key = (o['字'], o['码'])
        if o['op'] == '删' and key not in sim:
            conflicts.append({'批': name, '类型': '删除不存在的行', '字': o['字'], '码': o['码']})
        if o['op'] == '加' and key in sim:
            conflicts.append({'批': name, '类型': '添加已存在的行', '字': o['字'], '码': o['码']})
        prior = history.get(key)
        if prior and prior[2] != o['op']:
            item = {'批': name, '类型': '反转前批操作', '字': o['字'], '码': o['码'], '前批': '%s(%s)' % (prior[1], prior[2]), '备注': o.get('备注', '')}
            if o.get('覆盖'):
                covered.append(item)
            else:
                item['类型'] += '（未标覆盖）'
                conflicts.append(item)
        history[key] = (n, name, o['op'])
        if o['op'] == '删':
            sim.discard(key)
        else:
            sim.add(key)

print('裁定文件 %d 个：生效 %d，跳过（已撤回）%d → %s' % (len(batches), len(active), len(skipped), skipped))
print('阻塞冲突 %d；已标覆盖的反转 %d（放行）' % (len(conflicts), len(covered)))
for c in conflicts[:30]:
    print('   ✗', c)
if conflicts:
    json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '结果': '中止', '阻塞冲突': conflicts, '已覆盖反转': covered},
              open(H + '/核验报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n中止：存在阻塞冲突，未产出表。')
    sys.exit(1)

table = sim   # 检测通过，模拟结果即重放结果

irr = json.load(open(H + '/无理码表.json', encoding='utf-8'))
overlay = {(w, c) for grp in ('容错码', '特殊简码', '无理码') for c, w in irr[grp].items()}
missing = sorted(overlay - table)
core = table - overlay
full = collections.defaultdict(set)
for w, c in core:
    if len(c) >= 4:
        full[w].add(c)
bad_prefix = sorted((w, c) for w, c in core if len(c) < 4 and full[w] and not any(f.startswith(c) for f in full[w]))

cur = load(B + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt')
diff = sorted(table ^ cur)

out = H + '/重放结果_普通纯单字表.txt'
open(out, 'wb').write(('\r\n'.join('%s\t%s' % (w, c) for w, c in sorted(table, key=lambda x: (x[1], x[0]))) + '\r\n').encode('utf-8-sig'))
rep = {'时间': datetime.datetime.now().isoformat(timespec='seconds'),
       '结果': '通过' if not diff and not missing and not bad_prefix else '未通过',
       '起点条目': len(start), '生效批次': [b['批次'] for b in active], '跳过批次': skipped,
       '重放后条目': len(table), '与当前纯单字表差异': len(diff), '差异样例': ['%s%s' % x for x in diff[:20]],
       '无理码表缺失于结果': ['%s%s' % x for x in missing], '去无理码后非前缀短码': ['%s%s' % x for x in bad_prefix],
       '已覆盖的反转': covered, '输出sha256': hashlib.sha256(open(out, 'rb').read()).hexdigest()}
json.dump(rep, open(H + '/核验报告.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n重放后 %d 条；与当前纯单字表差异 %d；无理码缺失 %d；去无理码后非前缀短码 %d' % (len(table), len(diff), len(missing), len(bad_prefix)))
print('结果：', rep['结果'])
