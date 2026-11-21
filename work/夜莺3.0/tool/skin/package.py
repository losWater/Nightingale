"""把夜莺 / 夜桜 皮肤打成完整包：每个角色一个 zip，内含
- <皮肤名>.ssf：搜狗皮肤（skin.ini + panel.png 的 zip，改后缀 .ssf；搜狗、手心等双击安装）
- 虎符/<id>.json：虎符皮肤（候选窗配色 + 候选挂件动图），以及单独的挂件动图
- 预览.png、挂件动图.png（APNG，Safari 可看动画）、安装说明.txt
先跑 make_skin.py 与 make_hufu.py。用法：.venv/bin/python tool/skin/package.py
"""
import shutil, zipfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_skin import THEMES
from make_hufu import HUFU

SRC = Path.home() / 'Downloads/输入法皮肤'
OUT = SRC / '完整皮肤包'

GUIDE = '''{name} · 输入法皮肤

【搜狗 / 手心等（静态皮肤）】
双击「{name}.ssf」即可安装（需已装搜狗输入法或兼容 ssf 的输入法）。
也可以在输入法的「皮肤设置」里选择「本地导入」，选这个 .ssf 文件。

【虎符输入法（动态挂件）】
方法一：把「虎符/{hid}.json」放进虎符数据目录下的「皮肤」文件夹，在虎符设置里选择皮肤「{name}」。
方法二：只用动图挂件——在虎符设置页「候选挂件」里选择「虎符/{name}_挂件动图.png」。
挂件默认在候选框右侧、底部对齐、高 150，可在设置页里调整位置和大小。

【文件】
{name}.ssf          搜狗皮肤（静态，候选框与形象）
虎符/{hid}.json      虎符皮肤（配色 + 动图挂件）
虎符/{name}_挂件动图.png  动图挂件（APNG，用 Safari 等浏览器打开可看动画）
预览.png            静态皮肤效果预览

夜莺官网：https://loswater.github.io/Nightingale/
'''


def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for key, th in THEMES.items():
        name, hid = th['name'], HUFU[key]['id']
        d = OUT / name; (d / '虎符').mkdir(parents=True)
        with zipfile.ZipFile(d / f'{name}.ssf', 'w', zipfile.ZIP_DEFLATED) as z:      # ssf = 皮肤文件 zip
            z.write(SRC / name / 'skin.ini', 'skin.ini'); z.write(SRC / name / 'panel.png', 'panel.png')
        shutil.copy(SRC / '虎符' / f'{hid}.json', d / '虎符' / f'{hid}.json')
        shutil.copy(SRC / '虎符' / f'{name}_挂件动图.png', d / '虎符' / f'{name}_挂件动图.png')
        shutil.copy(SRC / f'{name}_预览.png', d / '预览.png')
        (d / '安装说明.txt').write_text(GUIDE.format(name=name, hid=hid), encoding='utf-8')
        z = OUT / f'{name}_皮肤.zip'
        with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zz:
            for p in sorted(d.rglob('*')):
                if p.is_file(): zz.write(p, p.relative_to(OUT))
        print(z, f'{z.stat().st_size / 1048576:.1f} MB')


if __name__ == '__main__':
    main()
