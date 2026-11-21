"""夜莺 / 夜桜 输入法皮肤（搜狗皮肤结构：skin.ini + panel.png，与参考皮肤“DS鲸鱼娘·冰海鲸语”同尺寸同布局）。
做法：Q版形象白底抠图 → 程序绘制候选框（主题配色、外发光、装饰）→ 形象趴在框的右上角（头和手里的键帽露在框上，身体藏在框后）。
输出：~/Downloads/输入法皮肤/<皮肤名>.zip（内含 skin.ini、panel.png），另出一张带示例文字的预览图。
用法：.venv/bin/python tool/skin/make_skin.py [夜莺|夜桜]   # 不带参数两个都做
"""
import math, random, sys, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ART = Path.home() / 'Documents/输入法形象'
OUT = Path.home() / 'Downloads/输入法皮肤'
W, H = 1995, 788                      # 与参考皮肤相同
FRAME = (30, 360, 1980, 722)          # 候选框外沿（左、上、右、下）
SS = 2                                # 超采样，画完缩小抗锯齿
FONT = '/System/Library/Fonts/Hiragino Sans GB.ttc'

THEMES = {
    '夜莺': dict(
        name='夜莺·月下文羽', author='夜莺', chibi='夜莺/ChatGPT 图像 2026年10月16日 08_27_17.png', full='夜莺/ChatGPT 图像 2026年10月16日 08_27_40.png',
        border='#2b2550', border2='#4a3f7a', trim='#d4af6a', fill_top='#fffaf0', fill_bottom='#f4ecdc', glow='#e9c98a',
        pinyin='#9a6a2a', first='#2b2550', other='#5b4a3a', hint='#a8875a',
        accent=['#e7c27a', '#f6e2b0', '#b48a3c'], deco='feather'),
    '夜桜': dict(
        name='夜桜·樱月幻梦', author='夜桜', chibi='夜桜/ChatGPT 图像 2026年10月15日 06_18_45.png', full='夜桜/樱月幻梦：绯紫少女եց.png',
        border='#3a2148', border2='#5c3570', trim='#f3a9c6', fill_top='#fff5f9', fill_bottom='#fbe6ef', glow='#f7b7d2',
        pinyin='#b0507e', first='#3a2148', other='#6a4a62', hint='#c286a6',
        accent=['#f7c3d6', '#ffe3ee', '#e98bb2'], deco='sakura'),
}


def rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def cutout(path):
    """白底抠图：与边缘相连的近白区域、以及大块封闭的近白区域设为透明；边缘按白度给半透明并去白边。"""
    im = np.asarray(Image.open(path).convert('RGB')).astype(np.float32)
    mn = im.min(axis=2)
    near = mn > 236
    lab, n = ndimage.label(near)
    border_ids = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    sizes = ndimage.sum(near, lab, range(1, n + 1))
    bg = np.isin(lab, list(border_ids)) | np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 600])
    # 边缘两像素内按白度渐变
    dist = ndimage.distance_transform_edt(~bg)
    alpha = np.ones(mn.shape, np.float32)
    alpha[bg] = 0
    edge = (dist > 0) & (dist <= 2.5)
    a_e = np.clip((255 - mn) / 60.0, 0, 1)
    alpha[edge] = np.minimum(alpha[edge], np.maximum(a_e[edge], (dist[edge] - 0.5) / 2.0))
    a = np.clip(alpha, 1e-3, 1)[..., None]
    col = np.clip((im - 255 * (1 - a)) / a, 0, 255)          # 去掉白色混入
    out = np.dstack([col, alpha[..., None] * 255]).astype(np.uint8)
    img = Image.fromarray(out, 'RGBA')
    return img.crop(img.getbbox())


