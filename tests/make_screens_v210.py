"""2.1.0 の画面写真を docs/screens_v2.1.0/ に撮る（suite には入れない）。
アラーム音を無効にしている間のヘッダーと赤い帯（両配色 × iPad 横・縦・スマホ、アラームが出ている状態も）、
開始画面の注意、確認ダイアログ、音量0の表示（ヘッダー・説明ダイアログ・設定の注意）、「このアプリについて」。
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
    if Image:  # 公開リポジトリを重くしないよう、256色に減らして保存（PIL があるときだけ。2.0.0 と同じ）
        Image.open(fp).convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(fp, optimize=True)

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
DST = os.path.join(APP, 'docs', 'screens_v2.1.0'); os.makedirs(DST, exist_ok=True)
SIZES = [(1180, 820, 'ipad_yoko'), (1024, 1366, 'ipad_tate'), (390, 844, 'phone')]


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
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
                pg.evaluate("setSoundOff(false)"); pg.wait_for_timeout(200)
                pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(300)
                if th == 'light' or tag == 'ipad_yoko':
                    pg.click('#soundBtn'); pg.wait_for_timeout(250)
                    shot(f'kakunin_{th}')
                    pg.click('#dlgActions .bad'); pg.wait_for_timeout(300)
                else:
                    pg.evaluate("setSoundOff(true)"); pg.wait_for_timeout(300)
                shot(f'mukou_alarm_{th}')            # 無効中：ヘッダー・アラーム帯（音は無効）・赤い帯
                if tag == 'ipad_yoko':
                    pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(200)
                    shot(f'mukou_yotei_{th}')         # ほかのタブでも帯が出る
                pg.click('nav button[data-tab=settings]'); pg.wait_for_timeout(200)
                pg.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(150)
                shot(f'mukou_settei_{th}')            # 下まで動かしても帯が見える
                pg.evaluate("window.scrollTo(0,0)")
                # 開始画面の注意
                pg.reload(); pg.wait_for_timeout(800)
                shot(f'start_mukou_{th}')
                pg.click('#startOv'); pg.wait_for_timeout(300); pg.evaluate("window.tone=function(){}")
                # 音量0
                pg.click('#muteOn'); pg.wait_for_timeout(300)
                pg.click('nav button[data-tab=settings]'); pg.fill('#sVol', '0'); pg.click('#sSave'); pg.wait_for_timeout(200)
                pg.locator('#sVol').scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0,-160)")
                shot(f'onryo0_settei_{th}')
                pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(200)
                pg.click('#soundBtn'); pg.wait_for_timeout(250)
                shot(f'onryo0_dialog_{th}')
                pg.click('#dlgActions button:has-text("閉じる")')
                pg.click('nav button[data-tab=settings]'); pg.fill('#sVol', '0.7'); pg.click('#sSave'); pg.wait_for_timeout(200)
                # このアプリについて
                # 上に固定した帯が欄に重ならないよう、撮る間だけ帯を固定しない
                pg.evaluate("document.querySelector('.topbar').style.position='static'")
                pg.locator('#aboutPanel').scroll_into_view_if_needed(); pg.wait_for_timeout(100)
                fp = os.path.join(DST, f'about_{th}_{tag}.png')
                pg.locator('#aboutPanel').screenshot(path=fp, animations='disabled'); small(fp)
                pg.evaluate("document.querySelector('.topbar').style.position=''")
                pg.evaluate("window.scrollTo(0,0)")
            ctx.close()
        b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
