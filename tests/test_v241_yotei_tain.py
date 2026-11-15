"""2.4.1：assert で確かめる。
(a) 予定の「詳細」も、外出・外泊中と同じく開いてから2分（OPEN_MS）で自動で閉じる。
    2分未満は開いたまま（毎秒の更新で作り直さない）・2分を過ぎると閉じる・ダイアログが開いている間は閉じない（閉じた後に閉じる）・
    index.html#detail（テスト用の全部開く表示）では閉じない。
(b) すでに使っている端末の「よく使う行き先」に「他院受診」を一度だけ末尾に足す（すでにあれば重ねない・消したら復活しない）。
(c) 版の2か所（index.html の APP_VERSION と sw.js の CACHE）が 2.4.1 でそろっている。
時計は 2026/11/13(金) 10:00（日本時間）から（pg.clock.install。時刻は普通に進み、fast_forward で先へ進める）。
"""
import os, re
from playwright.sync_api import sync_playwright
from v200_util import jst

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'
N = [0]
errs = []


def ok(cond, msg=''):
    N[0] += 1
    assert cond, msg


def open_page(b, url=URL, w=1180, h=820):
    ctx = b.new_context(viewport={'width': w, 'height': h}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.clock.install(time=jst(2026, 11, 13, 10, 0))
    pg.goto(url); pg.wait_for_timeout(600); pg.click('#startOv'); pg.wait_for_timeout(200)
    pg.evaluate("window.tone=function(){}")
    return ctx, pg


def demo_in(pg):
    pg.click('nav button[data-tab=settings]'); pg.click('#demoIn')
    pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを入れました')", timeout=30000)
    pg.wait_for_timeout(200)


def plan_tab(pg):
    pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(300)


def n_open(pg):
    return pg.locator('#planList .prbody').count()


def ff(pg, ms_):
    pg.clock.fast_forward(ms_); pg.wait_for_timeout(1300)   # 進めた後、毎秒の tick が動くのを待つ


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        # ================= (c) 版 =================
        html = open(os.path.join(APP, 'index.html'), encoding='utf-8').read()
        sw = open(os.path.join(APP, 'sw.js'), encoding='utf-8').read()
        ok(re.search(r"APP_VERSION='2\.4\.1'", html), 'APP_VERSION')
        ok("CACHE = 'gaishutsu-shisaku-v2.4.1'" in sw, 'sw.js CACHE')

        # ================= (a) 予定の詳細の自動で閉じる =================
        ctx, pg = open_page(b)
        ok(pg.evaluate('OPEN_MS') == 120000)
        demo_in(pg); plan_tab(pg)
        ok(n_open(pg) == 0, 'はじめは全部たたんである')
        tg = pg.locator('#planList [data-pact=toggle]').first
        tg.click(); pg.wait_for_timeout(300)
        ok(n_open(pg) == 1 and tg.get_attribute('aria-expanded') == 'true', '詳細が開かない')
        # 開いている間、毎秒の更新で作り直さない（ちらつかない）・スクロール位置も変わらない
        pg.evaluate("document.querySelector('#planList .prbody').__mark=1")
        y0 = pg.evaluate('scrollY')
        ff(pg, 100_000)
        ok(n_open(pg) == 1, '2分未満で閉じた')
        ok(pg.evaluate("!!document.querySelector('#planList .prbody').__mark"), '2分未満の間に作り直された')
        ok(pg.evaluate('scrollY') == y0, 'スクロール位置が変わった')
        pg.screenshot(path=os.path.join(OUT, 'v241_open_100s.png'))
        ff(pg, 21_000)   # 開いてから 121 秒
        ok(n_open(pg) == 0, '2分を過ぎても閉じない')
        ok(pg.locator('#planList [data-pact=toggle]').first.get_attribute('aria-expanded') == 'false')
        ok(pg.evaluate('planOpen.size') == 0, '期限の過ぎた印が残っている')
        # 閉じてから開き直すと、また2分
        pg.locator('#planList [data-pact=toggle]').first.click(); pg.wait_for_timeout(300)
        ok(n_open(pg) == 1)
        ff(pg, 60_000); ok(n_open(pg) == 1)
        # 「閉じる」で閉じる（手で閉じる動きは今まで通り）
        pg.locator('#planList [data-pact=toggle]').first.click(); pg.wait_for_timeout(300)
        ok(n_open(pg) == 0, '「閉じる」で閉じない')

        # ダイアログ（写真・GO・取り消しの確認）が開いている間は閉じない
        pg.locator('#planList [data-pact=toggle]').first.click(); pg.wait_for_timeout(300)
        ok(n_open(pg) == 1)
        pg.locator('#planList .card.open [data-pact=go]').click(); pg.wait_for_timeout(400)
        ok(pg.evaluate("!!document.querySelector('dialog[open]')"), 'GO のダイアログが開かない')
        ff(pg, 180_000)   # 開いてから3分以上
        ok(n_open(pg) == 1, 'ダイアログの間に閉じた')
        ok(pg.evaluate("!!document.querySelector('dialog[open]')"), 'ダイアログが閉じた')
        pg.evaluate("document.querySelector('dialog[open]').close()"); pg.wait_for_timeout(1500)
        ok(n_open(pg) == 0, 'ダイアログを閉じた後も閉じない')
        # 取り消しの確認（#cdlg）でも同じ
        pg.locator('#planList [data-pact=toggle]').first.click(); pg.wait_for_timeout(300)
        pg.locator('#planList .card.open [data-pact=cancel]').click(); pg.wait_for_timeout(400)
        ok(pg.evaluate("!!document.querySelector('#cdlg[open]')"), '確認のダイアログが開かない')
        ff(pg, 150_000)
        ok(n_open(pg) == 1, '確認のダイアログの間に閉じた')
        pg.click('#cdlgNo'); pg.wait_for_timeout(1500)
        ok(n_open(pg) == 0, '確認のダイアログを閉じた後も閉じない')
        ok(pg.locator('#planList .card.prow').count() == 19, '予定が消えた')

        # 外出・外泊中の「詳細」も同じ2分（共通の OPEN_MS）
        pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(300)
        before = pg.locator('#activeList [data-act=close]').count()
        opn = pg.locator('#activeList [data-act=open]')
        if opn.count():
            opn.first.click(); pg.wait_for_timeout(300)
            ok(pg.locator('#activeList [data-act=close]').count() == before + 1)
            ff(pg, 110_000); ok(pg.locator('#activeList [data-act=close]').count() == before + 1)
            ff(pg, 12_000); ok(pg.locator('#activeList [data-act=close]').count() == before)
        else:
            print('外出・外泊中の「詳細」ボタンが見つからない（時間軸表示のため）：省略')
        ctx.close()

        # 予定タブを離れている間に期限が過ぎた時：戻った時にはたたんである（いったん開いてから閉じる、にならない）
        ctx, pg = open_page(b, w=1024, h=1366)
        demo_in(pg); plan_tab(pg)
        pg.locator('#planList [data-pact=toggle]').first.click(); pg.wait_for_timeout(300)
        ok(n_open(pg) == 1)
        pg.click('nav button[data-tab=active]'); ff(pg, 130_000)
        pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(50)
        ok(n_open(pg) == 0, '戻った時に開いたまま')
        ctx.close()

        # #detail（テスト用の全部開く表示）では閉じない
        ctx, pg = open_page(b, URL + '#detail')
        demo_in(pg); plan_tab(pg)
        ok(n_open(pg) == 19, ('#detail で全部開いていない', n_open(pg)))
        ff(pg, 300_000)
        ok(n_open(pg) == 19, '#detail で閉じた')
        ctx.close()

        # ================= (b) 「他院受診」を一度だけ足す =================
        ctx, pg = open_page(b, w=1024, h=1366)
        dp = pg.evaluate('settings.destPresets')
        ok(dp.count('他院受診') == 1 and dp[-1] == '他院受診', ('新しい端末', dp))
        ok(pg.evaluate("dbGet('settings','main').then(s=>s.destAdded241)") is True)

        def put_old(lst):
            pg.evaluate("""async(l)=>{const s=await dbGet('settings','main')||{};s.destPresets=l;s.destAdded1110=true;delete s.destAdded241;await dbPut('settings',s,'main');}""", lst)
            pg.reload(); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(200)
            return pg.evaluate('settings.destPresets')

        # 2.4.0 までの端末（印なし・「他院受診」なし・利用者が並べ替え／足し／消し済み）：末尾に足す。他の項目と順番はそのまま
        old = ['実家', '自宅', '見本の公園', '図書館', '喫煙']
        dp = put_old(old)
        ok(dp == old + ['他院受診'], ('移行', dp))
        ok(pg.evaluate("dbGet('settings','main').then(s=>[s.destPresets,s.destAdded241])") == [old + ['他院受診'], True])
        pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(200)
        ok('他院受診' in pg.inner_text('.pchips[data-preset=dest]'), '行き先の候補に出ない')
        # すでにある端末：重ねない・位置も変えない
        dp = put_old(['他院受診', '自宅', '実家'])
        ok(dp == ['他院受診', '自宅', '実家'], ('重なった', dp))
        # 移行の後に利用者が消したら、開き直しても復活しない
        dp = put_old(['自宅', '実家'])
        ok(dp == ['自宅', '実家', '他院受診'])
        pg.click('nav button[data-tab=settings]'); pg.fill('#sDest', '自宅\n実家'); pg.click('#sPresetSave'); pg.wait_for_timeout(300)
        for _ in range(2):
            pg.reload(); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(200)
            ok(pg.evaluate('settings.destPresets') == ['自宅', '実家'], '消した「他院受診」が復活した')
        ctx.close()
        b.close()
    print('assert', N[0])
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
