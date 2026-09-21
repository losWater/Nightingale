# -*- coding: utf-8 -*-
"""把「曲」补登记进人工规则表（2026-09-21）。默认预演，--apply 落盘。

曲 当初没被登记，所以 140 的传播审计抓不到它——那 24 个错拆是靠群友反馈发现的。
补登记之后，以后任何一次审计都会把「由 ＋ 丨」这个旧形式当作应撤销项来查，
不会再出现"改了本字忘了全族"的情况。
写进 重开工程/02_规范拆分/正式历史结构裁决规则.yaml 的 guarded_rewrites，
格式与既有 27 条一致：expected_before / canonical_after / decision_at / reason。
"""
import io, sys, os, shutil, datetime, yaml
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
P = os.path.dirname(W) + '/重开工程/02_规范拆分/正式历史结构裁决规则.yaml'
APPLY = '--apply' in sys.argv[1:]
KEY = '曲'
NEW = {
    'expected_before': ['由', '丨'],
    'canonical_after': ['囗', '横', '丨', '丨'],
    'decision_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M +10:00'),
    'reason': ('由 的竖出头、曲 的两竖不出头，不是同一个部件；由＋丨 是错拆。'
               '曲 本字一直是 囗＋横＋丨＋丨，但 24 个含曲的字沿用了 由＋丨，'
               '属于本字改对、全族未跟上。2026-09-21 群友反馈后统一订正，'
               '補登记本条以便传播审计覆盖。'),
}
d = yaml.safe_load(open(P, encoding='utf-8'))
gr = d.setdefault('guarded_rewrites', {})
print('%s 现有 guarded_rewrites %d 条' % (os.path.basename(P), len(gr)))
if KEY in gr:
    print('  「%s」已登记：%s' % (KEY, gr[KEY])); sys.exit(0)
print('  将新增「%s」：%s → %s' % (KEY, ' ＋ '.join(NEW['expected_before']), ' ＋ '.join(NEW['canonical_after'])))
gr[KEY] = NEW
if not APPLY:
    print('\n这是预演。确认后加 --apply 落盘。')
    sys.exit(0)
stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
os.makedirs(H + '/备份', exist_ok=True)
shutil.copy2(P, '%s/备份/%s_正式历史结构裁决规则.yaml' % (H, stamp))
with open(P, 'w', encoding='utf-8') as f:
    yaml.safe_dump(d, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=100)
back = yaml.safe_load(open(P, encoding='utf-8'))
assert back['guarded_rewrites'][KEY]['canonical_after'] == NEW['canonical_after'], '回读不一致'
print('  已写入，guarded_rewrites 现有 %d 条（备份已存）' % len(back['guarded_rewrites']))
