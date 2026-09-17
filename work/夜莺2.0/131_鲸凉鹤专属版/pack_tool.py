# -*- coding: utf-8 -*-
"""组装给鲸凉鹤作者的工具包：exe + 夜莺核心单字表 + 他的词库 + 使用说明 → 一个 zip。
他双击 exe 就能生成合并结果；以后任一边更新，换掉对应的 txt 再双击一次即可。可复现打包。"""
import io, sys, os, shutil, zipfile, hashlib, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
EXE = H + '/工具/dist/夜莺单字合并工具.exe'
CORE = W + '/106_全平台导出/夜莺2.0_字词表与输入法/手心/模块化挂接/01_核心单字.txt'
SRC = 'E:/夜莺2.0/releases/v0.9.1/99_参考资料/参考/鲸凉鹤1.1手心挂接.txt'
assert os.path.exists(EXE), 'exe 不在。先构建：pip install pyinstaller 后，在 131_鲸凉鹤专属版/工具 目录跑
  python -m PyInstaller --onefile --console --name "夜莺单字合并工具" --distpath dist --workpath build --specpath build --clean 合并.py
（仓库不收 exe，只收源码 工具/合并.py）'
STAGE = H + '/工具包'; os.makedirs(STAGE, exist_ok=True)
for f in os.listdir(STAGE):
    if os.path.isfile(STAGE + '/' + f): os.remove(f'{STAGE}/{f}')      # 只清本脚本上次放的文件
shutil.copy2(EXE, STAGE + '/夜莺单字合并工具.exe')
shutil.copy2(CORE, STAGE + '/夜莺2.0_核心单字表.txt')
shutil.copy2(SRC, STAGE + '/鲸凉鹤1.1手心挂接.txt')
n_core = sum(1 for _ in open(CORE, encoding='utf-8-sig')); n_src = sum(1 for _ in open(SRC, encoding='utf-8-sig'))
open(STAGE + '/使用说明.txt', 'wb').write(('\r\n'.join(f"""夜莺单字 × 鲸凉鹤词库 合并工具

这个工具把「夜莺的单字」和「你自己的词库」拼成一张表：
  · 夜莺单字落在夜莺核心单字表指定的候选位上，位置一个都不变——这就是你要的"夜莺单字保持原样"。
  · 你的词库一个字节都不动：编码、词、先后顺序照抄，飞键、无理码、特设短语、简词、长码全部保留。
  · 同一个码上撞位置时，夜莺单字占住它的序号，你的词依次往后排。
    夜莺核心单字表的序号本来就留了空位（让位的字从第 2 位起），那些空位就是给你的词的。

怎么用
------
把这个文件夹里的东西解压到一起，双击「夜莺单字合并工具.exe」。
几秒钟后同目录会多出四个文件：

  合并结果_手心挂接.txt   手心格式（编码=序号,内容），和你原来的文件同款，直接替换即可
  合并结果_普通.txt       文字<Tab>编码，给别的输入法用
  合并结果_码前.txt       编码<Tab>文字，内容与顺序同上
  合并报告.txt            这次合并的条数、字词同码的码位数、被跳过的行

以后怎么更新
------------
不管是你的词库更新了，还是夜莺的单字表更新了，把新文件放进这个文件夹替换掉旧的，再双击一次就行。
工具会自己分辨哪个是单字表、哪个是词库（单字表里几乎每条都是单个汉字）。
夜莺的新单字表在这里取：https://github.com/losWater/Nightingale/releases 的「码表与挂接包」，
解压后路径是 手心/模块化挂接/01_核心单字.txt，拿它替换掉包里的 夜莺2.0_核心单字表.txt 即可（名字随便，含「核心单字」最保险）。
万一认不出来，把夜莺那份的文件名改成含「核心单字」三个字就行，例如 夜莺2.0_核心单字表.txt。

对文件的要求
------------
两个输入文件都是手心格式，一行一条：编码=序号,内容
例如   wwts=2,喂        aabc=1,阿宝
编码只能是小写字母，序号是数字，逗号后面是字或词。不合这个格式的行会被跳过，并在报告里逐行列出来。
（你现在这份词库里有 6 行少了逗号或内容为空，工具会点出具体行号，改好再跑一次就能收回。）

包里的文件
----------
  夜莺单字合并工具.exe      合并工具，不需要安装 Python
  夜莺2.0_核心单字表.txt     夜莺 2.0 的单字（8105 通用规范汉字 + 7391 扩展字），{n_core} 条
  鲸凉鹤1.1手心挂接.txt      你的词库，{n_src} 条，原样未动

其他
----
工具是用 PyInstaller 打包的，个别杀毒软件会对这类 exe 误报，加信任即可。它只读取同目录的 txt、只往同目录写结果，不联网。
生成日期 {datetime.date.today().strftime('%Y-%m-%d')}，工具版本 v1.0。有问题找夜莺作者。
""".splitlines())).encode('utf-8-sig'))
Z = H + '/夜莺单字合并工具包_%s.zip' % datetime.date.today().strftime('%Y%m%d')
items = sorted((f, STAGE + '/' + f) for f in os.listdir(STAGE) if os.path.isfile(STAGE + '/' + f))
with zipfile.ZipFile(Z + '.tmp', 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for rel, src in items:
        zi = zipfile.ZipInfo(rel, (2026, 1, 1, 0, 0, 0)); zi.external_attr = 0o644 << 16; zi.create_system = 0; zi.compress_type = zipfile.ZIP_DEFLATED
        with open(src, 'rb') as f: z.writestr(zi, f.read())
os.replace(Z + '.tmp', Z)
with zipfile.ZipFile(Z) as z: assert z.testzip() is None and len(z.namelist()) == 4
print('%s\n%d 个文件 %.1f MB  sha256 %s' % (os.path.basename(Z), len(items), os.path.getsize(Z) / 1048576, hashlib.sha256(open(Z, 'rb').read()).hexdigest()))
for rel, src in items: print('   %-28s %8.1f KB' % (rel, os.path.getsize(src) / 1024))
