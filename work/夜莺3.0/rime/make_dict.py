"""由普通单字表生成 Rime 单字码表：普通单字表 + 附加条目（夜莺 2.5 快符等：现有码表里有、旧普通单字表里没有的）。
同码内按表中顺序给权重 99999、99998…；附加条目排在同码汉字之后。
用法：python rime/make_dict.py <旧普通单字表> <新普通单字表> <版本号>   # 就地重写 rime/Rime/yeying_tune.dict.yaml
"""
import collections, re, sys
from pathlib import Path

DICT = Path(__file__).resolve().parent / 'Rime/yeying_tune.dict.yaml'


def read(table):
    return [tuple(l.rstrip('\n').split('\t')[:2]) for l in open(table, encoding='utf-8-sig') if '\t' in l]


def main(old_table, table, version):
    head, body = DICT.read_text(encoding='utf-8').split('\n...\n', 1)
    old = set(read(old_table))
    extra = [e for e in (tuple(l.split('\t')[:2]) for l in body.splitlines() if l.count('\t') == 2) if e not in old]
    slots = collections.defaultdict(list)
    for ch, code in read(table) + extra:
        slots[code].append(ch)
    lines = [f'{ch}\t{code}\t{99999 - k}' for code in sorted(slots) for k, ch in enumerate(slots[code])]
    head = re.sub(r'version: "[^"]*"', f'version: "{version}"', head)
    DICT.write_text(head + '\n...\n' + '\n'.join(lines) + '\n', encoding='utf-8')
    print(DICT, '条目', len(lines), '附加', len(extra))


if __name__ == '__main__':
    main(*sys.argv[1:4])
