"""2.2.0 の画面写真を docs/screens_v2.2.0/ に撮る（suite には入れない）。
デモを入れた直後の外出・外泊中（時間軸と一覧、両配色 × iPad 横・縦・スマホ）と、
歴史上の人物の名前を使った架空の4人それぞれの詳細（服装写真が見える状態、iPad 横・明るい）。
時計を 2026/11/13 10:00（日本時間）に固定し、デモデータ（架空）で撮る。1倍で撮る。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst
try:
    from PIL import Image
except ImportError:
    Image = None


def small(fp):
    if Image:  # 公開リポジトリを重くしないよう、256色に減らして保存（2.0.0 と同じ）
        Image.open(fp).convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(fp, optimize=True)

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
DST = os.path.join(APP, 'docs', 'screens_v2.2.0'); os.makedirs(DST, exist_ok=True)
SIZES = [(1180, 820, 'ipad_yoko'), (1024, 1366, 'ipad_tate'), (390, 844, 'phone')]
BUSHO = [('D1051', 'mitsuhide'), ('D1052', 'nobunaga'), ('D1053', 'ieyasu'), ('D1054', 'mitsunari')]


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w, h, tag in SIZES:
            ctx = b.new_context(viewport={'width': w, 'height': h}, timezone_id='Asia/Tokyo', device_scale_factor=1)
            pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.clock.set_fixed_time(jst(2026, 11, 13, 10, 0))
            pg.goto('file://' + APP + '/index.html'); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(300)
            pg.evaluate("window.tone=function(){}")  # 撮影中は鳴らさない

            def shot(name, full=False):
                sw = pg.evaluate('document.documentElement.scrollWidth')
                assert sw <= w, f'{name} {tag}: 横にはみ出し {sw}>{w}'
                pg.evaluate("document.getElementById('toast').style.display='none'")
                pg.wait_for_timeout(150)
                fp = os.path.join(DST, f'{name}_{tag}.png')
                pg.screenshot(path=fp, full_page=full, animations='disabled'); small(fp)

            def theme(th):
                pg.click('nav button[data-tab=settings]'); pg.click(f'#thmSeg [data-thm={th}]'); pg.wait_for_timeout(200)

            pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(1500)
            if pg.locator('#gapBar').is_visible():
                pg.click('#gapOk')
            for th in ['light', 'dark']:
                theme(th)
                pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(300)
                for view, lbl in [('timeline', 'jikanjiku'), ('list', 'ichiran')]:
                    pg.click(f'#viewSeg [data-view={view}]'); pg.wait_for_timeout(400)
                    shot(f'demo_{lbl}_{th}', full=True)
                pg.click('#viewSeg [data-view=timeline]'); pg.wait_for_timeout(300)
            if tag == 'ipad_yoko':
                theme('light')
                pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(300)
                for pid, key in BUSHO:
                    pg.evaluate("(pid)=>{for(const k in openUntil)delete openUntil[k];openUntil[outings.find(o=>o.pid===pid).id]=Date.now()+600000;lastSig='';tick();}", pid)
                    pg.wait_for_timeout(500)
                    card = pg.locator('#activeList .card:not(.crow)')
                    assert card.count() == 1
                    img = card.locator('img.thumb')
                    assert img.count() == 1 and img.evaluate("e=>e.decode().then(()=>e.naturalWidth>0)"), key
                    card.evaluate("e=>e.scrollIntoView({block:'center'})"); pg.wait_for_timeout(200)
                    bb = card.bounding_box()
                    pg.evaluate("document.getElementById('toast').style.display='none'")
                    fp = os.path.join(DST, f'shosai_{key}_{tag}.png')
                    pg.screenshot(path=fp, clip={'x': 0, 'y': max(0, bb['y'] - 12), 'width': w, 'height': min(h - max(0, bb['y'] - 12), bb['height'] + 24)}, animations='disabled')
                    small(fp)
            ctx.close()
        b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
