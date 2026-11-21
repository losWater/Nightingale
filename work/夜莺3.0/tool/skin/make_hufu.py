"""虎符输入法皮肤（夜莺 / 夜桜）：候选窗配色 + “候选挂件”动图（APNG，透明底，循环播放）。
虎符皮肤是 JSON（colors / layout / material，同 official-skins），挂件写在 overlay 节：image 为 data-URL，
支持 PNG/APNG/GIF；动图由虎符逐帧循环播放、候选窗隐藏即停。
动画：Q版形象上下轻浮、手中键帽光晕呼吸、四角闪星明灭；夜莺加金色音符飘起，夜桜加樱瓣飘落。
输出：~/Downloads/输入法皮肤/虎符/<id>.json（放进虎符数据目录的“皮肤”文件夹）＋ 单独的挂件动图与逐帧预览。
用法：.venv/bin/python tool/skin/make_hufu.py
"""
import base64, io, json, math, random, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_skin import ART, THEMES, cutout, rgb

OUT = Path.home() / 'Downloads/输入法皮肤/虎符'
N, MS = 24, 85                        # 24 帧 × 85ms ≈ 2 秒一圈
OUT_H = 320                           # 输出高度：虎符挂件约 150px 显示，高分屏 2 倍也够清楚
CW, CH = 480, 520                     # 挂件画布（形象高约 440）

HUFU = {
    '夜莺': dict(id='yeying-yuexia', glow_at=(0.335, 0.53), glow='#ffd98a', notes=True, petals=False,
                colors=dict(back='#FBF6ECFF', border='#C9A45CFF', text='#2B2550FF', label='#B48A3CFF', comment='#9A8460FF',
                            hl_text='#2B2550FF', hl_back='#EBDDB8FF', hl_label='#8A6420FF', capsule='#F1E6CCFF')),
    '夜桜': dict(id='yozakura-yingyue', glow_at=(0.31, 0.47), glow='#ff9cc8', notes=False, petals=True,
                colors=dict(back='#FFF4F8FF', border='#E98BB2FF', text='#3A2148FF', label='#C25C8AFF', comment='#A47A92FF',
                            hl_text='#3A2148FF', hl_back='#F8D3E3FF', hl_label='#B0507EFF', capsule='#FBE2EEFF')),
}


def star(d, cx, cy, r, color):
    pts = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.28
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=color)


def note(d, cx, cy, s, color):
    """八分音符：符头＋符干＋符尾。"""
    d.ellipse([cx - s * 0.55, cy - s * 0.38, cx + s * 0.35, cy + s * 0.38], fill=color)
    d.line([(cx + s * 0.3, cy), (cx + s * 0.3, cy - s * 1.6)], fill=color, width=max(2, int(s * 0.16)))
    d.line([(cx + s * 0.3, cy - s * 1.6), (cx + s * 0.85, cy - s * 1.15)], fill=color, width=max(2, int(s * 0.16)))


def frames(key):
    th, hf = THEMES[key], HUFU[key]
    ch = cutout(ART / th['chibi'])
    s = 440 / ch.height
    ch = ch.resize((int(ch.width * s), int(ch.height * s)), Image.LANCZOS)
    if ch.width > CW - 20:
        k = (CW - 20) / ch.width; ch = ch.resize((int(ch.width * k), int(ch.height * k)), Image.LANCZOS)
    ox, oy = (CW - ch.width) // 2, CH - ch.height - 22
    gx, gy = ox + ch.width * hf['glow_at'][0], oy + ch.height * hf['glow_at'][1]
    random.seed(3)
    stars = [(random.uniform(30, CW - 30), random.uniform(20, CH * 0.75), random.uniform(7, 13), random.random()) for _ in range(7)]
    petals = [(random.uniform(0, CW), random.random(), random.uniform(10, 16), random.uniform(0, math.pi), random.uniform(-0.3, 0.3)) for _ in range(9)]
    notes = [(random.uniform(40, CW - 40), random.random(), random.uniform(12, 17)) for _ in range(4)]
    a1 = rgb(th['accent'][0])
    out = []
    for f in range(N):
        t = f / N
        im = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
        bob = round(6 * math.sin(2 * math.pi * t))
        # 键帽光晕（呼吸）
        g = Image.new('RGBA', (CW, CH), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        r = 62 + 10 * math.sin(2 * math.pi * t)
        alpha = int(110 + 70 * (0.5 + 0.5 * math.sin(2 * math.pi * t)))
        gd.ellipse([gx - r, gy + bob - r, gx + r, gy + bob + r], fill=rgb(hf['glow']) + (alpha,))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(26)))
        nd = ImageDraw.Draw(im)
        if hf['notes']:                                                  # 音符在形象身后缓缓上飘、淡入淡出（不挡脸）
            for x, ph, sz in notes:
                p = (t + ph) % 1
                y = CH * 0.78 - p * CH * 0.6
                note(nd, x + 10 * math.sin(2 * math.pi * p), y, sz, rgb('#c9a45c') + (int(255 * math.sin(math.pi * p)),))
        im.alpha_composite(ch, (ox, oy + bob))
        d = ImageDraw.Draw(im)
        for x, y, rr, ph in stars:                                       # 闪星明灭
            k = 0.5 + 0.5 * math.sin(2 * math.pi * (t + ph))
            if k > 0.15:
                star(d, x, y + bob * 0.5, rr * (0.55 + 0.45 * k), (255, 255, 255, int(255 * k)) if hf['petals'] else a1 + (int(255 * k),))
        if hf['petals']:                                                 # 樱瓣飘落
            for x, ph, sz, ang, drift in petals:
                p = (t + ph) % 1
                y = -20 + p * (CH + 40)
                xx = (x + p * 120 * (1 + drift) + 18 * math.sin(2 * math.pi * (p * 2 + ph))) % (CW + 40) - 20
                _petal(d, xx, y, sz, ang + 4 * math.pi * p, rgb(th['accent'][0]) + (int(235 * min(1, 4 * p, 4 * (1 - p))),))
        out.append(im.resize((round(CW * OUT_H / CH), OUT_H), Image.LANCZOS))
    return out


