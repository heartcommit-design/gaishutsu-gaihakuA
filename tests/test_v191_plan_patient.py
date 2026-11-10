"""v1.9.1 G03：予定の登録・修正では患者台帳の「前回の外出」（lastOutAt・count・前回の行き先）を変えず、
出発（GO）したときに更新する。GOの取消ではGO前の値に戻す。通常の登録は従来どおり。assert で確かめる。
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html#detail'
SET = "([s,v])=>{const i=document.querySelector(s);i.value=v;i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}))}"
PT = "pid=>{const p=patients.find(x=>x.pid===pid);return p&&{lastOutAt:p.lastOutAt||0,count:p.count||0,lastDest:p.lastDest||'',dests:p.dests||[],ward:p.ward,famTel:p.famTel||''}}"


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1024, 'height': 1366}, has_touch=True)
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(800); pg.click('#startOv'); pg.wait_for_timeout(300)
        pt = lambda pid: pg.evaluate(PT, pid)

        def fill_new(name, pid, dest, hours=None, fam=''):
            pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(200)
            pg.fill('#pSearch', pid); pg.wait_for_timeout(200)
            chip = pg.locator('#pChips [data-pt]')
            if chip.count():
                chip.first.click(); pg.wait_for_timeout(200)
            else:
                pg.fill('input[name=name]', name); pg.fill('input[name=pid]', pid)
            pg.click('#wardRadios label:has-text("東1")')
            if hours is not None:
                pg.evaluate(SET, ['input[name=departAt]', pg.evaluate(f"toLocalInput(round15(Date.now()+{hours}*3600000))")])
            pg.click('#dueQuick button[data-h="4"]')
            pg.fill('input[name=dest]', dest)
            if fam: pg.fill('input[name=famTel]', fam)
            pg.fill('input[name=departNurse]', '(デモ) 看護師A')

        # ---- 1. 通常の登録（その場で出発）では従来どおり lastOutAt・count・前回の行き先が更新される
        fill_new('テスト 太郎', 'P0001', '見本の公園')
        pg.click('#submitBtn'); pg.wait_for_timeout(900)
        o = pg.evaluate("outings.find(o=>o.pid==='P0001')")
        assert o['status'] == 'out', o['status']
        a = pt('P0001')
        assert a['count'] == 1 and a['lastOutAt'] == o['departAt'] and a['lastDest'] == '見本の公園', a
        # 帰院させておく
        pg.locator('.card', has_text='テスト 太郎').locator('[data-act=return]').click()
        pg.fill('#dlgForm input[name=nurse]', '(デモ) 看護師B'); pg.click('#dlgActions button.ok'); pg.wait_for_timeout(900)
        assert pg.evaluate("outings.find(o=>o.pid==='P0001').status") == 'returned'
        before = pt('P0001')

        # ---- 2. 予定を登録しても lastOutAt・count・前回の行き先は変わらない。基本情報（家族の連絡先）は台帳に入る（1.11.0 で部屋はなくした）
        fill_new('テスト 太郎', 'P0001', '見本の駅', hours=3, fam='090-0000-0001')
        assert pg.inner_text('#submitBtn') == '予定として登録'
        pg.click('#submitBtn'); pg.wait_for_timeout(900)
        plan = pg.evaluate("outings.find(o=>o.pid==='P0001'&&o.status==='planned')")
        assert plan, '予定が登録されていない'
        a = pt('P0001')
        assert (a['lastOutAt'], a['count'], a['lastDest']) == (before['lastOutAt'], before['count'], before['lastDest']), (before, a)
        assert a['lastOutAt'] < pg.evaluate('Date.now()'), '前回外出日時が未来になっている'
        assert a['famTel'] == '090-0000-0001', a
        # 呼び出し欄に未来の日時（予定の出発日時）が出ない
        pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(200)
        pg.fill('#pSearch', 'P0001'); pg.wait_for_timeout(300)
        chip = pg.inner_text('#pChips [data-pt]')
        assert '前回 ' + pg.evaluate('fmt', before['lastOutAt']) in chip, chip
        assert pg.evaluate('fmt', plan['departAt']) not in chip, chip
        pg.fill('#pSearch', '')

        # ---- 3. 予定を修正しても count は増えない
        pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(300)
        pg.locator('#planList .card', has_text='テスト 太郎').locator('[data-pact=planedit]').click(); pg.wait_for_timeout(600)
        pg.evaluate(SET, ['input[name=departAt]', pg.evaluate("toLocalInput(round15(Date.now()+4*3600000))")])
        pg.fill('input[name=dest]', '見本の図書館')
        pg.fill('input[name=departNurse]', '(デモ) 看護師A')
        assert pg.inner_text('#submitBtn') == '予定を更新'
        pg.click('#submitBtn'); pg.wait_for_timeout(900)
        plans = pg.evaluate("outings.filter(o=>o.pid==='P0001'&&o.status==='planned')")
        assert len(plans) == 1 and plans[0]['dest'] == '見本の図書館', plans
        a = pt('P0001')
        assert (a['lastOutAt'], a['count'], a['lastDest']) == (before['lastOutAt'], before['count'], before['lastDest']), (before, a)

        # ---- 4. GO すると lastOutAt が出発時刻になり count が1増え、前回の行き先が更新される
        pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(300)
        pg.locator('#planList .card', has_text='テスト 太郎').locator('[data-pact=go]').click(); pg.wait_for_timeout(300)
        pg.select_option('#goTag', '')
        pg.fill('#dlgForm input[name=nurse]', '(デモ) 看護師C'); pg.click('#dlgActions button.ok'); pg.wait_for_timeout(900)
        o = pg.evaluate("outings.find(o=>o.pid==='P0001'&&o.status==='out')")
        assert o and o['departAtPlanned'], o
        a = pt('P0001')
        assert a['lastOutAt'] == o['departAt'], (a, o['departAt'])
        assert a['count'] == before['count'] + 1, (before, a)
        assert a['lastDest'] == '見本の図書館' and a['dests'][0] == '見本の図書館', a

        # ---- 5. GOの取消（予定に戻す）で lastOutAt・count・前回の行き先がGO前に戻る
        card = pg.locator('.card', has_text='テスト 太郎')
        card.locator('[data-act=undo]').click(); pg.wait_for_timeout(300)
        pg.fill('#dlgForm input[name=reason]', 'GOを押し間違えた'); pg.fill('#dlgForm input[name=staff]', '(デモ) 看護師C')
        pg.click('#dlgActions button.pri'); pg.wait_for_timeout(900)
        assert pg.evaluate("outings.find(o=>o.pid==='P0001'&&o.status==='planned')"), '予定に戻っていない'
        a = pt('P0001')
        assert (a['lastOutAt'], a['count'], a['lastDest'], a['dests']) == (before['lastOutAt'], before['count'], before['lastDest'], before['dests']), (before, a)

        # 再読み込みしても戻った値のまま（台帳に保存されている）
        pg.reload(); pg.wait_for_timeout(800); pg.click('#startOv'); pg.wait_for_timeout(600)
        a = pt('P0001')
        assert (a['lastOutAt'], a['count']) == (before['lastOutAt'], before['count']), (before, a)

        # ---- 6. 「内容を確認・変更して出発」（予定から入力欄で出発）でも1回だけ数え、取消で戻る
        pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(300)
        pg.locator('#planList .card', has_text='テスト 太郎').locator('[data-pact=edit]').click(); pg.wait_for_timeout(600)
        pg.fill('input[name=departNurse]', '(デモ) 看護師A')
        assert pg.inner_text('#submitBtn') == 'この内容で出発を登録'
        pg.click('#submitBtn'); pg.wait_for_timeout(900)
        o = pg.evaluate("outings.find(o=>o.pid==='P0001'&&o.status==='out')")
        a = pt('P0001')
        assert a['count'] == before['count'] + 1 and a['lastOutAt'] == o['departAt'], (before, a)
        pg.locator('.card', has_text='テスト 太郎').locator('[data-act=undo]').click(); pg.wait_for_timeout(300)
        pg.fill('#dlgForm input[name=reason]', '出発が延期になった'); pg.fill('#dlgForm input[name=staff]', '(デモ) 看護師C')
        pg.click('#dlgActions button.pri'); pg.wait_for_timeout(900)
        a = pt('P0001')
        assert (a['lastOutAt'], a['count'], a['lastDest']) == (before['lastOutAt'], before['count'], before['lastDest']), (before, a)

        # ---- 7. 1.9.0 までに登録した予定（台帳がすでに予定の日時・回数+1 になっている）は、GO で二重に数えない
        pg.evaluate("""async()=>{const p=patients.find(x=>x.pid==='P0001');const o=outings.find(x=>x.pid==='P0001'&&x.status==='planned');
            p.lastOutAt=o.departAt;p.count=(p.count||0)+1;await dbPut('patients',p);}""")
        old = pt('P0001')
        pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(300)
        pg.locator('#planList .card', has_text='テスト 太郎').locator('[data-pact=go]').click(); pg.wait_for_timeout(300)
        pg.select_option('#goTag', '')
        pg.fill('#dlgForm input[name=nurse]', '(デモ) 看護師C'); pg.click('#dlgActions button.ok'); pg.wait_for_timeout(900)
        o = pg.evaluate("outings.find(o=>o.pid==='P0001'&&o.status==='out')")
        a = pt('P0001')
        assert a['count'] == old['count'] and a['lastOutAt'] == o['departAt'], (old, a)

        # ---- 8. デモデータの予定の患者も、前回外出日時が未来にならない
        pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(1500)
        fut = pg.evaluate("patients.filter(p=>(p.lastOutAt||0)>Date.now()).map(p=>p.name)")
        assert fut == [], fut
        b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
