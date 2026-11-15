"""2.4.0 の画面写真を docs/screens_v2.4.0/ に撮る（suite には入れない）。
① 予定の「出発（GO）」で看護師を入れ忘れた状態（ダイアログの中・欄のそばの知らせ）
② 予定の一覧（たたんだ状態）③ 1件を「詳細」で開いた状態 ④ 1か月分（画面全体）
⑤ 新規登録で患者を選んだ状態（上端）⑥ 同じく下までスクロールした状態
⑦ 最悪の場合（アラーム帯・アラーム音無効の帯＋タブ＋下のバー）の新規登録
⑧ カレンダー（1か月の予定入り）⑨ 看護師名の候補（30人。「ほかの看護師」を開いた状態）
両配色（明るい／暗い）× iPad 横 1180×820・iPad 縦 1024×1366、1倍。時計は 2026/11/13(金) 10:00（日本時間）に固定し、デモデータ（架空）で撮る。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst
try:
    from PIL import Image
except ImportError:
    Image = None

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
DST = os.path.join(APP, 'docs', 'screens_v2.4.0'); os.makedirs(DST, exist_ok=True)
SIZES = [(1180, 820, 'ipad_yoko'), (1024, 1366, 'ipad_tate')]


def small(fp):
    if Image:  # 公開リポジトリを重くしないよう、256色に減らして保存（2.0.0 と同じ）
        Image.open(fp).convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(fp, optimize=True)


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w, h, tag in SIZES:
            for th in ['light', 'dark']:
                ctx = b.new_context(viewport={'width': w, 'height': h}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
                pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
                pg.clock.set_fixed_time(jst(2026, 11, 13, 10, 0))
                pg.goto('file://' + APP + '/index.html'); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(300)
                pg.evaluate("window.tone=function(){}")
                pg.click('nav button[data-tab=settings]'); pg.click(f'#thmSeg [data-thm={th}]'); pg.wait_for_timeout(200)
                pg.click('#demoIn'); pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを入れました')")
                pg.wait_for_timeout(300)
                if pg.locator('#prLater').is_visible():
                    pg.click('#prLater')   # 8時の控えのお知らせは閉じておく（アラーム帯は残す）

                def shot(name, full=False):
                    pg.wait_for_timeout(1100)
                    sw = pg.evaluate('document.documentElement.scrollWidth')
                    assert sw <= w, f'{name} {th} {tag}: 横にはみ出し {sw}>{w}'
                    pg.evaluate("document.getElementById('toast').style.display='none'")
                    pg.wait_for_timeout(120)
                    fp = os.path.join(DST, f'{name}_{th}_{tag}.png')
                    pg.screenshot(path=fp, full_page=full); small(fp)

                # ① GO で看護師を入れ忘れ
                pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(300)
                pg.locator('#planList [data-pact=go]').first.click(); pg.wait_for_timeout(300)
                pg.locator('#goTagBtns [data-gotag="T-04"]').click()
                pg.click('#dlgActions button.ok'); pg.wait_for_timeout(300)
                shot('go_kangoshi_wasure')
                pg.click('#dlgActions button:has-text("やめる")'); pg.wait_for_timeout(200)
                # ②③④ 予定の一覧
                pg.evaluate('window.scrollTo(0,0)')
                shot('yotei_tatami')
                pg.locator('#planList [data-pact=toggle]').nth(1).click(); pg.wait_for_timeout(400)
                shot('yotei_1ken_hiraku')
                pg.locator('#planList [data-pact=toggle]').nth(1).click(); pg.wait_for_timeout(300)
                shot('yotei_1kagetsu', full=True)
                # ⑤⑥ 新規登録で患者を選ぶ
                pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(300)
                pg.fill('#pSearch', 'D1030'); pg.wait_for_timeout(200)
                pg.locator('#pChips [data-pt]').first.click(); pg.wait_for_timeout(900)
                pg.evaluate('window.scrollTo(0,0)')
                shot('shinki_kanja_ue')
                pg.evaluate('window.scrollTo(0,document.documentElement.scrollHeight)')
                shot('shinki_kanja_shita')
                # ⑨ 看護師名の候補（30人）
                pg.locator('input[name=departNurse] + .nchips [data-nmore]').click(); pg.wait_for_timeout(300)
                pg.evaluate("""()=>{const e=document.querySelector('#newForm .nall');const r=e.getBoundingClientRect();
                  window.scrollTo({top:Math.max(0,scrollY+r.bottom-(innerHeight-document.getElementById('regBar').offsetHeight)+16),behavior:'instant'});}""")
                shot('kangoshi_30nin')
                pg.locator('input[name=departNurse] + .nchips [data-nmore]').click(); pg.wait_for_timeout(200)
                # ⑦ 最悪の場合：アラーム帯＋アラーム音無効の帯＋タブ＋下のバー
                pg.evaluate("settings.soundOff=true;updateSoundBtn();lastSig='';tick()"); pg.wait_for_timeout(300)
                pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(100)
                pg.evaluate("""()=>{const e=document.getElementById('dueCol');const r=e.getBoundingClientRect();window.scrollTo({top:scrollY+r.top-stickTop()-12,behavior:'instant'});}""")
                shot('saiaku_shinki')
                pg.evaluate("settings.soundOff=false;updateSoundBtn();lastSig='';tick()")
                # ⑧ カレンダー
                pg.click('nav button[data-tab=calendar]'); pg.wait_for_timeout(300)
                shot('calendar_1kagetsu')
                ctx.close()
        b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
