"""2.0.0（試作版）：全タブ・主なダイアログを両配色・3つの幅で開き、JSエラーがないこと・横にはみ出さないこと、
配色が実際に効いていること（ダイアログ・パネル・タブの面の色が配色で変わる）を assert で確かめる。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'
TABS = ['active', 'plan', 'new', 'calendar', 'history', 'stats', 'patients', 'tags', 'settings']
SIZES = [(1180, 820), (1024, 1366), (390, 844)]


def main():
    errs = []
    checked = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w, h in SIZES:
            ctx = b.new_context(viewport={'width': w, 'height': h}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
            pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.clock.set_fixed_time(jst(2026, 11, 10, 14, 32))
            pg.goto(URL); pg.wait_for_timeout(700)
            # 開始画面（両配色）
            for th in ['light', 'dark']:
                pg.evaluate(f"document.documentElement.dataset.theme='{th}'")
                assert pg.locator('#startOv').is_visible()
                assert pg.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth')
            pg.click('#startOv'); pg.wait_for_timeout(200)
            pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(1500)

            def no_overflow(where):
                nonlocal checked
                r = pg.evaluate("""()=>{const d=document.documentElement;const dl=[...document.querySelectorAll('dialog[open]')].map(x=>[x.scrollWidth,x.clientWidth]);
                  return {sw:d.scrollWidth,cw:d.clientWidth,dl}}""")
                assert r['sw'] <= r['cw'], (w, where, '横にはみ出し', r)
                for sw, cw in r['dl']:
                    assert sw <= cw + 1, (w, where, 'ダイアログが横にはみ出し', r)
                checked += 1

            bgs = {}
            for th in ['light', 'dark']:
                pg.click('nav button[data-tab=settings]'); pg.click(f'#thmSeg [data-thm={th}]'); pg.wait_for_timeout(200)
                assert pg.evaluate('document.documentElement.dataset.theme') == th
                for t in TABS:
                    pg.click(f'nav button[data-tab={t}]'); pg.wait_for_timeout(250)
                    assert pg.locator(f'#sec-{t}').is_visible(), t
                    no_overflow(t)
                bgs[th] = pg.evaluate("""()=>{const g=s=>getComputedStyle(document.querySelector(s)).backgroundColor;return [g('#themePanel'),g('nav'),g('.topbar'),getComputedStyle(document.body).color]}""")

                # 主なダイアログ
                def dlg(name, opener, close='#dlgActions button >> nth=0', sel='#dlg'):
                    opener(); pg.wait_for_timeout(300)
                    assert pg.locator(f'{sel}[open]').count() == 1, (w, th, name, 'ダイアログが開かない')
                    bg = pg.evaluate(f"getComputedStyle(document.querySelector('{sel}')).backgroundColor")
                    bgs.setdefault(th + ':dlg', bg)
                    no_overflow(name)
                    pg.click(close); pg.wait_for_timeout(250)
                    assert pg.locator(f'{sel}[open]').count() == 0, (w, th, name, '閉じない')

                def on_card(act):
                    def f():
                        pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(200)
                        c = pg.locator('#activeList .card.st-overdue').first
                        if c.locator(f'[data-act={act}]').count() == 0:
                            c.locator('[data-act=open]').click(); pg.wait_for_timeout(300)
                            c = pg.locator('#activeList .card.st-overdue:not(.crow)').first
                        c.locator(f'[data-act={act}]').click()
                    return f
                dlg('帰院', on_card('return'))
                dlg('対応記録', on_card('log'))
                dlg('帰院予定を変更', on_card('extend'))
                dlg('内容を修正', on_card('edit'))
                dlg('はぐれ・行方不明', on_card('lost'))
                pg.evaluate("Object.keys(openUntil).forEach(k=>delete openUntil[k]);lastSig='';tick()")

                def go():
                    pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(200)
                    pg.locator('#planList [data-pact=go]').first.click()
                dlg('出発（GO）', go)

                def ptedit():
                    pg.click('nav button[data-tab=patients]'); pg.wait_for_timeout(200)
                    pg.locator('#ptTable [data-ptedit]').first.click()
                dlg('患者の修正', ptedit)

                def hist():
                    pg.click('nav button[data-tab=history]'); pg.wait_for_timeout(200)
                    pg.locator('#hTable tbody tr.click').first.click()
                dlg('日別一覧の記録', hist)

                def confirm():
                    pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(200)
                    pg.locator('#planList [data-pact=cancel]').first.click()
                dlg('確認', confirm, close='#cdlgNo', sel='#cdlg')

                # 見守り確認（全画面）
                pg.evaluate("lastInteract=Date.now()-(settings.idleMin+1)*60000;outings.filter(o=>o.status==='out').forEach(o=>{o.dueAt=Date.now()+3*3600000;});lastSig='';tick()")
                pg.wait_for_timeout(1300)
                assert pg.locator('#watchOv').is_visible(), (w, th, '見守り確認が出ない')
                no_overflow('見守り確認')
                ov = pg.evaluate("getComputedStyle(document.getElementById('watchOv')).color")
                assert ov == ('rgb(20, 35, 58)' if th == 'light' else 'rgb(242, 246, 251)'), (th, ov)
                pg.click('#watchOv'); pg.wait_for_timeout(200)
                # 元に戻す（デモを入れ直す）
                pg.click('nav button[data-tab=settings]'); pg.click('#demoOut'); pg.wait_for_timeout(800)
                pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(1500)

            # 配色が実際に効いている（明るい／暗いで面と文字の色が違う）
            assert bgs['light'] != bgs['dark'], bgs
            assert bgs['light:dlg'] != bgs['dark:dlg'], bgs
            assert bgs['light'][3] == 'rgb(20, 35, 58)' and bgs['dark'][3] == 'rgb(242, 246, 251)', bgs
            ctx.close()
        b.close()
    print('checked', checked)
    assert checked >= 3 * 2 * (len(TABS) + 10)
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
