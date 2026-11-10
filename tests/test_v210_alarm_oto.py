"""2.1.0：ヘッダーの「アラーム音」ボタンで音の有効／無効を切り替える・音量0の表示・「このアプリについて」の2項目。
- 有効→確認ダイアログ→「無効にする」で無効／「やめる」では変わらない／「試しに鳴らす」で1回鳴る
- 無効中：ヘッダーのボタン（赤・点滅）・全タブで見える赤い帯・開始画面の注意。再読み込み後も保たれる
- 「有効に戻す」・ヘッダーのボタンで確認なしにすぐ戻る（知らせと試し鳴らし）
- 無効中に予定超過：音（tone）は1回も鳴らないが、アラーム帯（音は無効の表示つき）・点滅・脈動・タイトルの切り替えは出る
- 有効なら同じ状況で音が鳴る
- 音量0：ボタン「音量0（鳴りません）」・説明ダイアログ・設定の注意。0.5に戻すと「有効」
- 優先順位（無効 ＞ 音量0）、バックアップの書き出し・復元に無効の設定が乗る
- 「このアプリについて」の2項目（一字一句）
- 両配色で新しい帯・ボタンの文字のコントラスト比 4.5 以上、3つの幅で横にはみ出さない
音の確かめ方：アプリの音はすべて tone()（WebAudio の発振器）を通るので、tone を数える包みに差し替えて呼ばれた回数を見る。
"""
import os, json
from playwright.sync_api import sync_playwright
from v200_util import jst, contrast

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'

T_ON = '🔔 アラーム音：有効'
T_MUTE = '🔇 アラーム音：無効'
T_VOL0 = '🔇 アラーム音：音量0（鳴りません）'
BAR = 'アラーム音を無効にしています。帰院予定を過ぎても音が鳴りません。'
ABOUT = [
    ('ご意見・不具合', 'いただいたご意見は、反映すべきかどうか判断してからの採用になります。また、不具合があれば随時知らせてください。'),
    ('このアプリの外部への発信について', '作者（黒田優）の許可なく、学会や研究会での発表、宣伝、問い合わせへの対応など外部への発信は控えてください。許可なくこのような行為をしたことが判明した場合、取り下げ、アプリの使用中止なども検討いたします。'),
]
SPY = """()=>{if(window.__spy)return;window.__spy=1;window.__tones=0;window.__calls={alarm:0,alarmUrgent:0,chime:0};
  const t0=window.tone;window.tone=function(){window.__tones++;return t0.apply(this,arguments);};
  for(const k of ['alarm','alarmUrgent','chime']){const f=window[k];window[k]=function(){window.__calls[k]++;return f.apply(this,arguments);};}}"""


def btn(pg):
    return pg.inner_text('#soundBtn').strip()


def tones(pg):
    return pg.evaluate('window.__tones')


def hide_toast(pg):
    pg.evaluate("document.getElementById('toast').style.display='none'")


def dlg_buttons(pg):
    return [x.strip() for x in pg.locator('#dlgActions button').all_inner_texts()]


