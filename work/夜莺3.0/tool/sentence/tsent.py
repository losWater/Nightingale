"""虎整句（D89-r3）解码器的 Python 复刻，用于离线评测整句准确率。
逐项对照 lua/tiger_sentence*.lua：TCSKNM03 五元模型、TCSLEX01 词先验、码表索引（高频字本码过滤、白名单）、
格子图集束搜索（每段≥2键、单字重码组句、候选位惩罚、字奖励、整输入单字奖励）、结束分（句尾、本码奖励、孤立字惩罚）、
前 5 名词先验重排。未复刻：按键纠错、提前上屏、用户学习、补充词（tiger_sentence.supplement.txt）。
扩展：primary_by='reading' 时本码按“字+码前两位”（夜莺读音即字）确定。
"""
import bisect, collections, math, mmap, struct

LN10 = math.log(10)
BOS, EOS = '\2', '\3'


class FiveGram:
    def __init__(self, path):
        self.f = open(path, 'rb')
        self.m = mm = mmap.mmap(self.f.fileno(), 0, access=mmap.ACCESS_READ)
        h = mm[:256]
        assert h[:8] == b'TCSKNM03'
        self.version = struct.unpack_from('<I', h, 8)[0]
        assert struct.unpack_from('<Q', h, 16)[0] == len(mm)
        vocab_count = struct.unpack_from('<I', h, 28)[0]
        vocab_offset, vocab_bytes = struct.unpack_from('<QQ', h, 40)
        self.unknown, self.bos, self.eos = struct.unpack_from('<HHH', h, 56)
        div = 1e9 if self.version == 2 else 1e12
        self.qb = 1 if self.version == 2 else 2
        self.quant = []
        for i in range(5):
            pmin, pstep, bmin, bstep = struct.unpack_from('<iIiI', h, 160 + i * 16)
            self.quant.append((pmin / 1e7, pstep / div, bmin / 1e7, bstep / div))
        self.dirs = {}
        for order in range(2, 6):
            off = struct.unpack_from('<Q', h, 64 + (order - 2) * 24)[0]
            metas = []
            for b in range(256):
                bo, bb, io, ic, bc, rc = struct.unpack_from('<QQQIIQ', mm, off + b * 40)
                metas.append((io, ic, bc))
            self.dirs[order] = metas
        self.ids, self.up, self.ub = {}, [], []
        p = vocab_offset; q0 = self.quant[0]
        for i in range(vocab_count):
            n = struct.unpack_from('<H', mm, p)[0]; p += 2
            tok = mm[p:p + n].decode('utf-8'); p += n
            pq, bq = self._q(mm, p), self._q(mm, p + self.qb); p += 2 * self.qb
            self.ids[tok] = i
            self.up.append(q0[0] + pq * q0[1])
            self.ub.append(0.0 if bq == 0 else q0[2] + (bq - 1) * q0[3])
        self.index_cache, self.ctx_cache, self.step_cache = {}, {}, {}

    def _q(self, buf, p):
        return buf[p] if self.qb == 1 else struct.unpack_from('<H', buf, p)[0]

    def token_id(self, t):
        if t == BOS: return self.bos
        if t == EOS: return self.eos
        return self.ids.get(t, self.unknown)

    def _index(self, order, bucket, io, ic):
        key = (order, bucket)
        v = self.index_cache.get(key)
        if v is None:
            raw = self.m[io:io + ic * 16]
            keys = [struct.unpack_from('<4H', raw, e * 16) for e in range(ic)]
            offs = [struct.unpack_from('<Q', raw, e * 16 + 8)[0] for e in range(ic)]
            v = self.index_cache[key] = (keys, offs)
        return v

    def _context(self, ctx):
        """ctx: 上下文 id 元组（旧→新）。返回 (successors dict, bow) 或 None。"""
        hit = self.ctx_cache.get(ctx, 0)
        if hit != 0: return hit
        order = len(ctx) + 1
        io, ic, bc = self.dirs[order][ctx[0] % 256]
        res = None
        if bc and ic:
            keys, offs = self._index(order, ctx[0] % 256, io, ic)
            k = len(ctx)
            lo, hi = 0, ic
            while lo < hi:                              # 最后一个 key <= ctx
                mid = (lo + hi) // 2
                if keys[mid][:k] <= ctx: lo = mid + 1
                else: hi = mid
            if lo:
                e = lo - 1
                start = offs[e]; end = offs[e + 1] if e + 1 < ic else io
                data = self.m[start:end]; pos = 0; qb = self.qb
                hdr = k * 2 + qb + 2; sb = 2 + qb
                pq = self.quant[order - 1]; bq_ = self.quant[order - 2]
                while pos < len(data):
                    bctx = struct.unpack_from(f'<{k}H', data, pos)
                    bowq = self._q(data, pos + k * 2)
                    cnt = struct.unpack_from('<H', data, pos + k * 2 + qb)[0]
                    sp = pos + hdr
                    if bctx == ctx:
                        succ = {}
                        for j in range(cnt):
                            o = sp + j * sb
                            succ[struct.unpack_from('<H', data, o)[0]] = pq[0] + self._q(data, o + 2) * pq[1]
                        res = (succ, 0.0 if bowq == 0 else bq_[2] + (bowq - 1) * bq_[3])
                        break
                    if bctx > ctx: break
                    pos = sp + cnt * sb
        self.ctx_cache[ctx] = res
        return res

    def step(self, hist, tok):
        """hist: 最近至多 4 个 id（旧→新）。返回 (自然对数概率, 新 hist)。"""
        i = self.token_id(tok)
        key = (hist, i)
        s = self.step_cache.get(key)
        if s is None:
            total = 0.0; s = None
            for cl in range(min(4, len(hist)), 0, -1):
                c = self._context(hist[-cl:])
                if c is not None:
                    p = c[0].get(i)
                    if p is not None:
                        s = (total + p) * LN10; break
                    total += c[1]
            if s is None:
                s = (total + self.up[i]) * LN10
            self.step_cache[key] = s
        return s, (hist + (i,))[-4:]

    def observed_bigram(self, a, b):
        ia, ib = self.ids.get(a), self.ids.get(b)
        if ia is None or ib is None: return False
        c = self._context((ia,))
        return c is not None and ib in c[0]


