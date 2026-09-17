# -*- coding: utf-8 -*-
"""第二步：只读两张主表，生成全部输入法兼容格式与周边产物。纯固定脚本，不改主表。用 PowerShell 运行：
    python export.py                 # 体检 → 码前镜像 → 106 导出/引擎核验/打包 → 114/115 工具箱 → 123 虎娘 → 125 码圈 → Rime 主力版（127，魔虎基座：生成/引擎核验/打包）
    python export.py --deploy        # 再更新本机小狼毫与虎娘
    python export.py --release       # 再组装 117 发布目录、118 官网数据（git 提交与 Release 上传属对外动作，仍手动）
关卡：主表结构体检不过、任何一步失败即停。规则体检（78 的 14 项）只报告不拦——人工裁定可以高于规则，由你看报告决定。
运行前后校验两张主表的 SHA256 未变（保证本步只读）。每次运行在 导出记录.jsonl 追加一行。"""
import io, sys, os, re, json, subprocess, hashlib, datetime, shutil, time, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H); A = set(sys.argv[1:]); log = []
M = {'单字表': H + '/主表/夜莺2.0单字表.txt', '字词表': H + '/主表/夜莺2.0字词表.txt'}; ENV = dict(os.environ, PYTHONIOENCODING='utf-8')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(); start = {n: sha(p) for n, p in M.items()}
def finish(ok):
    open(H + '/导出记录.jsonl', 'a', encoding='utf-8').write(json.dumps({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '参数': sorted(A), '结果': '通过' if ok else '中止', '主表sha256': start, '步骤': log}, ensure_ascii=False) + '\n')
def step(name, cmd, gates=(), show=1, gate=True):
    t = time.time(); p = subprocess.run([sys.executable] + cmd, cwd=os.path.dirname(cmd[0]), env=ENV, capture_output=True)
    out = p.stdout.decode('utf-8', 'replace'); ok = p.returncode == 0 and all(re.search(g, out) for g in gates); lines = [l for l in out.strip().splitlines() if l.strip()]
    print('%s %-12s %5.1fs  %s' % ('✓' if ok else ('✗' if gate else '！'), name, time.time() - t, ' | '.join(l.strip()[:140] for l in lines[-show:]))); log.append({'步': name, '过': ok})
    if not ok and gate: print('\n'.join(lines[-25:])); print(p.stderr.decode('utf-8', 'replace')[-2000:]); finish(False); sys.exit(1)
    return ok, lines
# 0 主表结构体检（与 apply_ledger 同一套）+ 派生镜像
sys.path.insert(0, H)
rows = {n: [tuple(l.split('\t')) for l in open(p, encoding='utf-8').read().split('\n') if l] for n, p in M.items()}
def checkup(tabs):
    bad = []
    for n, r in tabs.items():
        if len(r) != len(set(r)): bad.append(n + ' 有重复行')
        if any(len(x) != 2 or not x[0] or not x[1] for x in r): bad.append(n + ' 有空字段')
    a = collections.defaultdict(list); b = collections.defaultdict(list)
    for t, c in tabs['单字表']: a[c].append(t)
    for t, c in tabs['字词表']:
        if len(t) == 1: b[c].append(t)
    d = sorted(c for c in set(a) | set(b) if a.get(c) != b.get(c))
    if d: bad.append('两表单字不一致 %d 个码位，如 %s' % (len(d), d[:8]))
    return bad
bad = checkup(rows); print('%s 主表结构体检  单字表 %d 行，字词表 %d 行  %s' % ('✗' if bad else '✓', len(rows['单字表']), len(rows['字词表']), '；'.join(bad)))
if bad: finish(False); sys.exit(1)
D = H + '/派生'; os.makedirs(D, exist_ok=True)
open(D + '/夜莺2.0字词表_码前.txt', 'wb').write(('\r\n'.join('%s\t%s' % (c, t) for t, c in rows['字词表']) + '\r\n').encode('utf-8-sig'))
ext = {l.split('\t')[0] for l in open(W + '/112_扩展字继承/夜莺2.0扩展字表_普通格式.txt', encoding='utf-8-sig') if l.strip()}
open(D + '/规则体检用_8105单字表.txt', 'wb').write(('\r\n'.join('%s\t%s' % r for r in rows['单字表'] if r[0] not in ext) + '\r\n').encode('utf-8-sig'))
ok, lines = step('规则体检', [W + '/78_纯单字表核验/audit.py', D + '/规则体检用_8105单字表.txt'], [r'完整表[^\n]*未通过 0 项'], show=3, gate=False)
if not ok: print('   （只报告不拦。详情：python 78_纯单字表核验/audit.py 00_维护/派生/规则体检用_8105单字表.txt）')
P = W + '/106_全平台导出'
if os.path.isdir(P + '/engine-check-final'): shutil.rmtree(P + '/engine-check-final')      # 106 自己生成的核验目录
step('106 导出', [P + '/build.py']); step('106 引擎核验', [P + '/verify.py'], [r'main PASS', r'light PASS', r'mobile PASS'], show=4); step('106 打包', [P + '/package.py'], show=3)
step('114 工具箱', [W + '/114_工具箱同步扩展字/sync.py']); step('115 练习例字', [W + '/115_练习例字补扩展字/sync.py'])
step('123 虎娘', [W + '/123_虎娘导入/build.py']); step('125 码圈', [W + '/125_码圈交付/build.py']); 
M7 = W + '/127_魔虎基座试验'   # Rime 主力版「夜莺主力」（魔虎基座；数据取自上面 106 的中间产物）
step('主力版 生成', [M7 + '/build.py']); step('主力版 引擎核验', [M7 + '/verify.py'], [r'main PASS'], show=2); step('主力版 打包', [M7 + '/package.py'])
if '--deploy' in A: step('本机部署', [H + '/deploy_local.py'], [r'0 failure', r'tigirl update exit: 0'], show=3)
if '--release' in A:
    step('117 发布目录', [W + '/117_发布v2.0/build_release.py']); step('118 官网数据', [W + '/118_官网2.0/compute_performance.py']); step('118 同步官网', [W + '/118_官网2.0/sync_to_repo.py'])
assert {n: sha(p) for n, p in M.items()} == start, '主表在导出过程中被改动了！'
finish(True); print('全部通过；两张主表未被改动。')
