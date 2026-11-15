"""2.4.1 の画面写真を docs/screens_v2.4.1/ に撮る（suite には入れない）。
① 予定の1件を「詳細」で開いた状態 ② 開いてから2分を過ぎて自動で閉じた状態
明るい配色 × iPad 横 1180×820・iPad 縦 1024×1366、1倍。時計は 2026/11/13(金) 10:00（日本時間）から進め、デモデータ（架空）で撮る。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst
try:
    from PIL import Image
except ImportError:
    Image = None

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
DST = os.path.join(APP, 'docs', 'screens_v2.4.1'); os.makedirs(DST, exist_ok=True)
SIZES = [(1180, 820, 'ipad_yoko'), (1024, 1366, 'ipad_tate')]


def small(fp):
    if Image:  # 公開リポジトリを重くしないよう、256色に減らして保存（2.0.0 と同じ）
        Image.open(fp).convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(fp, optimize=True)


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w, h, tag in SIZES:
            ctx = b.new_context(viewport={'width': w, 'height': h}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
            pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.clock.install(time=jst(2026, 11, 13, 10, 0))
            pg.goto('file://' + APP + '/index.html'); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(300)
            pg.evaluate("window.tone=function(){}")
            pg.click('nav button[data-tab=settings]'); pg.click('#thmSeg [data-thm=light]'); pg.wait_for_timeout(200)
            pg.click('#demoIn'); pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを入れました')")
            pg.wait_for_timeout(300)
            pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(300)
            pg.locator('#planList [data-pact=toggle]').first.click(); pg.wait_for_timeout(400)
            pg.evaluate("toastHide()"); pg.mouse.move(0, 0)
            fp = os.path.join(DST, f'01_yotei_shosai_hiraku_{tag}.png'); pg.screenshot(path=fp); small(fp)
            pg.clock.fast_forward(125_000); pg.wait_for_timeout(1500)
            assert pg.locator('#planList .prbody').count() == 0
            # 時計を2分飛ばしたため出る「アプリが止まっていました」の帯（撮影の都合）は閉じてから撮る
            if pg.is_visible('#gapOk'): pg.click('#gapOk'); pg.wait_for_timeout(200)
            pg.evaluate("toastHide()")
            fp = os.path.join(DST, f'02_yotei_2fungo_tojiru_{tag}.png'); pg.screenshot(path=fp); small(fp)
            ctx.close()
        b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
