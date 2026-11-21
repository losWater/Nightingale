"""全拼 → 小鹤 / 自然码 双拼。零声母：单韵母双写，双字母韵母取原拼，ang/eng 取首字母+韵母键。"""
INIT = {'zh': 'v', 'ch': 'i', 'sh': 'u'}
XIAOHE = {'iu': 'q', 'ei': 'w', 'uan': 'r', 'ue': 't', 've': 't', 'un': 'y', 'uo': 'o', 'ie': 'p',
          'ong': 's', 'iong': 's', 'ai': 'd', 'en': 'f', 'eng': 'g', 'ang': 'h', 'an': 'j',
          'ing': 'k', 'uai': 'k', 'iang': 'l', 'uang': 'l', 'ou': 'z', 'ia': 'x', 'ua': 'x',
          'ao': 'c', 'ui': 'v', 'v': 'v', 'in': 'b', 'iao': 'n', 'ian': 'm',
          'a': 'a', 'o': 'o', 'e': 'e', 'i': 'i', 'u': 'u'}
ZIRANMA = {'iu': 'q', 'ia': 'w', 'ua': 'w', 'uan': 'r', 'ue': 't', 've': 't', 'ing': 'y', 'uai': 'y',
           'uo': 'o', 'un': 'p', 'ong': 's', 'iong': 's', 'iang': 'd', 'uang': 'd', 'en': 'f',
           'eng': 'g', 'ang': 'h', 'an': 'j', 'ao': 'k', 'ai': 'l', 'ei': 'z', 'ie': 'x',
           'iao': 'c', 'ui': 'v', 'v': 'v', 'ou': 'b', 'in': 'n', 'ian': 'm',
           'a': 'a', 'o': 'o', 'e': 'e', 'i': 'i', 'u': 'u'}
SCHEMES = {'xiaohe': XIAOHE, 'ziranma': ZIRANMA}


def split(py):
    py = py.lower().replace('ü', 'v').rstrip('012345')
    for ini in ('zh', 'ch', 'sh'):
        if py.startswith(ini):
            return ini, py[2:]
    if py[0] in 'aoe':
        return '', py
    ini, fin = py[0], py[1:]
    return ini, fin  # j/q/x/y 后的 u 即 ü，双拼中按 u 系韵母取键（qu→qu、quan→qr、yun→yy）


SPECIAL = {'ng': 'ng', 'n': 'nn', 'm': 'mm', 'hm': 'hm', 'hng': 'hg'}


def encode(py, scheme='ziranma'):
    table = SCHEMES[scheme]
    bare = py.lower().rstrip('012345')
    if bare in SPECIAL:
        return SPECIAL[bare]
    ini, fin = split(py)
    if ini == '':
        if len(fin) == 1:
            return fin * 2
        if len(fin) == 2:
            return fin
        return fin[0] + table[fin]
    return INIT.get(ini, ini) + table[fin]


_SYL = None


def syllables():
    """音节表（全音节映射 + 补充音节）。"""
    global _SYL
    if _SYL is None:
        import json
        from pathlib import Path
        sy = json.load(open(Path(__file__).resolve().parent.parent / 'data/inputs/全音节映射.json', encoding='utf-8'))['小鹤']
        _SYL = list(sy) + ['fiao', 'rua', 'chua', 'zhei', 'shei', 'sei']
    return _SYL


def recode(code2, src='xiaohe', dst='ziranma'):
    """一个音节的双拼码（两码）从 src 方案换成 dst 方案；音节表取 data/inputs/全音节映射.json（另补 fiao、rua、chua 与口语音 zhei、shei、sei）；表外的码（作者自定义、特殊码）原样返回。"""
    if src == dst: return code2
    m = {}
    for py in syllables():
        m.setdefault(encode(py, src), set()).add(encode(py, dst))
    out = m.get(code2, {code2})
    assert len(out) == 1, (code2, out)
    return next(iter(out))


def recode_word(word, code, src='xiaohe', dst='ziranma'):
    """词码换方案：二字词四码 = 两音节双拼（逐个换）、三码 = 首音节双拼 + 次字声母（换首音节）；
    二码（声母缩写或作者自定义）与三字以上的词（只取声母，两方案声母键相同）不变。"""
    if src == dst or len(word) != 2 or len(code) < 3: return code
    head = recode(code[:2], src, dst)
    return head + (recode(code[2:], src, dst) if len(code) == 4 else code[2:])