def lift(path, box, scale, lo=168, hi=248):
    """从立绘里取一块装饰（月亮、羽毛、樱枝……）：按离白色的远近给软透明度，并去掉白色混入。"""
    im = np.asarray(Image.open(path).convert('RGB').crop(box)).astype(np.float32)
    mn = im.min(axis=2)
    a = np.clip((hi - mn) / (hi - lo), 0, 1) ** 0.85
    h_, w_ = mn.shape                                   # 取块边缘 10px 渐隐，避免直线切口
    ry = np.minimum(np.arange(h_), np.arange(h_)[::-1])[:, None]; rx = np.minimum(np.arange(w_), np.arange(w_)[::-1])[None, :]
    a = a * np.clip(np.minimum(ry, rx) / 10.0, 0, 1)
    aa = np.clip(a, 1e-3, 1)[..., None]
    col = np.clip((im - 255 * (1 - aa)) / aa, 0, 255)
    img = Image.fromarray(np.dstack([col, a[..., None] * 255]).astype(np.uint8), 'RGBA')
    img = img.crop(img.getbbox())
    return img.resize((max(1, int(img.width * scale * SS)), max(1, int(img.height * scale * SS))), Image.LANCZOS)


def put(layer, piece, cx, cy):
    layer.alpha_composite(piece, (int(cx * SS - piece.width / 2), int(cy * SS - piece.height / 2)))


def rounded(draw, box, r, **kw):
    draw.rounded_rectangle([v * SS for v in box], radius=r * SS, **kw)


def vgrad(size, top, bottom):
    w, h = size
    t = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(rgb(top)) * (1 - t) + np.array(rgb(bottom)) * t).repeat(w, axis=1)
    return Image.fromarray(np.dstack([arr, np.full((h, w, 1), 255)]).astype(np.uint8), 'RGBA')


def star(draw, cx, cy, r, color, k=0.28):
    """四角闪光星。"""
    pts = []
    for i in range(8):
        ang = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * k
        pts.append(((cx + rr * math.cos(ang)) * SS, (cy + rr * math.sin(ang)) * SS))
    draw.polygon(pts, fill=color)


def crescent(layer, cx, cy, r, color, glow):
    m = Image.new('L', layer.size, 0); d = ImageDraw.Draw(m)
    d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=255)
    o = r * 0.42
    d.ellipse([(cx - r + o) * SS, (cy - r - o * 0.5) * SS, (cx + r + o) * SS, (cy + r - o * 0.5) * SS], fill=0)
    g = m.filter(ImageFilter.GaussianBlur(10 * SS))
    layer.alpha_composite(Image.composite(Image.new('RGBA', layer.size, rgb(glow) + (170,)), Image.new('RGBA', layer.size, (0, 0, 0, 0)), g))
    layer.alpha_composite(Image.composite(Image.new('RGBA', layer.size, rgb(color) + (255,)), Image.new('RGBA', layer.size, (0, 0, 0, 0)), m))


def petal(draw, cx, cy, size, ang, color):
    pts = []
    for i in range(24):
        t = 2 * math.pi * i / 24
        x = size * 0.55 * math.sin(t) * (1 - 0.25 * math.cos(t))
        y = size * math.cos(t) * 0.5
        if y < -size * 0.38: x *= 0.6                          # 樱瓣尖端的缺口感
        xr, yr = x * math.cos(ang) - y * math.sin(ang), x * math.sin(ang) + y * math.cos(ang)
        pts.append(((cx + xr) * SS, (cy + yr) * SS))
    draw.polygon(pts, fill=color)


def sakura(draw, cx, cy, r, color, center):
    for i in range(5):
        ang = 2 * math.pi * i / 5 - math.pi / 2
        petal(draw, cx + r * 0.55 * math.cos(ang), cy + r * 0.55 * math.sin(ang), r * 0.95, ang + math.pi / 2, color)
    draw.ellipse([(cx - r * 0.18) * SS, (cy - r * 0.18) * SS, (cx + r * 0.18) * SS, (cy + r * 0.18) * SS], fill=center)


def feather(layer, cx, cy, length, ang, c1, c2):
    """简笔羽毛：中轴 + 两侧渐细的羽片。"""
    d = ImageDraw.Draw(layer)
    for side in (-1, 1):
        pts = []
        for i in range(21):
            t = i / 20
            wdt = length * 0.16 * math.sin(math.pi * t) ** 0.8
            pts.append((t * length, side * wdt))
        pts.append((length, 0))
        poly = [((cx + x * math.cos(ang) - y * math.sin(ang)) * SS, (cy + x * math.sin(ang) + y * math.cos(ang)) * SS) for x, y in pts]
        d.polygon(poly, fill=c1 if side < 0 else c2)
    d.line([(cx * SS, cy * SS), ((cx + length * math.cos(ang)) * SS, (cy + length * math.sin(ang)) * SS)], fill=c2, width=2 * SS)


