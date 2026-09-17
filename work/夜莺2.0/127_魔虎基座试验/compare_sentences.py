# -*- coding: utf-8 -*-
"""同一批整句，试验版（魔虎新模型）对 现主力版（106 engine-check-final/main）。只看首选。"""
import io, sys, os, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
S = [('今天天气不错想出去散步', 'jbtmtmqibucoxliuqusjbu'), ('你可以帮我把这个文件发过来吗', 'nikeyibhwobavegewfjmfagoldma'), ('夜莺输入法是一个音形方案', 'yeykuurufauiyigeybxkfhan'),
     ('我们明天上午九点在公司开会', 'womfmktmuhwujqdmzdgssikdhv'), ('这个问题我已经反馈给作者了', 'vegewftiwoyijkfjkvgwzovele'), ('他说的话我一句也没听懂', 'tauodehxwoyijuyemwtkds'),
     ('现在的年轻人压力都很大', 'xmzddenmqkrfyalidzhfda'), ('麻烦把实战反馈整理一下', 'mafjbauivjfjkvvgliyixx'), ('晚上要不要一起去吃火锅', 'wjuhycbuycyiqiquiihogo'), ('输入法的词库需要经常维护', 'uurufadecikuxuycjkihwwhu')]
def run(user, schema):
    p = subprocess.run(['D:/nightingale/.tmp/rime_bench.exe', 'D:/Rime/weasel-0.17.4', 'D:/Rime/weasel-0.17.4/data', user, schema], input=('\n'.join(c for _, c in S) + '\n').encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=900)
    assert p.returncode == 0, (user, p.returncode, p.stderr[-500:])
    return [l.split('\t') for l in p.stdout.decode('utf-8').splitlines()]
new = run('E:/ymt', 'yeying_flypy')
subprocess.run(['subst', 'Y:', '/D'], capture_output=True); subprocess.run(['subst', 'Y:', (W + '/106_全平台导出/engine-check-final/main').replace('/', '\\')], check=True)
try: old = run('Y:/', 'yeying20_main')
finally: subprocess.run(['subst', 'Y:', '/D'])
a = b = 0
for (want, code), n, o in zip(S, new, old):
    a += n[3] == want; b += o[3] == want
    print('%s\n   试验版 %s %s  [%sms]\n   现主力 %s %s  [%sms]' % (want, '✓' if n[3] == want else '✗', n[3], n[1][:5], '✓' if o[3] == want else '✗', o[3], o[1][:5]))
print('首选全对：试验版 %d/%d，现主力 %d/%d' % (a, len(S), b, len(S)))
