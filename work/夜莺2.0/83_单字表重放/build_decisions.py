# -*- coding: utf-8 -*-
"""从既有批次表自动导出裁定文件（diff 形式）+ 无理码表。只读现有表，只写本目录。"""
import io, sys, os, json, glob, hashlib, shutil, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
B = 'E:/夜莺2.0/work/夜莺2.0'
R = B + '/54_补删鹿旁保留羊南心四起点试跑/二简人工复核'
H = os.path.dirname(os.path.abspath(__file__))
os.makedirs(H + '/起点', exist_ok=True)
os.makedirs(H + '/裁定', exist_ok=True)

def load(p):
    s = set()
    for l in open(p, encoding='utf-8-sig', errors='replace').read().splitlines():
        q = l.rstrip('\r').split('\t')
        if len(q) >= 2 and len(q[0]) == 1 and q[1].strip().isalpha():
            s.add((q[0], q[1].strip()))
    return s

def rd(p):
    try:
        return json.load(open(p, encoding='utf-8-sig'))
    except Exception:
        return None

def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()

# 起点
src = B + '/54_补删鹿旁保留羊南心四起点试跑/finalists/01_t1_projection/普通纯单字表.txt'
shutil.copy2(src, H + '/起点/普通纯单字表.txt')
json.dump({'来源': src.replace(B + '/', ''), 'sha256': sha(src), '条目': len(load(src))},
          open(H + '/起点/来源.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 链（旧→新），含撤回批
CHAIN = ['第一批已裁定', '第二批已裁定', '第三批已裁定_gs待定', '第三批已裁定', '第四批已裁定', '第五批已裁定',
         '第六批已裁定_lq待定', '第六批已裁定_six无理码_lq待定', '第六批已裁定', '第六批已裁定_赢字架移e', '第七批已裁定',
         '第八批已裁定_pg待定', '第八批已裁定', '第八批已裁定_q系调整', '第九批已裁定', '第十批已裁定_vj待定', '第十批已裁定',
         '第十一批已裁定', '第十二批已裁定', '第十三批_嗯en读音补全', '第十五批_ju四字容错', '第十六批_绪xv容错',
         '第十七批_yu五字容错', '第十八批_撤回于yv', '第十九批_正归止与焉三简', '第二十批_二简建议明确项', '第二十一批_简码任选项定稿']
WITHDRAWN = {'第十四批_二三简让位': '第十三批_嗯en读音补全'}

prev = load(src)
n = 0
for d in CHAIN:
    n += 1
    cur = load(R + '/' + d + '/普通纯单字表.txt')
    ops = [{'op': '删', '字': w, '码': c} for w, c in sorted(prev - cur)] + \
          [{'op': '加', '字': w, '码': c} for w, c in sorted(cur - prev)]
    rec = rd(R + '/' + d + '/裁定记录.json')
    json.dump({'序号': n, '批次': d, '状态': '生效', '来源目录': ('54_补删鹿旁保留羊南心四起点试跑/二简人工复核/' + d),
               '结果表sha256': sha(R + '/' + d + '/普通纯单字表.txt'), '操作': ops, '原裁定记录': rec},
              open(H + '/裁定/%02d_%s.json' % (n, d), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%02d %-30s 删%3d 加%3d' % (n, d, sum(o['op'] == '删' for o in ops), sum(o['op'] == '加' for o in ops)))
    prev = cur
for d, base in WITHDRAWN.items():
    cur = load(R + '/' + d + '/普通纯单字表.txt') if os.path.exists(R + '/' + d + '/普通纯单字表.txt') else set()
    basev = load(R + '/' + base + '/普通纯单字表.txt')
    ops = [{'op': '删', '字': w, '码': c} for w, c in sorted(basev - cur)] + [{'op': '加', '字': w, '码': c} for w, c in sorted(cur - basev)]
    json.dump({'序号': None, '批次': d, '状态': '已撤回', '撤回记录': rd(B + '/66_二三简兼占复核/撤回记录.json'),
               '本应基于': base, '操作': ops, '原裁定记录': rd(R + '/' + d + '/裁定记录.json')},
              open(H + '/裁定/撤回_%s.json' % d, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('撤回 %-30s （%d 项操作，重放时跳过）' % (d, len(ops)))

# 第二十二批：今天的单字改动 = 今早64备份 → 当前
old = load(B + '/74_简码让位实装/实装前备份/64_加入鲸凉鹤简词__夜莺2.0含简词字词表_普通格式.txt')
now = load(B + '/64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt')
ops = [{'op': '删', '字': w, '码': c} for w, c in sorted(old - now)] + [{'op': '加', '字': w, '码': c} for w, c in sorted(now - old)]
srcs = {k: rd(B + '/' + k + '/实装报告.json') for k in ('74_简码让位实装', '75_全码让位修复', '77_大佬清单笔误修正', '79_ve让位给着', '81_容错码字让位修正')}
srcs['74_简码让位实装/让位清单'] = rd(B + '/74_简码让位实装/让位清单.json')
json.dump({'序号': n + 1, '批次': '第二十二批_本日裁定', '状态': '生效', '日期': '2026-09-14',
           '说明': '简码让位32处、全码让位2处、笔误修正5码位、ve让位、居欲予绪；规则见 码表概念与规则.md',
           '操作': ops, '原始记录': srcs},
          open(H + '/裁定/%02d_第二十二批_本日裁定.json' % (n + 1), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('%02d %-30s 删%3d 加%3d' % (n + 1, '第二十二批_本日裁定', sum(o['op'] == '删' for o in ops), sum(o['op'] == '加' for o in ops)))

# 无理码表（附加物，规则脚本不读）
irr = {'容错码': {'jv': '剧', 'jvb': '居', 'jvn': '巨', 'jvo': '狙', 'xv': '绪', 'yvl': '欲', 'yvz': '予', 'yvc': '郁', 'yvo': '羽'},
       '特殊简码': {'eh': '鹤'}, '无理码': {'lqq': '六'},
       '来源': {'容错码': '54 第十五/十六/十七批 新增容错码.json；第十八批撤回 yv=于', '特殊简码': '57 历史盘点：小鹤系传统 eh=鹤，用户裁决',
              '无理码': '54 第六批裁定：取消 six，定 lqq=六，刘保留 lqe'},
       '性质': '码表成型后叠加；去掉全部后仍为规则完整码表；不参与任何规则判定'}
json.dump(irr, open(H + '/无理码表.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n无理码表：容错 %d + 特殊 %d + 无理 %d' % (len(irr['容错码']), len(irr['特殊简码']), len(irr['无理码'])))
