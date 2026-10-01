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