def _petal(d, cx, cy, size, ang, color):
    pts = []
    for i in range(20):
        a = 2 * math.pi * i / 20
        x = size * 0.55 * math.sin(a) * (1 - 0.25 * math.cos(a)); y = size * 0.5 * math.cos(a)
        if y < -size * 0.38: x *= 0.6
        pts.append((cx + x * math.cos(ang) - y * math.sin(ang), cy + x * math.sin(ang) + y * math.cos(ang)))
    d.polygon(pts, fill=color)


def apng(fr):
    buf = io.BytesIO()
    fr[0].save(buf, format='PNG', save_all=True, append_images=fr[1:], duration=MS, loop=0, disposal=1, blend=0, optimize=True)
    return buf.getvalue()


def skin_json(key, data):
    th, hf = THEMES[key], HUFU[key]
    c = hf['colors']
    base = json.load(open(Path.home() / '.cache/hufu/engine/crates/hufu-server/official-skins/hufu-yuebai.json', encoding='utf-8'))
    base['id'], base['name'], base['author'] = hf['id'], th['name'], key
    base['colors'].update({
        'back_color': c['back'], 'border_color': c['border'], 'text_color': c['text'], 'preedit_back_color': c['back'][:7] + '00',
        'candidate_text_color': c['text'], 'candidate_back_color': c['back'][:7] + '00', 'comment_text_color': c['comment'],
        'label_color': c['label'], 'hilited_text_color': c['hl_text'], 'hilited_back_color': c['back'][:7] + '00',
        'hilited_candidate_text_color': c['hl_text'], 'hilited_candidate_back_color': c['hl_back'],
        'hilited_candidate_label_color': c['hl_label'], 'hilited_comment_text_color': c['comment'], 'hilited_label_color': c['hl_label'],
        'hilited_mark_color': c['hl_label'], 'capsule_text_color': c['text'], 'capsule_back_color': c['capsule']})
    base['layout'].update({'corner_radius': 12.0, 'hilited_corner_radius': 9.0, 'border_width': 1.5})
    base['overlay'] = {'enabled': True, 'image': 'data:image/png;base64,' + base64.b64encode(data).decode(),
                       'side': 'right', 'base_height': 150, 'offset_x': 0, 'offset_y': 0, 'gap': 2,
                       'flip_h': False, 'layer': 'below', 'opacity': 100, 'v_align': 'bottom'}
    return base


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for key in HUFU:
        fr = frames(key)
        data = apng(fr)
        name = THEMES[key]['name']
        (OUT / f'{name}_挂件动图.png').write_bytes(data)
        w, h = fr[0].size
        sheet = Image.new('RGBA', (w * 6, h * 2), (236, 238, 242, 255))                     # 逐帧预览（每隔一帧，12 张）
        for i, im in enumerate(fr[::2][:12]):
            sheet.alpha_composite(im, ((i % 6) * w, (i // 6) * h))
        sheet.save(OUT / f'{name}_逐帧预览.png')
        sk = skin_json(key, data)
        (OUT / f'{sk["id"]}.json').write_text(json.dumps(sk, ensure_ascii=False, indent=2), encoding='utf-8')
        print(key, f'{len(data) / 1024:.0f} KB', OUT / f'{sk["id"]}.json')


if __name__ == '__main__':
    main()
