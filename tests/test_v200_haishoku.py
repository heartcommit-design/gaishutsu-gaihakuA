"""2.0.0（試作版）：画面の明るさ（自動／明るい／暗い）とガラス調の2配色。
- 設定の3択とヘッダーのボタンで data-theme が変わる
- 自動のときは時刻（Playwright の時計を固定・進める）で切り替わる／暗くする時間帯の変更が効く
- 再読み込み後も保たれ、最初の描画の前に決まっている
- 「透明感を弱める」でぼかしが消える
- 両配色で主要な文字のコントラスト比が 4.5 以上（画面上の実際の色から計算）
- アラーム帯・予定超過カード・音が出ない時のボタンが、両配色で不透明・点滅のまま
- 印刷（emulate_media print）では配色に関係なく白地・黒文字・ガラスなし
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst, contrast

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'


def theme(pg):
    return pg.evaluate('document.documentElement.dataset.theme')


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1180, 'height': 820}, timezone_id='Asia/Tokyo', device_scale_factor=1)
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        dec = ctx.new_page()
        pg.clock.set_fixed_time(jst(2026, 11, 10, 14, 0))
        pg.goto(URL); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(200)

        # 初期値は「自動」・18:00〜翌7:00。14時なので明るい
        assert pg.evaluate('[settings.themeMode,settings.darkFrom,settings.darkTo,settings.glassOff]') == ['auto', '18:00', '07:00', False]
        assert theme(pg) == 'light'
        assert pg.inner_text('#themeBtn') == '画面：自動（明るい）', pg.inner_text('#themeBtn')

        # ---- ヘッダーのボタン：押すたびに 自動→明るい→暗い→自動
        pg.click('#themeBtn'); assert theme(pg) == 'light' and pg.inner_text('#themeBtn') == '画面：明るい'
        pg.click('#themeBtn'); assert theme(pg) == 'dark' and pg.inner_text('#themeBtn') == '画面：暗い'
        pg.wait_for_timeout(200)
        assert pg.evaluate("dbGet('settings','main').then(s=>s.themeMode)") == 'dark', '設定（IndexedDB）に保存されていない'
        pg.click('#themeBtn'); assert theme(pg) == 'light' and pg.inner_text('#themeBtn') == '画面：自動（明るい）'
        assert pg.evaluate('settings.themeMode') == 'auto'

        # ---- 設定の3択
        pg.click('nav button[data-tab=settings]'); pg.wait_for_timeout(200)
        assert pg.locator('#themePanel').is_visible() and '画面の明るさ' in pg.inner_text('#themePanel')
        pg.click('#thmSeg [data-thm=dark]'); assert theme(pg) == 'dark'
        assert pg.get_attribute('#thmSeg [data-thm=dark]', 'aria-pressed') == 'true'
        pg.click('#thmSeg [data-thm=light]'); assert theme(pg) == 'light'
        pg.click('#thmSeg [data-thm=auto]'); assert theme(pg) == 'light'
        assert pg.inner_text('#themeBtn') == '画面：自動（明るい）'

        # ---- 自動：時刻をまたぐと、画面を開いたまま切り替わる（毎秒の見回りに乗せている）
        def at(h, mi, s=0):
            pg.clock.set_fixed_time(jst(2026, 11, 10, h, mi, s)); pg.wait_for_timeout(1300)
        at(17, 59, 50); assert theme(pg) == 'light'
        at(18, 0, 5); assert theme(pg) == 'dark', '18:00 を過ぎても暗くならない'
        assert pg.inner_text('#themeBtn') == '画面：自動（暗い）'
        pg.clock.set_fixed_time(jst(2026, 11, 11, 6, 59)); pg.wait_for_timeout(1300); assert theme(pg) == 'dark'
        pg.clock.set_fixed_time(jst(2026, 11, 11, 7, 0, 5)); pg.wait_for_timeout(1300); assert theme(pg) == 'light', '7:00 を過ぎても明るくならない'
        pg.click('#gapOk') if pg.locator('#gapBar').is_visible() else None

        # ---- 暗くする時間帯を変える（20:00〜翌5:00）
        pg.select_option('#thmFrom', '20:00'); pg.select_option('#thmTo', '05:00'); pg.wait_for_timeout(200)
        assert pg.evaluate("dbGet('settings','main').then(s=>[s.darkFrom,s.darkTo])") == ['20:00', '05:00']
        assert pg.locator('#thmToPre').is_visible()
        pg.clock.set_fixed_time(jst(2026, 11, 11, 18, 30)); pg.wait_for_timeout(1300); assert theme(pg) == 'light'
        pg.clock.set_fixed_time(jst(2026, 11, 11, 20, 10)); pg.wait_for_timeout(1300); assert theme(pg) == 'dark'
        pg.clock.set_fixed_time(jst(2026, 11, 12, 5, 30)); pg.wait_for_timeout(1300); assert theme(pg) == 'light'
        # 同じ日の中の時間帯（12:00〜13:00）も効く
        pg.select_option('#thmFrom', '12:00'); pg.select_option('#thmTo', '13:00'); pg.wait_for_timeout(200)
        assert not pg.locator('#thmToPre').is_visible()
        pg.clock.set_fixed_time(jst(2026, 11, 12, 12, 30)); pg.wait_for_timeout(1300); assert theme(pg) == 'dark'
        pg.clock.set_fixed_time(jst(2026, 11, 12, 13, 30)); pg.wait_for_timeout(1300); assert theme(pg) == 'light'

        # ---- 再読み込み後も保たれる（最初の描画の前に決まっている）
        pg.click('#thmSeg [data-thm=dark]'); pg.wait_for_timeout(300)
        pg.goto(URL, wait_until='commit')
        pg.wait_for_selector('#startOv', state='attached')
        assert theme(pg) == 'dark', '開いた直後（データを読む前）に暗い配色になっていない'
        pg.wait_for_timeout(700)
        assert theme(pg) == 'dark' and pg.evaluate('settings.themeMode') == 'dark'
        # 開始画面も配色に従う（暗い背景・明るい文字）
        bgc = pg.evaluate("getComputedStyle(document.getElementById('startOv')).color")
        assert bgc == 'rgb(242, 246, 251)', bgc
        pg.screenshot(path=OUT + '/v200_start_dark.png')
        pg.click('#startOv'); pg.wait_for_timeout(200)
        # 時間帯（12:00〜13:00）も保たれている
        pg.click('nav button[data-tab=settings]'); pg.wait_for_timeout(200)
        assert pg.input_value('#thmFrom') == '12:00' and pg.input_value('#thmTo') == '13:00'
        # 写し（localStorage）が消えても、本体（IndexedDB）から戻る
        pg.evaluate("localStorage.removeItem('gaishutsu_shisaku_theme')")
        pg.reload(); pg.wait_for_timeout(800)
        assert theme(pg) == 'dark' and pg.evaluate("JSON.parse(localStorage.getItem('gaishutsu_shisaku_theme')).mode") == 'dark'
        pg.click('#startOv'); pg.wait_for_timeout(200)

        # ---- 透明感を弱める
        pg.click('nav button[data-tab=settings]'); pg.wait_for_timeout(200)
        bf = "s=>getComputedStyle(document.querySelector(s)).backdropFilter"
        for sel in ['#themePanel', 'nav', '.topbar']:
            assert pg.evaluate(bf, sel) != 'none', sel
        pg.check('#thmGlass'); pg.wait_for_timeout(200)
        assert pg.evaluate('document.documentElement.dataset.glass') == 'off'
        for sel in ['#themePanel', 'nav', '.topbar']:
            assert pg.evaluate(bf, sel) == 'none', sel
        a = pg.evaluate("getComputedStyle(document.getElementById('themePanel')).backgroundColor")
        assert a.startswith('rgb('), f'透明感を弱めても面が半透明のまま：{a}'
        pg.reload(); pg.wait_for_timeout(700); pg.click('#startOv')
        assert pg.evaluate('document.documentElement.dataset.glass') == 'off' and pg.evaluate(bf, 'nav') == 'none'
        pg.click('nav button[data-tab=settings]'); pg.uncheck('#thmGlass'); pg.wait_for_timeout(200)
        assert pg.evaluate(bf, 'nav') != 'none'

        # ---- デモデータ（架空）を入れて、両配色で読みやすさ・目立ち方を確かめる
        pg.clock.set_fixed_time(jst(2026, 11, 13, 10, 0)); pg.wait_for_timeout(1200)
        if pg.locator('#gapBar').is_visible():
            pg.click('#gapOk')
        pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(1500)
        pg.evaluate("document.getElementById('toast').style.display='none'")
        assert pg.locator('#banner.on').count() == 1 and pg.locator('.card.st-overdue').count() == 1

        results = []
        for th in ['light', 'dark']:
            pg.click('nav button[data-tab=settings]'); pg.click(f'#thmSeg [data-thm={th}]'); pg.wait_for_timeout(200)
            assert theme(pg) == th
            pg.evaluate("document.getElementById('toast').style.display='none'")

            # アラーム帯：不透明の赤・点滅
            bn = pg.evaluate("(()=>{const c=getComputedStyle(document.getElementById('banner'));return [c.animationName,c.backgroundColor,c.display]})()")
            assert bn[0] in ('flash', 'flash2') and bn[2] == 'flex', bn
            assert bn[1].startswith('rgb('), f'アラーム帯が半透明 {bn}'
            # 予定超過カード：不透明・脈動・ぼかしなし
            pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(300)
            od = pg.evaluate("(()=>{const c=getComputedStyle(document.querySelector('#activeList .card.st-overdue'));return [c.animationName,c.backgroundColor,c.backdropFilter]})()")
            assert od[0] == 'pulse' and od[1].startswith('rgb(') and od[2] == 'none', od
            # 音が出ない時のボタン：不透明の赤・点滅
            sb = pg.evaluate("(()=>{const b=document.getElementById('soundBtn');const had=b.classList.contains('off');b.classList.add('off');const c=getComputedStyle(b);const r=[c.animationName,c.backgroundColor,c.color];if(!had)b.classList.remove('off');return r})()")
            assert sb[0] == 'blink' and sb[1] == 'rgb(198, 40, 40)' and sb[2] == 'rgb(255, 255, 255)', sb

            # コントラスト比（画面上の実際の色）
            def chk(name, loc):
                assert loc.count() >= 1, name
                r = contrast(pg, loc.first, dec)
                results.append((th, name, round(r, 2)))
                assert r >= 4.5, f'{th}: {name} のコントラスト比 {r:.2f} < 4.5'

            pg.evaluate("window.scrollTo(0,0)")
            chk('アプリ名', pg.locator('header h1'))
            chk('時計', pg.locator('#clock'))
            chk('画面ボタン', pg.locator('#themeBtn'))
            chk('タブ（選択中）', pg.locator('nav button.active'))
            chk('タブ（他）', pg.locator('nav button[data-tab=calendar]'))
            chk('件数バッジ', pg.locator('#cntActive'))
            chk('見出し', pg.locator('#sec-active h2'))
            chk('印刷ボタン', pg.locator('#printBtn'))
            for st in ['overdue', 'soon', 'ok']:
                card = pg.locator(f'#activeList .card.st-{st}').first
                nm = card.locator('.name'); chk(f'氏名（{st}）', nm)
                chk(f'残り時間（{st}）', card.locator('[data-count]'))
                chk(f'状態ラベル（{st}）', card.locator('.lbl'))
                chk(f'帰院したボタン（{st}）', card.locator('[data-act=return]'))
                chk(f'詳細ボタン（{st}）', card.locator('[data-act=open]'))
                chk(f'タグ番号（{st}）', card.locator('.tagbadge'))
            chk('アラーム帯の文字', pg.locator('#bannerMsg'))
            # 新規登録：入力欄・ラジオ・チップ
            pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(300)
            pg.fill('input[name=name]', '見本 太郎')
            chk('入力欄', pg.locator('input[name=name]'))
            chk('入力欄の見出し', pg.locator('#newForm label').filter(has_text='患者氏名'))
            chk('ラジオ', pg.locator('#kindRadios label').first)
            chk('ラジオ（選択中）', pg.locator('#kindRadios label:has(input:checked)'))
            chk('患者チップ', pg.locator('#pChips .chip').first)
            chk('ボタン（主）', pg.locator('#submitBtn'))
            chk('説明文', pg.locator('#sec-new p.hint').first)
            pg.fill('input[name=name]', '')
            # 表（日別一覧）
            pg.click('nav button[data-tab=history]'); pg.wait_for_timeout(300)
            chk('表の見出し', pg.locator('#hTable th').nth(1))
            chk('表の文字', pg.locator('#hTable tbody tr').first.locator('td').nth(1))
            chk('表の文字（偶数行）', pg.locator('#hTable tbody tr').nth(1).locator('td').nth(1))
            # 設定
            pg.click('nav button[data-tab=settings]'); pg.wait_for_timeout(200)
            chk('設定の見出し', pg.locator('#themePanel h2'))
            chk('選択中のボタン', pg.locator('#thmSeg .btn.on'))
            chk('選択していないボタン', pg.locator('#thmSeg .btn:not(.on)').first)
            chk('選択肢', pg.locator('#thmFrom'))

            # 印刷：配色に関係なく白地・黒文字・ガラスなし
            pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(200)
            pg.emulate_media(media='print')
            pr = pg.evaluate("""(()=>{const g=(e,ps)=>getComputedStyle(e,ps);const c=document.querySelector('#activeList .card');
              return [g(document.body).backgroundColor,g(document.body).color,g(c).backgroundColor,g(c).color,g(c).backdropFilter,
                g(document.querySelector('nav')).display,g(document.body,'::before').display]})()""")
            assert pr == ['rgb(255, 255, 255)', 'rgb(0, 0, 0)', 'rgb(255, 255, 255)', 'rgb(0, 0, 0)', 'none', 'none', 'none'], (th, pr)
            pg.screenshot(path=f'{OUT}/v200_print_{th}.png', full_page=True)
            pg.emulate_media(media='screen')
        for r in results:
            print('contrast', *r)
        assert len(results) >= 60
        ctx.close(); b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
