"""汇总 Rime 里 NB46 单字试用的手动调频记录（~/Library/Rime/yeying_tune_adjust.tsv）。
输出：每个调过的码最终的首选顺序、调整次数、原来排第几；按调整次数排序。
用法：python release/summarize_adjust.py [记录文件]"""
import sys, collections
from pathlib import Path
path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'Library/Rime/yeying_tune_adjust.tsv'
if not path.exists():
    sys.exit(f'还没有记录：{path}')
order, times, first_pos = {}, collections.Counter(), {}
for line in path.read_text(encoding='utf-8').splitlines():
    p = line.split('\t')
    if len(p) != 5:
        continue
    t, code, text, pos, act = p
    if act == 'reset':
        order.pop(code, None); continue
    l = [x for x in order.get(code, []) if x != text]
    order[code] = [text] + l
    times[code] += 1
    first_pos.setdefault((code, text), pos)
print(f'记录文件：{path}；调过 {len(order)} 个码')
for code in sorted(order, key=lambda c: -times[c]):
    print(f'{code}\t调整{times[code]}次\t现首选顺序：' + ' > '.join(f'{x}(原第{first_pos.get((code, x), "?")})' for x in order[code]))
