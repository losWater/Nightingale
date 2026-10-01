"""流式抓取多体裁中文语料（不整包下载），按体裁截取固定汉字量，繁转简，每行一段。
来源：HuggingFace liwu/MNBVC（新闻/百科/知乎/树洞）、wdndev/webnovel-chinese、qhchina/100_top_chinese_novels。"""
import gzip, io, json, re, sys, urllib.request, urllib.parse, random
from pathlib import Path
import opencc

HF = 'https://huggingface.co/datasets/'
OUT = Path(__file__).resolve().parent.parent / 'corpus'
BUDGET = int(sys.argv[1]) if len(sys.argv) > 1 else 8_000_000   # 每体裁汉字数
HAN = re.compile(r'[一-鿿]')
t2s = opencc.OpenCC('t2s')


def stream(path, gz):
    url = HF + urllib.parse.quote(path)
    r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'yozakura'}), timeout=120)
    f = gzip.GzipFile(fileobj=r) if gz else r
    for line in io.TextIOWrapper(f, encoding='utf-8', errors='ignore'):
        yield line


def paras_mnbvc(rec, min_year=None):
    if min_year:
        m = re.search(r'/(\d{4})年', rec.get('文件名', ''))
        if not m or int(m.group(1)) < min_year:
            return
    for p in rec.get('段落', []):
        if not p.get('是否重复'):
            yield p.get('内容', '')


def gen_news():
    for i in range(13):
        for line in stream(f'liwu/MNBVC/resolve/main/news/20230196/{i}.jsonl.gz', True):
            yield from paras_mnbvc(json.loads(line), min_year=1990)


def gen_wiki():
    for line in stream('liwu/MNBVC/resolve/main/wiki/20230197/0.jsonl.gz', True):
        yield from paras_mnbvc(json.loads(line))


def gen_zhihu():
    for i in range(5):
        for line in stream(f'liwu/MNBVC/resolve/main/qa/20230196/zhihu/{i}.jsonl.gz', True):
            r = json.loads(line)
            yield r.get('问', '')
            yield from r.get('答', '').split('\n')


def gen_forum():
    for line in stream('liwu/MNBVC/resolve/main/forum/20230253/pkuhole.20230253.2.论坛/pkuholefromarchive_0.jsonl.gz', True):
        r = json.loads(line)
        yield r.get('主题', '')
        for x in r.get('回复', []):
            yield x.get('回复', '')


def gen_webnovel():
    for line in stream('wdndev/webnovel-chinese/resolve/main/data/webnovel_0.jsonl', False):
        yield from json.loads(line).get('text', '').split('\n')


def gen_classic():
    api = 'https://huggingface.co/api/datasets/qhchina/100_top_chinese_novels/tree/main/data'
    files = [x['path'] for x in json.load(urllib.request.urlopen(api)) if x['path'].endswith('.txt')]
    random.Random(0).shuffle(files)
    for p in files:
        yield from stream('qhchina/100_top_chinese_novels/resolve/main/' + p, False)


GENRES = dict(news=gen_news, wiki=gen_wiki, zhihu=gen_zhihu, forum=gen_forum, webnovel=gen_webnovel, classic=gen_classic)

if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    for name in (sys.argv[2:] or GENRES):
        n = 0
        with open(OUT / f'{name}.txt', 'w', encoding='utf-8') as out:
            for para in GENRES[name]():
                para = t2s.convert(para.strip())
                h = len(HAN.findall(para))
                if h < 8:
                    continue
                out.write(para.replace('\n', ' ') + '\n')
                n += h
                if n >= BUDGET:
                    break
        print(name, '汉字', n, flush=True)