def keycap(layer, cx, cy, s, text, face, edge, ink, glow):
    g = Image.new('RGBA', layer.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    gd.rounded_rectangle([(cx - s) * SS, (cy - s) * SS, (cx + s) * SS, (cy + s) * SS], radius=s * 0.35 * SS, fill=rgb(glow) + (200,))
    layer.alpha_composite(g.filter(ImageFilter.GaussianBlur(s * 0.5 * SS)))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([(cx - s) * SS, (cy - s * 0.92) * SS, (cx + s) * SS, (cy + s) * SS], radius=s * 0.3 * SS, fill=edge)
    d.rounded_rectangle([(cx - s * 0.82) * SS, (cy - s * 0.92) * SS, (cx + s * 0.82) * SS, (cy + s * 0.68) * SS], radius=s * 0.25 * SS, fill=face)
    f = ImageFont.truetype(FONT, int(s * 1.05 * SS), index=1)
    d.text((cx * SS, (cy - s * 0.12) * SS), text, font=f, fill=ink, anchor='mm')


def build(key):
    th = THEMES[key]
    random.seed(7)
    big = (W * SS, H * SS)
    canvas = Image.new('RGBA', big, (0, 0, 0, 0))
    x0, y0, x1, y1 = FRAME
    # 外发光
    glow = Image.new('L', big, 0)
    ImageDraw.Draw(glow).rounded_rectangle([(x0 - 4) * SS, (y0 - 4) * SS, (x1 + 4) * SS, (y1 + 4) * SS], radius=52 * SS, fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(10 * SS))
    canvas.alpha_composite(Image.composite(Image.new('RGBA', big, rgb(th['glow']) + (120,)), Image.new('RGBA', big, (0, 0, 0, 0)), glow))
    # 框：深色外框 → 第二层 → 金/粉细线 → 渐变底
    d = ImageDraw.Draw(canvas)
    rounded(d, (x0, y0, x1, y1), 46, fill=rgb(th['border']))
    rounded(d, (x0 + 7, y0 + 7, x1 - 7, y1 - 7), 40, fill=rgb(th['border2']))
    rounded(d, (x0 + 13, y0 + 13, x1 - 13, y1 - 13), 35, fill=rgb(th['trim']))
    inner = (x0 + 17, y0 + 17, x1 - 17, y1 - 17)
    m = Image.new('L', big, 0)
    ImageDraw.Draw(m).rounded_rectangle([v * SS for v in inner], radius=31 * SS, fill=255)
    canvas.paste(vgrad(big, th['fill_top'], th['fill_bottom']), (0, 0), m)
    # 内侧细描边
    d = ImageDraw.Draw(canvas)
    rounded(d, (inner[0] + 9, inner[1] + 9, inner[2] - 9, inner[3] - 9), 24, outline=rgb(th['trim']) + (110,), width=2 * SS)
    deco = Image.new('RGBA', big, (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    a1, a2, a3 = [rgb(c) for c in th['accent']]
    full = ART / th['full']
    if th['deco'] == 'feather':
        put(deco, lift(full, (815, 22, 935, 140), 1.0), 118, 292)               # 新月与小星（取自立绘）
        put(deco, lift(full, (40, 640, 140, 760), 0.9), 62, 412)                # 羽毛
        put(deco, lift(full, (128, 148, 200, 212), 0.9), 430, 262)              # 飞鸟
        keycap(deco, 262, 326, 30, '夜', '#fff7e2', '#e8d2a0', rgb(th['border']), th['glow'])
        keycap(deco, 342, 300, 24, '莺', '#fff7e2', '#e8d2a0', rgb(th['border']), th['glow'])
        for cx, cy, r in [(212, 250, 13), (395, 338, 9), (455, 318, 7)]:      # 装饰都在 x<480，避开横向拉伸区
            star(dd, cx, cy, r, a1 + (255,))
        star(dd, 120, 650, 11, a1 + (230,)); star(dd, 1905, 655, 11, a1 + (230,))
    else:
        crescent(deco, 118, 296, 54, '#ece6f0', th['glow'])                     # 银色新月
        put(deco, lift(full, (840, 68, 990, 215), 1.15), 300, 292)             # 樱枝（取自立绘，只取上段）
        for cx, cy, r, ang in [(440, 258, 26, 0.6), (420, 330, 21, 2.2), (1912, 600, 24, 1.1), (112, 655, 22, 2.8), (205, 238, 18, 0.2)]:
            petal(dd, cx, cy, r, ang, a1 + (240,))
        for cx, cy, r in [(250, 250, 10), (465, 300, 8)]:
            star(dd, cx, cy, r, (255, 255, 255, 240))
    canvas.alpha_composite(deco)
    # 形象：头与键帽露在框上方，框以下的身体淡出隐藏
    ch = cutout(ART / th['chibi'])
    s = 610 / ch.height
    ch = ch.resize((int(ch.width * s * SS), int(ch.height * s * SS)), Image.LANCZOS)
    cx = 1530
    px, py = int((cx - ch.width / SS / 2) * SS), int(-8 * SS)
    layer = Image.new('RGBA', big, (0, 0, 0, 0)); layer.alpha_composite(ch, (px, py))
    cut = y0 + 14                                                     # 只留到框的上沿：手和键帽搭在框边上，身体藏在框后
    fade = np.ones((big[1], 1), np.float32)
    ys = np.arange(big[1]) / SS
    fade[:, 0] = np.clip((cut + 6 - ys) / 6, 0, 1)
    la = np.asarray(layer).astype(np.float32); la[..., 3] *= fade
    canvas.alpha_composite(Image.fromarray(la.astype(np.uint8), 'RGBA'))
    panel = canvas.resize((W, H), Image.LANCZOS)
    return th, panel


def skin_ini(th):
    c = lambda h: '0x' + h.lstrip('#').upper()[4:6] + h.lstrip('#').upper()[2:4] + h.lstrip('#').upper()[0:2]   # 搜狗配色为 BGR
    ref = (Path.home() / '.cache/skin-ref/skin.ini').read_text(encoding='utf-8-sig')
    body = ref[ref.index('[Scheme_H1]'):]
    return ('[General]\n' f'skin_name={th["name"]}\nskin_author={th["author"]}\npreview_comp=panel.png\n'
            '[Display]\nfont_size=200\nfont_ch=Microsoft YaHei UI\nfont_en=Microsoft YaHei UI\n'
            f'pinyin_color={c(th["pinyin"])}\nzhongwen_first_color={c(th["first"])}\nzhongwen_color={c(th["other"])}\n'
            f'comphint_color={c(th["hint"])}\ncandidate_spacing=120\nline_spacing=24\ncharacter_spacing=0\n' + body)


def preview(th, panel):
    """示例效果：在框里写上编码与候选（只用于看效果，不进皮肤包）。"""
    im = panel.copy(); d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(FONT, 46, index=1); f2 = ImageFont.truetype(FONT, 60, index=1)
    d.text((110, 420), 'yeyk', font=f1, fill=th['pinyin'])
    x = 110
    for i, w in enumerate(['夜莺', '野营', '夜桜', '业余', '夜鹰']):
        d.text((x, 520), f'{i + 1}.{w}', font=f2, fill=th['first'] if i == 0 else th['other']); x += 260
    bg = Image.new('RGBA', im.size, (236, 238, 242, 255)); bg.alpha_composite(im)
    return bg


def main(keys):
    OUT.mkdir(parents=True, exist_ok=True)
    for k in keys:
        th, panel = build(k)
        d = OUT / th['name']; d.mkdir(exist_ok=True)
        panel.save(d / 'panel.png', optimize=True)
        (d / 'skin.ini').write_text(skin_ini(th), encoding='utf-8-sig')
        with zipfile.ZipFile(OUT / f'{th["name"]}.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            z.write(d / 'skin.ini', 'skin.ini'); z.write(d / 'panel.png', 'panel.png')
        preview(th, panel).save(OUT / f'{th["name"]}_预览.png')
        print(k, '→', OUT / f'{th["name"]}.zip')


if __name__ == '__main__':
    main(sys.argv[1:] or list(THEMES))
