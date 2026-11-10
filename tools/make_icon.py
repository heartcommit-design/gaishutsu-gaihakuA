#!/usr/bin/env python3
"""試作版（2.0.x）のホーム画面アイコンを作る。

図案：明るい青緑→青の斜めグラデーションの地に、ガラス風の白い半透明の板。
板の中に時間軸の帯（角丸バー3本：白・白・琥珀）と、それを貫く白い縦線（＝現在）。
下に白い太字「外出」、右上に小さく「試作」。

4倍の大きさで描いてから縮小し、輪郭をなめらかにする。外部のフォント・画像は使わず、
端末にある日本語フォント（fc-list :lang=ja）を探して使う。
使い方：python3 tools/make_icon.py   （リポジトリのいちばん上に icon-180/192/512.png を書き出す）
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 512          # 設計の基準サイズ（座標は 512px 版で考える）
SS = 4              # 4倍で描く
W = BASE * SS

C_TOP = (0x19, 0xb3, 0xa6)   # 左上：青緑
C_BOT = (0x2a, 0x6f, 0xd6)   # 右下：青
AMBER = (0xff, 0xc4, 0x57)
WHITE = (255, 255, 255)


def s(v):
    """512px 基準の値を描画用（4倍）に直す"""
    return int(round(v * SS))


def find_jp_font():
    """端末にある日本語のゴシック（太字）を探す。無ければ None。"""
    try:
        out = subprocess.run(['fc-list', ':lang=ja', 'file', 'family', 'style', 'index'],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return None
    cands = []
    for line in out.splitlines():
        path = line.split(':', 1)[0].strip()
        low = line.lower()
        if 'serif' in low or 'mono' in low:
            continue
        idx = 0
        if 'index=' in line:
            try:
                idx = int(line.rsplit('index=', 1)[1].split(':')[0].split(',')[0])
            except ValueError:
                idx = 0
        # 日本語向け（JP）を優先、太さは Black > Bold > Heavy > Medium
        score = 0
        if ' jp' in low or 'japan' in low or 'gothic' in low or 'ipa' in low:
            score += 10
        for w, pts in (('black', 6), ('heavy', 5), ('bold', 4), ('medium', 2)):
            if w in low:
                score += pts
                break
        cands.append((score, path, idx))
    cands.sort(key=lambda c: -c[0])
    for _, path, idx in cands:
        try:
            ImageFont.truetype(path, 40, index=idx)
            return path, idx
        except Exception:
            continue
    return None


def gradient():
    """左上→右下の斜めグラデーション（不透明）"""
    small = Image.new('RGB', (256, 256))
    px = small.load()
    for y in range(256):
        for x in range(256):
            t = (x + y) / 510
            px[x, y] = tuple(int(round(a + (b - a) * t)) for a, b in zip(C_TOP, C_BOT))
    return small.resize((W, W), Image.BICUBIC).convert('RGBA')


def overlay(img, draw_fn, blur=0):
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    if blur:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(img, layer)


def text_center(d, cx, top, txt, font, fill):
    """文字の見た目の上端を top にそろえ、横は cx で中央に置く"""
    l, t, r, b = d.textbbox((0, 0), txt, font=font)
    d.text((cx - (l + r) / 2, top - t), txt, font=font, fill=fill)


def build(with_text=True, with_badge=False):
    img = gradient()

    # 全体にやわらかい光（左上を少し明るく）
    img = overlay(img, lambda d: d.ellipse([s(-120), s(-160), s(330), s(260)], fill=(255, 255, 255, 34)), blur=s(60))

    # --- ガラスの板 ---
    px0, py0, px1, py1 = 76, 92, 436, 300
    rad = 40
    # 影
    img = overlay(img, lambda d: d.rounded_rectangle([s(px0), s(py0 + 10), s(px1), s(py1 + 14)], s(rad), fill=(10, 40, 90, 60)), blur=s(12))
    # 板本体（白の半透明）＋縁
    img = overlay(img, lambda d: d.rounded_rectangle([s(px0), s(py0), s(px1), s(py1)], s(rad),
                                                     fill=(255, 255, 255, 58), outline=(255, 255, 255, 150), width=s(3)))
    # 上辺のハイライト（板の上半分だけ明るく）
    hl = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle([s(px0 + 3), s(py0 + 3), s(px1 - 3), s(py1 - 3)], s(rad - 3), fill=(255, 255, 255, 70))
    mask = Image.new('L', img.size, 0)
    ImageDraw.Draw(mask).rectangle([0, s(py0), W, s(py0 + 46)], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(s(10)))
    hl.putalpha(Image.composite(hl.getchannel('A'), Image.new('L', img.size, 0), mask))
    img = Image.alpha_composite(img, hl)
    img = overlay(img, lambda d: d.line([s(px0 + rad), s(py0 + 2), s(px1 - rad), s(py0 + 2)], fill=(255, 255, 255, 230), width=s(3)))

    # --- 時間軸の帯（3本）---
    bh = 34
    bars = [
        (112, 300, 128, (255, 255, 255, 245)),
        (170, 400, 179, (255, 255, 255, 245)),
        (130, 340, 230, AMBER + (255,)),
    ]
    for x0, x1, y0, col in bars:
        img = overlay(img, lambda d, x0=x0, x1=x1, y0=y0: d.rounded_rectangle([s(x0), s(y0 + 4), s(x1), s(y0 + bh + 4)], s(bh / 2), fill=(10, 50, 100, 55)), blur=s(4))
        img = overlay(img, lambda d, x0=x0, x1=x1, y0=y0, col=col: d.rounded_rectangle([s(x0), s(y0), s(x1), s(y0 + bh)], s(bh / 2), fill=col))

    # --- 「現在」の縦線（3本を貫く）---
    nx = 262
    def now_line(d):
        d.rounded_rectangle([s(nx - 5), s(110), s(nx + 5), s(282)], s(5), fill=WHITE + (255,), outline=(20, 80, 150, 255), width=s(2))
        d.ellipse([s(nx - 11), s(102), s(nx + 11), s(124)], fill=WHITE + (255,), outline=(20, 80, 150, 255), width=s(2))
    img = overlay(img, lambda d: d.rounded_rectangle([s(nx - 6), s(112), s(nx + 8), s(286)], s(6), fill=(10, 40, 90, 70)), blur=s(4))
    img = overlay(img, now_line)

    font = find_jp_font()
    if with_text and font:
        path, idx = font
        # 「外出」：文字の高さ約110px
        f_main = ImageFont.truetype(path, s(124), index=idx)
        img = overlay(img, lambda d: text_center(d, s(256), s(332 + 5), '外出', f_main, (10, 45, 100, 90)), blur=s(5))
        img = overlay(img, lambda d: text_center(d, s(256), s(332), '外出', f_main, WHITE + (255,)))
        if with_badge:
            # 右上の小さな「試作」：琥珀の角丸札に濃い文字（板の右上の角に重ねる）
            f_b = ImageFont.truetype(path, s(40), index=idx)
            bx0, by0, bx1, by1 = 340, 52, 462, 104
            img = overlay(img, lambda d: d.rounded_rectangle([s(bx0), s(by0 + 4), s(bx1), s(by1 + 4)], s(14), fill=(10, 40, 90, 70)), blur=s(4))
            img = overlay(img, lambda d: d.rounded_rectangle([s(bx0), s(by0), s(bx1), s(by1)], s(14), fill=AMBER + (255,)))
            def badge(d):
                l, t, r, b = d.textbbox((0, 0), '試作', font=f_b)
                cx, cy = s((bx0 + bx1) / 2), s((by0 + by1) / 2)
                d.text((cx - (l + r) / 2, cy - (t + b) / 2), '試作', font=f_b, fill=(60, 36, 0, 255))
            img = overlay(img, badge)
    return img.convert('RGB'), bool(font)


def main():
    img, has_font = build()
    if not has_font:
        print('日本語フォントが見つからないため、文字なしの図案で作りました', file=sys.stderr)
    for size in (512, 192, 180):
        out = img.resize((size, size), Image.LANCZOS)
        out.save(os.path.join(ROOT, f'icon-{size}.png'), optimize=True)
        print('wrote', f'icon-{size}.png')


if __name__ == '__main__':
    main()