def mute_visible_in_view(pg):
    """赤い帯が、画面をいちばん下まで動かしても見えている（上に固定されている）"""
    pg.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)'); pg.wait_for_timeout(80)
    r = pg.evaluate("(()=>{const e=document.getElementById('muteBar');const b=e.getBoundingClientRect();return [getComputedStyle(e).display,b.top,b.bottom,innerHeight]})()")
    pg.evaluate('window.scrollTo(0,0)')
    return r[0] != 'none' and r[1] >= 0 and r[2] <= r[3] and r[2] > r[1]


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
        ctx = b.new_context(viewport={'width': 1180, 'height': 820}, timezone_id='Asia/Tokyo', device_scale_factor=1, accept_downloads=True)
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        dec = ctx.new_page()
        pg.clock.set_fixed_time(jst(2026, 11, 13, 10, 0))
        pg.goto(URL); pg.wait_for_timeout(700)
        assert not pg.locator('#startMute').is_visible(), '有効なのに開始画面に注意が出ている'
        pg.click('#startOv'); pg.wait_for_timeout(400)
        pg.evaluate(SPY)
        assert pg.evaluate('soundReady()'), '音が出せる状態にならない（テスト環境）'
        assert pg.evaluate('settings.soundOff') in (None, False) and pg.evaluate('soundState()') == 'on'
        assert btn(pg) == T_ON, btn(pg)
        assert not pg.locator('#muteBar').is_visible()

        # ---- 有効のとき押す → 確認ダイアログ（アプリ内）。「試しに鳴らす」は閉じずに1回鳴らす。「やめる」で変わらない
        pg.on('dialog', lambda d: errs.append('window の dialog が出た：' + d.message))
        pg.click('#soundBtn'); pg.wait_for_timeout(200)
        assert pg.evaluate("document.getElementById('dlg').open")
        assert pg.inner_text('#dlgTitle') == 'アラーム音を無効に切り替えますか？', pg.inner_text('#dlgTitle')
        assert pg.inner_text('#dlgBody').strip() == '無効の間は、帰院予定を過ぎても音が鳴りません。画面の赤い表示と点滅は続きます。'
        assert dlg_buttons(pg) == ['試しに鳴らす', 'やめる', '無効にする'], dlg_buttons(pg)
        assert 'bad' in pg.get_attribute('#dlgActions button:has-text("無効にする")', 'class')
        assert pg.evaluate("getComputedStyle(document.querySelector('#dlgActions .bad')).backgroundColor") == 'rgb(198, 40, 40)'
        pg.screenshot(path=OUT + '/v210_confirm.png')
        n0 = tones(pg)
        pg.click('#dlgActions button:has-text("試しに鳴らす")'); pg.wait_for_timeout(400)
        assert tones(pg) > n0, '「試しに鳴らす」で鳴らない'
        assert pg.evaluate("document.getElementById('dlg').open"), '「試しに鳴らす」でダイアログが閉じた'
        pg.click('#dlgActions button:has-text("やめる")'); pg.wait_for_timeout(200)
        assert not pg.evaluate("document.getElementById('dlg').open")
        assert pg.evaluate('!!settings.soundOff') is False and btn(pg) == T_ON and not pg.locator('#muteBar').is_visible()

        # ---- 無効にする
        pg.click('#soundBtn'); pg.wait_for_timeout(200)
        pg.click('#dlgActions button:has-text("無効にする")'); pg.wait_for_timeout(300)
        assert pg.evaluate('settings.soundOff') is True
        assert pg.evaluate("dbGet('settings','main').then(s=>s.soundOff)") is True, '設定（IndexedDB）に保存されていない'
        assert btn(pg) == T_MUTE, btn(pg)
        st = pg.evaluate("(()=>{const b=document.getElementById('soundBtn');const c=getComputedStyle(b);return [b.className,c.backgroundColor,c.color,c.animationName]})()")
        assert st == ['mute', 'rgb(198, 40, 40)', 'rgb(255, 255, 255)', 'blink'], st
        assert pg.locator('#muteBar').is_visible()
        assert pg.inner_text('#muteBar .msg').replace('🔇', '').strip() == BAR, pg.inner_text('#muteBar .msg')
        assert pg.inner_text('#muteOn').strip() == '有効に戻す'
        assert pg.locator('#muteBar button').count() == 1, '帯に閉じるボタンがある'
        # 全タブで見える（上に固定）
        for tab in pg.locator('nav button[data-tab]').evaluate_all('l=>l.map(b=>b.dataset.tab)'):
            pg.click(f'nav button[data-tab={tab}]'); pg.wait_for_timeout(150)
            assert mute_visible_in_view(pg), f'{tab} タブで赤い帯が見えない'
        pg.click('nav button[data-tab=active]')

        # ---- 再読み込みしても無効のまま・開始画面に注意・帯が出続ける
        pg.reload(); pg.wait_for_timeout(800)
        assert pg.locator('#startMute').is_visible(), '開始画面に注意が出ない'
        assert BAR in pg.inner_text('#startMute').replace('\n', ''), pg.inner_text('#startMute')
        pg.screenshot(path=OUT + '/v210_start_mute.png')
        pg.click('#startOv'); pg.wait_for_timeout(400)
        pg.evaluate(SPY)
        assert pg.evaluate('settings.soundOff') is True and btn(pg) == T_MUTE and pg.locator('#muteBar').is_visible()

        # ---- 無効中：アプリの音はすべて止まる（直接呼んでも鳴らない）
        assert pg.evaluate('[alarm(),alarmUrgent(),chime()]') == [False, False, False]
        assert tones(pg) == 0
        # 設定の「アラーム音を試す」も鳴らず、無効だと知らせる
        pg.click('nav button[data-tab=settings]'); pg.click('#sTest'); pg.wait_for_timeout(400)
        assert tones(pg) == 0 and 'アラーム音を無効にしています' in pg.inner_text('#toast')
        hide_toast(pg)

        # ---- 無効中に予定超過（デモデータ：架空）：音を鳴らす処理（tone）は呼ばれず、画面の知らせは出る
        pg.click('#demoIn'); pg.wait_for_timeout(1500)
        if pg.locator('#gapBar').is_visible():
            pg.click('#gapOk')
        pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(2600)
        assert pg.locator('#banner.on').count() == 1, 'アラーム帯が出ない'
        assert pg.evaluate("getComputedStyle(document.getElementById('banner')).animationName") in ('flash', 'flash2')
        assert '（音は無効）' in pg.inner_text('#bannerMsg'), pg.inner_text('#bannerMsg')
        assert pg.locator('.card.st-overdue').count() >= 1
        assert pg.evaluate("getComputedStyle(document.querySelector('.card.st-overdue')).animationName") == 'pulse'
        titles = set()
        for _ in range(3):
            titles.add(pg.evaluate('document.title')); pg.wait_for_timeout(1000)
        assert '⚠ 帰院確認が必要です' in titles and '外出・外泊管理' in titles, titles
        assert pg.evaluate('window.__calls.alarm+window.__calls.alarmUrgent') >= 1, '鳴らす判断（見回り）が動いていない'
        assert tones(pg) == 0, f'無効なのに音が鳴った（tone {tones(pg)}回）'
        assert pg.locator('#muteBar').is_visible()
        pg.screenshot(path=OUT + '/v210_mute_overdue.png')

        # ---- 「有効に戻す」：確認なしですぐ戻り、知らせて1回試し鳴らし
        pg.click('#muteOn'); pg.wait_for_timeout(500)
        assert not pg.evaluate("document.getElementById('dlg').open"), '有効に戻すときに確認が出た'
        assert pg.evaluate('settings.soundOff') is False and pg.evaluate("dbGet('settings','main').then(s=>s.soundOff)") is False
        assert 'アラーム音を有効にしました' in pg.inner_text('#toast')
        assert tones(pg) > 0, '有効に戻したときに試し鳴らしがない'
        assert btn(pg) == T_ON and not pg.locator('#muteBar').is_visible()
        assert '（音は無効）' not in pg.inner_text('#bannerMsg')
        # 有効なら予定超過で鳴る（見回りが次に鳴らす時刻まで進める）
        n1 = tones(pg)
        pg.clock.set_fixed_time(jst(2026, 11, 13, 10, 0, 20)); pg.wait_for_timeout(1500)
        assert tones(pg) > n1, '有効なのに予定超過で鳴らない'
        hide_toast(pg)

        # ---- ヘッダーのボタンでも、無効中なら確認なしで戻る
        pg.click('#soundBtn'); pg.click('#dlgActions button:has-text("無効にする")'); pg.wait_for_timeout(300)
        assert btn(pg) == T_MUTE
        n2 = tones(pg)
        pg.click('#soundBtn'); pg.wait_for_timeout(500)
        assert not pg.evaluate("document.getElementById('dlg').open")
        assert btn(pg) == T_ON and pg.evaluate('settings.soundOff') is False and tones(pg) > n2
        assert 'アラーム音を有効にしました' in pg.inner_text('#toast')
        hide_toast(pg)

        # ---- 音量0
        pg.click('nav button[data-tab=settings]'); pg.wait_for_timeout(200)
        assert not pg.locator('#sVolWarn').is_visible()
        pg.fill('#sVol', '0'); pg.wait_for_timeout(100)
        assert pg.locator('#sVolWarn').is_visible() and '音量が0のため、アラーム音は鳴りません' in pg.inner_text('#sVolWarn')
        assert btn(pg) == T_ON, '保存前に表示が変わった'
        pg.click('#sSave'); pg.wait_for_timeout(200)
        assert pg.evaluate('settings.volume') == 0 and btn(pg) == T_VOL0, btn(pg)
        st = pg.evaluate("(()=>{const b=document.getElementById('soundBtn');const c=getComputedStyle(b);return [b.className,c.backgroundColor,c.color,c.animationName]})()")
        assert st == ['vol0', 'rgb(198, 40, 40)', 'rgb(255, 255, 255)', 'blink'], st
        assert not pg.locator('#muteBar').is_visible(), '音量0で「無効」の帯が出た（取り違え）'
        assert pg.locator('#banner.on').count() == 1, '音量0で画面の知らせが消えた'
        # 再読み込みしても音量0の注意
        pg.reload(); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(400)
        assert btn(pg) == T_VOL0
        pg.click('nav button[data-tab=settings]'); pg.wait_for_timeout(200)
        assert pg.locator('#sVolWarn').is_visible()
        pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(200)
        pg.click('#soundBtn'); pg.wait_for_timeout(200)
        assert pg.evaluate("document.getElementById('dlg').open")
        assert '設定のアラーム音量が0のため鳴りません' in pg.inner_text('#dlgBody')
        assert sorted(dlg_buttons(pg)) == sorted(['設定を開く', '閉じる']), dlg_buttons(pg)
        pg.screenshot(path=OUT + '/v210_vol0_dlg.png')
        pg.click('#dlgActions button:has-text("設定を開く")'); pg.wait_for_timeout(300)
        assert not pg.evaluate("document.getElementById('dlg').open")
        assert pg.locator('#sec-settings').is_visible() and pg.locator('#sVol').is_visible()
        # 優先順位：無効 ＞ 音量0
        pg.evaluate("setSoundOff(true)"); pg.wait_for_timeout(200)
        assert btn(pg) == T_MUTE and pg.locator('#muteBar').is_visible()
        pg.click('#muteOn'); pg.wait_for_timeout(300)
        assert btn(pg) == T_VOL0
        # 優先順位：音が出ません ＞ 無効
        pg.evaluate("setSoundOff(true)"); pg.wait_for_timeout(100)
        pg.evaluate("actx.suspend().then(updateSoundBtn)"); pg.wait_for_timeout(300)
        assert btn(pg) == '🔇 音が出ません：ここを押す' and pg.get_attribute('#soundBtn', 'class') == 'off', btn(pg)
        assert pg.locator('#muteBar').is_visible(), '音が出ない状態でも、無効の帯は出し続ける'
        pg.evaluate("actx.resume().then(updateSoundBtn)"); pg.wait_for_timeout(300)
        assert btn(pg) == T_MUTE
        pg.click('#muteOn'); pg.wait_for_timeout(300)
        # 0.5 に戻すと「有効」
        pg.fill('#sVol', '0.5'); pg.wait_for_timeout(100)
        assert not pg.locator('#sVolWarn').is_visible()
        pg.click('#sSave'); pg.wait_for_timeout(200)
        assert pg.evaluate('settings.volume') == 0.5 and btn(pg) == T_ON, btn(pg)
        hide_toast(pg)

        # ---- バックアップの書き出し・復元に無効の設定が乗る
        pg.evaluate("setSoundOff(true)"); pg.wait_for_timeout(200)
        with pg.expect_download() as dl:
            pg.click('#bkOut')
        path = dl.value.path()
        data = json.load(open(path, encoding='utf-8'))
        assert data['settings'].get('soundOff') is True, 'バックアップに無効の設定が入っていない'
        pg.click('#muteOn'); pg.wait_for_timeout(300)
        assert pg.evaluate('settings.soundOff') is False
        pg.set_input_files('#bkIn', path); pg.wait_for_timeout(400)
        pg.click('#cdlgYes'); pg.wait_for_timeout(1200)
        assert pg.evaluate('settings.soundOff') is True and btn(pg) == T_MUTE and pg.locator('#muteBar').is_visible(), '復元で無効が戻らない'
        hide_toast(pg)

        # ---- 「このアプリについて」の2項目（一字一句）
        pairs = pg.evaluate("[...document.querySelectorAll('#aboutPanel dt')].map(d=>[d.textContent,d.nextElementSibling.textContent])")
        for h, body in ABOUT:
            assert [h, body] in pairs, (h, pairs)
        assert [d for d, _ in pairs].count('ご意見・不具合') == 1, '「ご意見・不具合」が重なっている'

        # ---- 両配色：新しい帯・ボタンの文字のコントラスト比（画面上の実際の色）
        results = []
        for th in ['light', 'dark']:
            pg.click('nav button[data-tab=settings]'); pg.click(f'#thmSeg [data-thm={th}]'); pg.wait_for_timeout(200)
            hide_toast(pg)

            def chk(name, loc):
                assert loc.count() >= 1 and loc.first.is_visible(), name
                r = contrast(pg, loc.first, dec)
                results.append((th, name, round(r, 2)))
                assert r >= 4.5, f'{th}: {name} のコントラスト比 {r:.2f} < 4.5'
            # 帯は不透明の赤
            bg = pg.evaluate("getComputedStyle(document.getElementById('muteBar')).backgroundColor")
            assert bg == 'rgb(183, 28, 28)', bg
            chk('赤い帯の文', pg.locator('#muteBar .msg'))
            chk('有効に戻す', pg.locator('#muteOn'))
            chk('ボタン（無効）', pg.locator('#soundBtn'))
            pg.fill('#sVol', '0'); pg.click('#sSave'); pg.wait_for_timeout(200); hide_toast(pg)
            chk('設定の注意（音量0）', pg.locator('#sVolWarn'))
            pg.click('#muteOn'); pg.wait_for_timeout(300); hide_toast(pg)
            assert btn(pg) == T_VOL0
            chk('ボタン（音量0）', pg.locator('#soundBtn'))
            pg.fill('#sVol', '0.7'); pg.click('#sSave'); pg.wait_for_timeout(200)
            pg.evaluate("setSoundOff(true)"); pg.wait_for_timeout(200); hide_toast(pg)
            # 開始画面の注意
            pg.reload(); pg.wait_for_timeout(800)
            chk('開始画面の注意', pg.locator('#startMute'))
            chk('開始画面の注意（戻し方）', pg.locator('#startMute .mnote'))
            pg.click('#startOv'); pg.wait_for_timeout(300)
            chk('有効に戻す（開き直し後）', pg.locator('#muteOn'))
            pg.click('#muteOn'); pg.wait_for_timeout(300); hide_toast(pg)
            pg.click('#soundBtn'); pg.wait_for_timeout(200)
            chk('確認ダイアログの見出し', pg.locator('#dlgTitle'))
            chk('確認ダイアログの説明', pg.locator('#dlgBody p'))
            chk('確認の「無効にする」', pg.locator('#dlgActions .bad'))
            pg.click('#dlgActions .bad'); pg.wait_for_timeout(300); hide_toast(pg)
            pg.click('nav button[data-tab=settings]')
        print('contrast', results)

        # ---- 3つの幅・両配色：横にはみ出さない（無効中・音量0）
        for th in ['light', 'dark']:
            pg.click('nav button[data-tab=settings]'); pg.click(f'#thmSeg [data-thm={th}]'); pg.wait_for_timeout(150)
            for w, h in [(1024, 1366), (1180, 820), (390, 844)]:
                pg.set_viewport_size({'width': w, 'height': h}); pg.wait_for_timeout(200)
                for tab in ['active', 'plan', 'settings']:
                    pg.click(f'nav button[data-tab={tab}]'); pg.wait_for_timeout(120)
                    sw = pg.evaluate('document.documentElement.scrollWidth')
                    assert sw <= w, f'{th} {w}px {tab}：横にはみ出し {sw}'
                    ov = pg.evaluate("(()=>{const e=document.getElementById('muteBar');return [e.scrollWidth,e.clientWidth]})()")
                    assert ov[0] <= ov[1], f'{th} {w}px：帯の中がはみ出し {ov}'
                    assert mute_visible_in_view(pg), f'{th} {w}px {tab}：帯が見えない'
                # 音量0の表示（ボタンが長い）でもはみ出さない
                pg.evaluate("settings.volume=0;settings.soundOff=false;updateSoundBtn()"); pg.wait_for_timeout(100)
                assert btn(pg) == T_VOL0
                assert pg.evaluate('document.documentElement.scrollWidth') <= w
                hb = pg.evaluate("(()=>{const b=document.getElementById('soundBtn').getBoundingClientRect();return b.right})()")
                assert hb <= w, f'{w}px：音量0のボタンがはみ出し'
                pg.evaluate("settings.volume=0.7;settings.soundOff=true;updateSoundBtn()"); pg.wait_for_timeout(100)
                # 「このアプリについて」
                pg.click('nav button[data-tab=settings]')
                ap = pg.evaluate("(()=>{const e=document.getElementById('aboutPanel');return [e.scrollWidth,e.clientWidth]})()")
                assert ap[0] <= ap[1], f'{w}px：このアプリについて がはみ出し'
                pg.locator('#aboutPanel').scroll_into_view_if_needed()
                pg.locator('#aboutPanel').screenshot(path=f'{OUT}/v210_about_{th}_{w}.png')
        pg.set_viewport_size({'width': 1180, 'height': 820})
        b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
