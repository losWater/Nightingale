# -*- coding: utf-8 -*-
"""夜莺 2.0 一条命令重建（2026-09-17，仿 1.0 的 pipelines/v09/rebuild.py：真源改完只记一个命令）。
用 PowerShell 运行（引擎核验程序依赖 PowerShell 的 PATH）：
    python E:\\夜莺2.0\\work\\夜莺2.0\\00_维护\\rebuild.py            # 码表链：83→78→109→97→102→103→104→110→112→113，逐步过关卡
    python ...\\rebuild.py --export                                  # 再加：106 导出+引擎核验+打包、114/115 工具箱、123 虎娘、125 码圈、127 魔虎试验版
    python ...\\rebuild.py --export --deploy                         # 再加：更新本机小狼毫与虎娘
    python ...\\rebuild.py --export --release                        # 再加：117 发布目录、118 官网数据（git 提交与 Release 上传仍手动，属对外动作）
任何一步关卡不过即停，不往下跑。每次运行在 00_维护/重建记录.jsonl 追加一行（时间、各步结论、最终表条数与 SHA256）。"""
import sys
if '--我知道已封存' not in sys.argv: sys.exit('生成链已于 2026-09-17 封存：主表冻结后不再从 83→113 重新生成。维护请用 apply_ledger.py，导出请用 export.py。')
import io, os, re, json, subprocess, hashlib, datetime, shutil, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H); A = set(sys.argv[1:]); log = []
ENV = dict(os.environ, PYTHONIOENCODING='utf-8')
def step(name, script, gates=(), cwd=None, show=1):
    t = time.time(); p = subprocess.run([sys.executable, script], cwd=cwd or os.path.dirname(script), env=ENV, capture_output=True)
    out = p.stdout.decode('utf-8', 'replace'); ok = p.returncode == 0 and all(re.search(g, out) for g in gates)
    lines = [l for l in out.strip().splitlines() if l.strip()]
    print('%s %-14s %5.1fs  %s' % ('✓' if ok else '✗', name, time.time() - t, ' | '.join(l.strip()[:150] for l in lines[-show:])))
    log.append({'步': name, '过': ok})
    if not ok:
        print('\n'.join(lines[-25:])); print(p.stderr.decode('utf-8', 'replace')[-2000:]); finish(False); sys.exit(1)
def finish(ok):
    f = W + '/113_扩展字入表/夜莺2.0最终表_普通格式.txt'; d = open(f, 'rb').read()
    json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '参数': sorted(A), '结果': '通过' if ok else '中止', '步骤': log, '最终表条数': d.count(b'\n'), '最终表sha256': hashlib.sha256(d).hexdigest()},
              open(H + '/重建记录.jsonl', 'a', encoding='utf-8'), ensure_ascii=False); open(H + '/重建记录.jsonl', 'a', encoding='utf-8').write('\n')
# 登记一致性关卡：补音批次里的全码必须都在补音表里（防止"补了音却没登记"再次发生）
reg = json.load(open(W + '/83_单字表重放/补音表.json', encoding='utf-8'))['条目']; miss = []
for fn in sorted(os.listdir(W + '/83_单字表重放/裁定')):
    if not fn.endswith('.json'): continue
    b = json.load(open(W + '/83_单字表重放/裁定/' + fn, encoding='utf-8'))
    if b.get('类别') == '补音' and b.get('状态') == '生效':                       # 批次文件里显式标记，不靠文件名猜
        for o in b['操作']:
            if o['op'] == '加' and len(o['码']) == 4 and o['字'] not in reg.get(o['码'], []): miss.append(o['字'] + o['码'])
assert not miss, '补音批次里有未登记到 补音表.json 的：%s' % miss
step('83 重放', W + '/83_单字表重放/replay.py', [r'结果：\s*通过'])
step('补音字次序', H + '/order_buyin.py')
step('78 核验', W + '/78_纯单字表核验/audit.py', [r'完整表[^\n]*未通过 0 项', r'去容错码版[^\n]*未通过 0 项'], show=3)
step('109 普通词', W + '/109_普通词共识筛选/build.py', show=1)
step('97 字词合并', W + '/97_字词合并/build.py', [r'补音字让位生效'])
step('102 二字简词', W + '/102_二字简词/build.py', show=2)
step('103 三字词', W + '/103_三字词三码/build.py', show=2)
step('104 简词入表', W + '/104_简词入表/build.py', [r'自检通过'])
step('110 词序投票', W + '/110_词序三家投票/build.py', [r'自检通过'])
step('112 扩展字', W + '/112_扩展字继承/build.py')
step('113 最终表', W + '/113_扩展字入表/build.py', [r'自检通过'])
if '--export' in A:
    P = W + '/106_全平台导出'
    if os.path.isdir(P + '/engine-check-final'): shutil.rmtree(P + '/engine-check-final')      # 106 自己生成的核验目录
    step('106 导出', P + '/build.py'); step('106 核验', P + '/verify.py', [r'main PASS', r'light PASS', r'mobile PASS'], show=4); step('106 打包', P + '/package.py', show=3)
    step('114 工具箱', W + '/114_工具箱同步扩展字/sync.py'); step('115 练习例字', W + '/115_练习例字补扩展字/sync.py')
    step('123 虎娘', W + '/123_虎娘导入/build.py'); step('125 码圈', W + '/125_码圈交付/build.py'); step('127 魔虎试验版', W + '/127_魔虎基座试验/build.py')
if '--deploy' in A:
    step('本机部署', H + '/deploy_local.py', [r'0 failure', r'tigirl update exit: 0'], show=3)
if '--release' in A:
    step('117 发布目录', W + '/117_发布v2.0/build_release.py'); step('118 官网数据', W + '/118_官网2.0/compute_performance.py'); step('118 同步官网', W + '/118_官网2.0/sync_to_repo.py')
finish(True); print('全部通过。')
