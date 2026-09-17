# -*- coding: utf-8 -*-
"""入库排除规则（2026-09-16 你同意的原则：退火只版本化清单/报告/配置/入围者，原始运行输出、语料原件、引擎检查、
Rime 主力包与整句模型、所有"…备份"目录不入库；超过单文件上限的文件不入库并登记）。"""
import os, re
MAX_FILE = 20 * 1048576   # 仓库单文件上限（GitHub 硬限 100MB；超过 20MB 的中间产物一律不入库并登记）
# 目录名（任意层级）整目录排除
DIR_EXACT = {'jobs', 'round1', 'round2', 'configs', 'practice', 'raw', 'engine-check', 'engine-check-final', 'engine-check-light',
             'Rime_主力版', 'Rime_手机版', 'models', 'smoke', 'calibration', 'output', '__pycache__', '.candidate_check', 'node_modules', 'target',
             'upstream', '夜莺魔虎试验版'}   # 127：魔虎上游包（第三方 GPL 二进制与大词库）和由它生成的试验包不入库，build.py 可重建
DIR_RE = [(re.compile(r'备份'), '*备份*/'),                                  # 实装前备份_*、修改前备份、正式同步前备份…
          (re.compile(r'^\d\d_(projection|perturbed|random)$'), '[0-9][0-9]_projection/\n[0-9][0-9]_perturbed/\n[0-9][0-9]_random/'),   # 11 的运行目录
          (re.compile(r'^output-'), 'output-*/'),                             # 退火器单次运行输出（config/checkpoint/solution 各 5MB）
          ]
FILE_RE = [(re.compile(r'Rime主力版.*\.zip$'), '*Rime主力版*.zip'), (re.compile(r'Rime手机版.*\.zip$'), '*Rime手机版*.zip'), (re.compile(r'\.gram$'), '*.gram'), (re.compile(r'\.(log|pyc|tmp)$'), '*.log\n*.pyc\n*.tmp'), (re.compile(r'^~\$'), '~$*'),
           (re.compile(r'mohu-sentence-ngram.*\.bin$'), 'mohu-sentence-ngram*.bin'), (re.compile(r'\.exe$'), '*.exe'),
           (re.compile(r'^(checkpoint|solution)-.*\.yaml$'), 'checkpoint-*.yaml\nsolution-*.yaml'),          # 退火器解文件
           (re.compile(r'^(run|initial|final_config|feasible_start|repair|optimized)\.json$'), 'run.json\ninitial.json\nfinal_config.json\nfeasible_start.json\nrepair.json\noptimized.json'),   # 完整布局配置 6.8MB
           (re.compile(r'逐句按键\.json$'), '*逐句按键.json')]
# 白名单：脚本仍要读的个别文件（相对 work/夜莺2.0，/ 分隔），以及 frozen/finalists 下的一切（frozen/raw 语料原件除外）
KEEP_PATHS = {
    '54_补删鹿旁保留羊南心四起点试跑/jobs/t1_projection/final_config.json',   # 58/build.py 读根→键映射
    '52_均衡参数512方案正式晋级赛/jobs/g06_large_01/round2.json',              # 54/controller.py 读
}
KEEP_UNDER = ('frozen/', 'finalists/')
def excluded_dir(name):
    if name in DIR_EXACT: return name
    for r, _ in DIR_RE:
        if r.search(name): return '目录名含 ' + r.pattern
    return None
def excluded_file(name, size):
    for r, _ in FILE_RE:
        if r.search(name): return '文件名 ' + r.pattern
    if size > MAX_FILE: return '超过 %dMB' % (MAX_FILE // 1048576)
    return None
def dir_size(p):
    t = 0
    for dp, dn, fn in os.walk(p):
        for f in fn:
            try: t += os.path.getsize(os.path.join(dp, f))
            except OSError: pass
    return t
def walk_included(root):
    """返回 (入库 [(相对路径, 大小)], 排除 [(相对路径, 大小, 原因)])。相对路径用 / 分隔。"""
    inc = []; exc = []
    for dp, dn, fn in os.walk(root):
        rel = os.path.relpath(dp, root).replace('\\', '/'); rel = '' if rel == '.' else rel + '/'
        under_keep = any(('/' + rel).find('/' + k) >= 0 for k in KEEP_UNDER) and '/raw/' not in '/' + rel
        via_keep = rel and any(k.startswith(rel) for k in KEEP_PATHS) and any(excluded_dir(seg) for seg in rel.split('/') if seg)   # 只为取白名单文件而进入的被排除目录
        keep = []
        for d in dn:
            sub = rel + d + '/'
            if any(k.startswith(sub) for k in KEEP_PATHS): keep.append(d); continue
            if via_keep: exc.append((sub, dir_size(os.path.join(dp, d)), '目录 白名单目录中的其他子目录')); continue   # 身处被排除目录（只为白名单进来的），不再展开别的子目录
            w = excluded_dir(d)
            if w and not (under_keep and d != 'raw'): exc.append((sub, dir_size(os.path.join(dp, d)), '目录 ' + w))
            else: keep.append(d)
        dn[:] = keep
        for f in fn:
            p = os.path.join(dp, f)
            try: s = os.path.getsize(p)
            except OSError: continue
            if rel + f in KEEP_PATHS: inc.append((rel + f, s)); continue
            if via_keep: exc.append((rel + f, s, '白名单目录中的其他文件')); continue
            w = excluded_file(f, s)
            if under_keep and w and not w.startswith('文件名 \\.(log'): w = None
            (exc.append((rel + f, s, w)) if w else inc.append((rel + f, s)))
    return inc, exc
def gitignore_text():
    lines = ['# 由 116_仓库同步/rules.py 生成：与 E 盘同步脚本同一套排除规则，防止误加原始运行输出', '']
    for d in sorted(DIR_EXACT): lines.append('**/' + d + '/')
    for _, g in DIR_RE: lines += ['**/' + x for x in g.split('\n')]
    for _, g in FILE_RE: lines += g.split('\n')
    lines += ['', '# 白名单（脚本仍要读）'] + ['!/' + k for k in sorted(KEEP_PATHS)]
    lines += ['# frozen/finalists 下的解与配置保留'] + ['!**/' + k + '**' for k in KEEP_UNDER]
    return '\n'.join(lines) + '\n'
