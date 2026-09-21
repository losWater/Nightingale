# -*- coding: utf-8 -*-
"""订正「曲」部件的拆分（2026-09-21 群友反馈）。默认预演，--apply 才落盘。

问题：曲 本字拆作「囗 ＋ 横 ＋ 丨 ＋ 丨」，但所有含曲的字都拆作「由 ＋ 丨」。
由 的竖出头、曲 的两竖不出头，两者不是一个部件，由＋丨 是错拆。
这是一处内部不一致：同一个部件在本字和合体字里拆法不同。

订正：把 24 个字里的「由 ＋ 丨」统一换成「囗 ＋ 横 ＋ 丨 ＋ 丨」，与曲本字一致。
已核对过没有别的写法的错拆（冂 ＋ 丨 ＋ 丨 是冊/刪，与曲无关）。

编码影响：夜莺只取首根与末根，曲在字中间的 22 个字编码不变；
只有曲在字首的 農、鄷 首根由 由(p) 变 囗(j)，这两个码位要另行走台账改主表。
"""
import io, sys, os, csv, shutil, datetime, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
SRC = {
    '通用规范': W + '/55_拆分继承核验/当前完整拆分表.txt',
    '扩展字': W + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt',
}
OLD, NEW = '由 ＋ 丨', '囗 ＋ 横 ＋ 丨 ＋ 丨'
APPLY = '--apply' in sys.argv[1:]
BK = H + '/备份'
print('订正：「%s」→「%s」\n' % (OLD, NEW))
report = []
for name, path in SRC.items():
    raw = open(path, encoding='utf-8-sig').read()
    lines = raw.split('\n')
    head = lines[0]
    cols = head.split('\t')
    try: ci = cols.index('完整拆分')
    except ValueError: sys.exit('%s 没有「完整拆分」列：%s' % (name, cols))
    hit = []
    out = [head]
    for l in lines[1:]:
        if not l: out.append(l); continue
        f = l.split('\t')
        if len(f) > ci and OLD in f[ci]:
            before = f[ci]; f[ci] = f[ci].replace(OLD, NEW)
            a0, a1 = before.split(' ＋ ')[0], before.split(' ＋ ')[-1]
            b0, b1 = f[ci].split(' ＋ ')[0], f[ci].split(' ＋ ')[-1]
            hit.append((f[0], before, f[ci], a0 != b0 or a1 != b1))
            out.append('\t'.join(f))
        else: out.append(l)
    print('── %s：%d 字命中' % (name, len(hit)))
    for t, b, a, chg in hit:
        print('   %-3s %s' % (t + ('*' if chg else ' '), a[:52]))
    report.append((name, path, raw, '\n'.join(out), hit))
    print()
chg = [(n, t) for n, _, _, _, h in report for t, _, _, c in h if c]
total = sum(len(h) for _, _, _, _, h in report)
print('合计 %d 字。带 * 的 %d 个首末根有变化：%s' % (total, len(chg), '、'.join(t for _, t in chg)))
print('（其余 %d 个字，曲在中间，首末根不变，编码不受影响）' % (total - len(chg)))
if total != 24:
    sys.exit('\n命中数不是预期的 24，停手。请先核对。')
if not APPLY:
    print('\n这是预演。确认后加 --apply 落盘。')
    sys.exit(0)
os.makedirs(BK, exist_ok=True)
stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
for name, path, raw, new, hit in report:
    bak = '%s/%s_%s_%s' % (BK, stamp, name, os.path.basename(path))
    shutil.copy2(path, bak)
    # 原文件带 BOM，写回时保持一致
    open(path, 'w', encoding='utf-8-sig', newline='').write(new)
    print('%s 已写入（备份 %s）' % (os.path.basename(path), os.path.basename(bak)))
    # 回读核对
    back = open(path, encoding='utf-8-sig').read()
    if OLD in back: sys.exit('回读仍含「%s」，异常！' % OLD)
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '替换': [OLD, NEW],
           '命中': {n: [h[0] for h in hh] for n, _, _, _, hh in report},
           '首末根变化': [t for _, t in chg]},
          open(H + '/订正记录.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n完成。接下来：農、鄷 的主表编码要走 00_维护/apply_ledger.py 改，然后跑 export.py。')