class Lexical:
    MOD = 4294967291

    def __init__(self, path):
        d = open(path, 'rb').read()
        assert d[:8] == b'TCSLEX01'
        _, self.n, self.bits_n, self.k, self.lmin, self.lmax = struct.unpack_from('<6I', d, 8)
        self.bits = d[32:]
        self.cache = {}

    def contains(self, text):
        v = self.cache.get(text)
        if v is not None: return v
        a, b = 2166136261, 16777619
        for byte in text.encode('utf-8'):
            a = (a * 131 + byte + 17) % self.MOD
            b = (b * 137 + byte + 53) % self.MOD
        if b == 0: b = 1
        v = True
        for i in range(self.k):
            bit = (a + i * b + i * i * 97) % self.bits_n
            if not (self.bits[bit // 8] >> (bit % 8)) & 1:
                v = False; break
        self.cache[text] = v
        return v

    def score(self, text):
        n = len(text); best = [0.0] * (n + 1)
        for fin in range(1, n + 1):
            best[fin] = best[fin - 1]
            for L in range(self.lmin, self.lmax + 1):
                s = fin - L
                if s < 0: break
                if self.contains(text[s:fin]):
                    v = best[s] + 1.0 + 0.2 * (L - 2)
                    if v > best[fin]: best[fin] = v
        return best[n]


def read_codes(path):
    out, seen = [], set()
    for l in open(path, encoding='utf-8-sig'):
        if not l.strip() or l.startswith('#'): continue
        p = l.split()
        if len(p) < 2: continue
        w, c = p[0], p[1].lower()
        if c.isalpha() and c.isascii() and (w, c) not in seen:
            seen.add((w, c)); out.append((w, c))
    return out


def read_ranks(path):
    r = {}
    for l in open(path, encoding='utf-8-sig'):
        l = l.strip()
        if l and not l.startswith('#') and l[0] not in r:
            r[l[0]] = len(r) + 1
    return r


class Lexicon:
    """build_lexicon_index 的复刻。primary_by='char'（原版）或 'reading'（按 字+码前两位）。"""

    def __init__(self, entries, ranks, high_freq_limit=1500, whitelist=(), primary_by='char'):
        exact = collections.defaultdict(list)
        by_key = collections.defaultdict(list)
        key_of = (lambda w, c: w) if primary_by == 'char' else (lambda w, c: (w, c[:2]))
        for w, c in entries:
            exact[c].append(w)
            if len(w) == 1: by_key[key_of(w, c)].append(c)
        common = {ch for ch, r in ranks.items() if r <= high_freq_limit} if high_freq_limit > 0 else None
        primary, optimal = {}, {}
        for k, cs in by_key.items():
            bf = ba = None
            for c in cs:
                if len(c) >= 2:
                    if ba is None or len(c) < len(ba): ba = c
                    if exact[c][0] == (k if primary_by == 'char' else k[0]) and (bf is None or len(c) < len(bf)): bf = c
            if bf or ba: primary[k] = bf or ba
            ch = None
            for c in cs:
                if ch is None or len(c) < len(ch): ch = c
            optimal[k] = ch
        self.primary, self.key_of = primary, key_of
        wl = set(whitelist)
        self.codes, lengths = {}, set()
        for c, ws in exact.items():
            allowed = []
            for r, w in enumerate(ws, 1):
                k = key_of(w, c) if len(w) == 1 else None
                ok = len(c) == 1 or len(w) != 1 or common is None or w not in common or w in wl
                if ok or primary.get(k) == c:
                    allowed.append((w, r, optimal.get(k) == c, primary.get(k) == c))
            if allowed:
                self.codes[c] = allowed; lengths.add(len(c))
        self.lengths = sorted(lengths)

    def typed(self, ch, sy=None):
        """用户在整句里为该字（读音）打的码：本码。"""
        if sy is not None and self.key_of('x', 'xx') != 'x':
            return self.primary.get((ch, sy))
        return self.primary.get(ch)


class Decoder:
    BEAM, LONG_AT, LONG_BEAM = 200, 24, 48
    RANK_PEN, CHAR_REWARD, WHOLE_SINGLE, CODE_REWARD = 0.03, 2.0, 5.0, 2.0
    ISO_TH, ISO_LAMBDA, LEX_W, LEX_TOP, TOPK = 3000, 2.0, 0.1, 5, 20

    def __init__(self, lm, lex, lexicon, ranks):
        self.lm, self.lex, self.L, self.ranks = lm, lex, lexicon, ranks
        self.unknown_rank = len(ranks) + 1 if ranks else 20001

    @staticmethod
    def _score_first(it):     # state_better_score_first：分高、候选位小、文本小
        return (-it['score'], it['max_rank'], it['text'])

    def _dup_better(self, a, b):
        if a['max_rank'] != b['max_rank']: return a['max_rank'] < b['max_rank']
        if a['score'] != b['score']: return a['score'] > b['score']
        return a['edges'] < b['edges']

    def _add(self, bucket, it):
        old = bucket.get(it['text'])
        if old is None or self._dup_better(it, old): bucket[it['text']] = it

    def _prune(self, bucket, pos):
        lim = self.LONG_BEAM if pos > self.LONG_AT else self.BEAM
        items = sorted(bucket.values(), key=self._score_first)
        return items[:lim]

    def _iso(self, path):
        pen, last, lw = 0.0, None, 0.0
        for chars, prim, clen in path:
            factor = 0.0 if (prim and clen >= 4) else 1.0
            for ch in chars:
                rare = self.ranks.get(ch, self.unknown_rank) > self.ISO_TH
                rw = factor if rare else 0.0
                linked = last is not None and (lw > 0 or rw > 0) and self.lm.observed_bigram(last, ch)
                if lw > 0 and linked: pen -= self.ISO_LAMBDA * lw
                lw = rw if (rw > 0 and not linked) else 0.0
                if lw > 0: pen += self.ISO_LAMBDA * lw
                last = ch
        return pen

    def decode(self, raw):
        n = len(raw)
        states = [dict() for _ in range(n + 1)]
        states[0][''] = {'score': 0.0, 'text': '', 'hist': (self.lm.bos,), 'max_rank': 1, 'code': 0.0, 'edges': 0, 'path': ()}
        for pos in range(n):
            cur = self._prune(states[pos], pos) if pos else list(states[0].values())
            for L in self.L.lengths:
                if pos + L > n or (n > 1 and L < 2): continue
                cands = self.L.codes.get(raw[pos:pos + L])
                if not cands: continue
                whole = pos == 0 and pos + L == n
                if not whole:
                    cands = [c for c in cands if c[1] == 1 or len(c[0]) == 1]
                for it in cur:
                    for w, r, opt, prim in cands:
                        s, h = it['score'], it['hist']
                        for ch in w:
                            lp, h = self.lm.step(h, ch); s += lp + self.CHAR_REWARD
                        s -= self.RANK_PEN * math.log(r)
                        single = len(w) == 1
                        if whole and opt and single: s += self.WHOLE_SINGLE
                        self._add(states[pos + L], {
                            'score': s, 'text': it['text'] + w, 'hist': h, 'max_rank': max(it['max_rank'], r),
                            'code': it['code'] + (self.CODE_REWARD * L if (prim and single) else 0.0),
                            'edges': it['edges'] + 1, 'path': it['path'] + ((w, prim and single, L),)})
        done = self._prune(states[n], n)
        if not done: return None
        res = []
        for it in done:
            eos, _ = self.lm.step(it['hist'], EOS)
            res.append(dict(it, score=it['score'] + eos - self._iso(it['path']) + it['code']))
        composed = any(it['edges'] > 1 for it in res)
        key = self._score_first if composed else (lambda it: (it['max_rank'], -it['score'], it['text']))
        res = sorted(res, key=key)[:self.TOPK]
        if len(res) > 1 and self.lex:
            for it in res[:self.LEX_TOP]:
                it['score'] += self.lex.score(it['text']) * self.LEX_W
            res.sort(key=key)
        return res
