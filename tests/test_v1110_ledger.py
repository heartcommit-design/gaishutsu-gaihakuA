"""1.11.0（第1部）患者台帳まわり。assert で確かめる。
H1 退院・再入院／H2 患者情報の修正／H3 同意の撤回・取得日／H4 部屋をなくす／H5 服装の記入3件／
H6 変更せずに戻る／H7 GO で写真・服装を任意で／H8 行き先の3つ／H9 看護師名60人。
データはすべて架空（テスト 太郎 など）。
"""
import os, struct, zlib
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html#detail'
SET = "([s,v])=>{const i=document.querySelector(s);i.value=v;i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}))}"
NURSE = '(デモ) 看護師A'


def png(path, w=60, h=80):
    raw = b''.join(b'\x00' + b'\x30\x50\x90' * w for _ in range(h))
    ch = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))


PHOTO = os.path.join(OUT, 'v1110_p.png'); png(PHOTO)
errs = []


def open_app(ctx):
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(300)
    return pg


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1024, 'height': 1366}, has_touch=True, accept_downloads=True)
        pg = open_app(ctx)
        P = lambda pid: pg.evaluate("pid=>patients.find(x=>x.pid===pid)", pid)
        tab = lambda t: (pg.click(f'nav button[data-tab={t}]'), pg.wait_for_timeout(250))
        def staff_ok(sel='#dlgActions button.pri'):
            pg.fill('#dlgBody input[name=staff]', NURSE); pg.click(sel); pg.wait_for_timeout(500)
        def row(name):
            return pg.locator('#ptTable tbody tr', has_text=name)

        def register(name, pid, clothes='', photo=False, ward='東1', hours=None, tag=None, dest='見本の公園'):
            tab('new')
            pg.fill('#pSearch', pid); pg.wait_for_timeout(150)
            chip = pg.locator('#pChips [data-pt]')
            if chip.count():
                chip.first.click(); pg.wait_for_timeout(150)
            else:
                pg.fill('input[name=name]', name); pg.fill('input[name=pid]', pid)
            pg.click(f'#wardRadios label:has-text("{ward}")')
            if hours is not None:
                pg.evaluate(SET, ['input[name=departAt]', pg.evaluate(f"toLocalInput(round15(Date.now()+{hours}*3600000))")])
            pg.click('#dueQuick button[data-h="4"]')
            pg.fill('input[name=dest]', dest)
            pg.fill('textarea[name=clothes]', clothes)
            if photo:
                pg.set_input_files('#photoInput', PHOTO); pg.wait_for_timeout(400)
            if tag:
                pg.select_option('#tagSelect', tag); pg.wait_for_timeout(100)
                if pg.locator('#consentBox input[name=consent]').count():
                    pg.check('#consentBox input[name=consent]')
            pg.fill('input[name=departNurse]', NURSE)
            pg.click('#submitBtn'); pg.wait_for_timeout(800)

        def return_out(pid):
            oid = pg.evaluate("pid=>outings.find(o=>o.pid===pid&&(o.status==='out'||o.status==='search')).id", pid)
            tab('active')
            pg.locator(f'.card[data-id="{oid}"] [data-act=return]').click()
            pg.fill('#dlgForm input[name=nurse]', NURSE); pg.click('#dlgActions button.ok'); pg.wait_for_timeout(700)
            return oid

        # 架空の患者を台帳に入れる
        pg.evaluate("""async()=>{const mk=(pid,name,kana,ward,extra)=>({id:uid(),pid,name,kana,sex:'男',age:'40',ward,adm:'任意入院',famName:'テスト 家族',famRel:'母',famTel:'090-0000-0'+pid.slice(-3),
            consentDate:'',consentWithdrawn:'',consentLog:[],dests:[],count:0,lastOutAt:0,createdAt:Date.now(),...(extra||{})});
          const L=[mk('P0001','テスト 太郎','てすと たろう','東1',{consentDate:'2026-10-01'}),mk('P0002','テスト 花子','てすと はなこ','東1'),mk('P0003','テスト 次郎','てすと じろう','東2'),
            mk('P0004','テスト 四郎','てすと しろう','東1'),mk('P0005','テスト 五郎','てすと ごろう','東1'),mk('P0006','テスト 六郎','てすと ろくろう','東1')];
          for(const x of L){patients.push(x);await dbPut('patients',x);}}""")

        # ================= H2（操作の列）・H1 退院 =================
        tab('patients')
        ops = row('テスト 花子').locator('td').nth(1).locator('button').all_inner_texts()
        assert ops == ['この患者で登録', '修正', '退院', '過去の記録'], ops
        assert pg.locator('#ptTable [data-ptdel]').count() == 0, '削除ボタンが行に残っている'
        assert '入院中（6人）' in pg.inner_text('#ptSeg') and '退院（0人）' in pg.inner_text('#ptSeg')
        row('テスト 花子').locator('[data-ptdis]').click(); pg.wait_for_timeout(200)
        assert pg.evaluate("document.querySelector('#dlgBody input[name=ddate]').value") == pg.evaluate("toDateInput(Date.now())")
        pg.click('#dlgActions button.pri'); pg.wait_for_timeout(200)       # 職員名なしでは退院しない
        assert P('P0002').get('status') != 'discharged'
        staff_ok()
        h = P('P0002')
        assert h['status'] == 'discharged' and h['dischargedAt'] == pg.evaluate("toDateInput(Date.now())"), h
        assert '退院' in h['ledger'][-1]['text'] and h['ledger'][-1]['by'] == NURSE, h['ledger']
        assert row('テスト 花子').count() == 0, '入院中の一覧に残っている'
        pg.click('#ptSeg [data-pts=discharged]'); pg.wait_for_timeout(200)
        assert row('テスト 花子').count() == 1 and '退院（1人）' in pg.inner_text('#ptSeg')
        assert row('テスト 花子').locator('td').nth(1).locator('button').all_inner_texts() == ['修正', '再入院', '過去の記録']
        # 呼び出し候補・チップに出ない
        tab('new'); pg.fill('#pSearch', 'テスト'); pg.wait_for_timeout(200)
        chips = pg.inner_text('#pChips')
        assert 'テスト 花子' not in chips and 'テスト 太郎' in chips, chips
        pg.fill('#pSearch', '')
        # 退院の患者のIDを手で入れても登録しない
        pg.fill('input[name=name]', 'テスト 花子'); pg.fill('input[name=pid]', 'P0002')
        pg.click('#wardRadios label:has-text("東1")'); pg.click('#dueQuick button[data-h="2"]'); pg.fill('input[name=departNurse]', NURSE)
        n0 = pg.evaluate('outings.length'); pg.click('#submitBtn'); pg.wait_for_timeout(500)
        assert pg.evaluate('outings.length') == n0 and '退院' in pg.inner_text('#formErr')
        pg.evaluate("clearPatientForm()")

        # 外出中・予定ありは退院できない
        register('テスト 次郎', 'P0003', ward='東2')
        register('テスト 四郎', 'P0004', hours=3, clothes='')   # 予定
        assert pg.evaluate("outings.find(o=>o.pid==='P0004').status") == 'planned'
        for nm, pid in [('テスト 次郎', 'P0003'), ('テスト 四郎', 'P0004')]:
            tab('patients'); row(nm).locator('[data-ptdis]').click(); pg.wait_for_timeout(200)
            assert '退院にできません' in pg.inner_text('#dlgTitle') and '先に帰院・予定の取消' in pg.inner_text('#dlgBody')
            pg.click('#dlgActions button'); pg.wait_for_timeout(150)
            assert P(pid).get('status') != 'discharged'

        # 再入院（病棟を変える）
        tab('patients'); pg.click('#ptSeg [data-pts=discharged]'); pg.wait_for_timeout(150)
        row('テスト 花子').locator('[data-ptre]').click(); pg.wait_for_timeout(200)
        pg.click('#dlgBody .radios label:has-text("東2")'); pg.select_option('#dlgBody select[name=adm]', '医療保護入院')
        staff_ok()
        h = P('P0002')
        assert h['status'] == 'in' and h['ward'] == '東2' and h['adm'] == '医療保護入院', h
        assert '再入院' in h['ledger'][-1]['text'] and '東1 → 東2' in h['ledger'][-1]['text'], h['ledger']
        assert row('テスト 花子').count() == 0
        pg.click('#ptSeg [data-pts=in]'); pg.wait_for_timeout(150)
        assert row('テスト 花子').count() == 1

        # ================= H2 修正 =================
        row('テスト 太郎').locator('[data-ptedit]').click(); pg.wait_for_timeout(200)
        pg.click('#dlgBody .radios label:has-text("西1")'); pg.fill('#dlgBody input[name=famTel]', '090-0000-0999')
        staff_ok()
        t = P('P0001')
        assert t['ward'] == '西1' and t['famTel'] == '090-0000-0999', t
        last = t['ledger'][-1]['text']
        assert '病棟 東1 → 西1' in last and '家族の電話' in last and t['ledger'][-1]['by'] == NURSE, last
        # 台帳の記録が修正の画面の下に出る・削除ボタンは修正の画面の下
        row('テスト 太郎').locator('[data-ptedit]').click(); pg.wait_for_timeout(200)
        body = pg.inner_text('#dlgBody')
        assert '台帳の記録' in body and '病棟 東1 → 西1' in body and pg.locator('#ptDelBtn').is_visible()
        # IDの重複は保存しない
        pg.fill('#dlgBody input[name=pid]', 'P0003'); pg.fill('#dlgBody input[name=name]', 'テスト 太郎X')
        staff_ok()
        assert pg.evaluate("document.getElementById('dlg').open"), '重複IDなのにダイアログが閉じた'
        assert 'P0003' in pg.inner_text('#toast') and P('P0001')['name'] == 'テスト 太郎'
        pg.click('#dlgActions button:has-text("やめる")'); pg.wait_for_timeout(150)
        # 外出中の記録の病棟は書き換えない
        row('テスト 次郎').locator('[data-ptedit]').click(); pg.wait_for_timeout(200)
        pg.click('#dlgBody .radios label:has-text("東3")'); staff_ok()
        assert P('P0003')['ward'] == '東3' and pg.evaluate("outings.find(o=>o.pid==='P0003').ward") == '東2'

        # ================= H3 同意の撤回・取得日 =================
        assert row('テスト 太郎').locator('[data-ptwd]').inner_text() == '撤回'
        assert row('テスト 花子').locator('[data-ptcd]').inner_text() == '取得日を入れる'
        row('テスト 太郎').locator('[data-ptwd]').click(); pg.wait_for_timeout(200)
        assert 'タグを渡せなくなります' in pg.inner_text('#dlgBody')
        staff_ok('#dlgActions button.bad')
        t = P('P0001')
        assert t['consentWithdrawn'] == pg.evaluate("toDateInput(Date.now())"), t
        assert pg.evaluate("consentState(patients.find(x=>x.pid==='P0001')).st") == 'withdrawn'
        assert '撤回' in row('テスト 太郎').inner_text() and row('テスト 太郎').locator('[data-ptcd]').count() == 1
        # 撤回した人にはタグを渡せない
        n0 = pg.evaluate('outings.length')
        register('テスト 太郎', 'P0001', ward='西1', tag='T-01')
        assert pg.evaluate('outings.length') == n0 and '撤回' in pg.inner_text('#formErr')
        pg.evaluate("clearPatientForm()")
        # 取得日を入れると戻る
        tab('patients'); row('テスト 太郎').locator('[data-ptcd]').click(); pg.wait_for_timeout(200)
        pg.evaluate(SET, ['#dlgBody input[name=cdate]', '2026-11-01']); staff_ok()
        t = P('P0001')
        assert t['consentDate'] == '2026-11-01' and not t['consentWithdrawn'], t
        assert pg.evaluate("consentState(patients.find(x=>x.pid==='P0001')).st") == 'ok'
        register('テスト 太郎', 'P0001', ward='西1', tag='T-01')
        assert pg.evaluate("outings.find(o=>o.pid==='P0001'&&o.status==='out').tagId") == 'T-01'
        return_out('P0001')

        # ================= H5 服装の記入を3件 =================
        for c in ['服A 紺の上着', '服B 灰色のズボン', '服C 白い帽子', '服D 黒いリュック']:
            register('テスト 五郎', 'P0005', clothes=c, photo=(c.startswith('服A')))
            return_out('P0005')
        assert P('P0005')['clothesHist'] == ['服D 黒いリュック', '服C 白い帽子', '服B 灰色のズボン'], P('P0005')['clothesHist']
        assert pg.evaluate("dbKeys('photos').then(k=>k.length)") == 0, '帰院後も写真が残っている'
        register('テスト 五郎', 'P0005', clothes='服C 白い帽子'); return_out('P0005')
        assert P('P0005')['clothesHist'] == ['服C 白い帽子', '服D 黒いリュック', '服B 灰色のズボン'], '同じ文が重なった'
        tab('new'); pg.fill('#pSearch', 'P0005'); pg.wait_for_timeout(150); pg.click('#pChips [data-pt]'); pg.wait_for_timeout(200)
        hb = pg.locator('#clothesHist [data-memo]')
        assert hb.count() == 3
        hb.nth(1).click()
        assert pg.input_value('textarea[name=clothes]') == '服D 黒いリュック'
        pg.evaluate("clearPatientForm()")
        assert pg.locator('#clothesHist [data-memo]').count() == 0

        # ================= H6 変更せずに戻る =================
        tab('plan')
        before = pg.evaluate("JSON.stringify(outings.find(o=>o.pid==='P0004'))"); n0 = pg.evaluate('outings.length')
        pg.locator('#planList .card', has_text='テスト 四郎').locator('[data-pact=edit]').click(); pg.wait_for_timeout(500)
        assert pg.locator('#formBack').is_visible() and pg.inner_text('#formBack') == '変更せずに戻る'
        assert pg.evaluate("document.getElementById('formBack').parentElement===document.getElementById('submitBtn').parentElement")
        pg.fill('input[name=dest]', '書き換えた行き先'); pg.fill('textarea[name=clothes]', '書き換えた服装')
        pg.click('#formBack'); pg.wait_for_timeout(400)
        assert pg.evaluate("document.getElementById('sec-plan').classList.contains('active')")
        assert pg.evaluate("JSON.stringify(outings.find(o=>o.pid==='P0004'))") == before and pg.evaluate('outings.length') == n0
        tab('new')
        assert not pg.locator('#formBack').is_visible(), '通常の登録で「変更せずに戻る」が出ている'

        # ================= H7 GO で写真・服装を任意で =================
        tab('plan')
        pg.locator('#planList .card', has_text='テスト 四郎').locator('[data-pact=go]').click(); pg.wait_for_timeout(300)
        assert '服装の写真（首から下）' in pg.inner_text('#dlgBody')
        pg.set_input_files('#goPhotoInput', PHOTO); pg.wait_for_timeout(500)
        assert pg.locator('#goPhotoPrev img').count() == 1
        pg.fill('#dlgBody textarea[name=goClothes]', '服G 赤いマフラー')
        pg.select_option('#goTag', ''); pg.fill('#dlgForm input[name=nurse]', NURSE); pg.click('#dlgActions button.ok'); pg.wait_for_timeout(800)
        o = pg.evaluate("outings.find(o=>o.pid==='P0004')")
        assert o['status'] == 'out' and o['hasPhoto'] and o['clothes'] == '服G 赤いマフラー', o
        assert pg.evaluate(f"dbKeys('photos').then(k=>k.includes('{o['id']}'))")
        assert P('P0004')['clothesHist'][0] == '服G 赤いマフラー'
        return_out('P0004')
        assert not pg.evaluate(f"dbKeys('photos').then(k=>k.includes('{o['id']}'))"), '帰院で写真が消えていない'
        # 空のままでも出発できる
        register('テスト 六郎', 'P0006', hours=3, clothes='')
        tab('plan')
        pg.locator('#planList .card', has_text='テスト 六郎').locator('[data-pact=go]').click(); pg.wait_for_timeout(300)
        assert pg.input_value('#dlgBody textarea[name=goClothes]') == ''
        pg.select_option('#goTag', ''); pg.fill('#dlgForm input[name=nurse]', NURSE); pg.click('#dlgActions button.ok'); pg.wait_for_timeout(800)
        o6 = pg.evaluate("outings.find(o=>o.pid==='P0006')")
        assert o6['status'] == 'out' and not o6['hasPhoto'] and not o6.get('clothes'), o6

        # ================= H4 部屋・号室をどこにも出さない =================
        # 古い版で保存した「部屋」の値を持つ記録・患者（表示しないだけ）
        pg.evaluate("""async()=>{const p=patients.find(x=>x.pid==='P0003');p.room='105';await dbPut('patients',p);
          const o=outings.find(x=>x.pid==='P0003');o.room='105';await saveOuting(o);
          const t=Date.now()-3*86400000;const r={id:uid(),name:'テスト 七郎',pid:'P0007',ward:'東1',room:'201',adm:'任意入院',kind:'外出',departAt:t,dueAt:t+7200000,dueAtOriginal:t+7200000,returnedAt:t+8000000,returnNurse:'(デモ) 看護師B',
            dest:'見本の駅',alone:true,selfTel:'',famName:'',famRel:'',famTel:'',clothes:'',tagId:'',departNurse:'(デモ) 看護師A',status:'returned',hasPhoto:false,log:[]};outings.push(r);await saveOuting(r);
          window.print=()=>{};lastSig='';await tick();}""")
        bad = lambda t: ('号室' in t) or ('部屋' in t) or ('病室' in t)
        seen = []
        for t in ['active', 'plan', 'new', 'history', 'calendar', 'stats', 'patients']:
            tab(t)
            if t == 'history':
                pg.evaluate("setDay(toDateInput(Date.now()-3*86400000));$('#hTo').value=toDateInput(Date.now());renderHistory()")
            seen.append(pg.inner_text('main'))
        assert not any(bad(x) for x in seen), [x for x in seen if bad(x)][0][:300]
        assert '105' not in seen[0] and '201' not in seen[3]
        # 記録の詳細・修正の画面
        o3 = pg.evaluate("outings.find(o=>o.pid==='P0003').id")
        pg.evaluate(f"dlgDetail(outings.find(o=>o.id==='{o3}'))"); assert not bad(pg.inner_text('#dlg')); pg.click('#dlgActions button')
        pg.evaluate(f"dlgEdit(outings.find(o=>o.id==='{o3}'))"); assert not bad(pg.inner_text('#dlg')) and pg.locator('#dlgBody [name=room]').count() == 0
        pg.click('#dlgActions button:has-text("やめる")')
        tab('new'); assert pg.locator('#newForm [name=room]').count() == 0
        # 印刷（日別一覧・外出中・集計）
        tab('history'); pg.click('#hPrint'); pg.wait_for_timeout(200)
        pa = pg.inner_html('#printArea'); assert not bad(pa) and 'テスト 七郎' in pa, pa[:200]
        pg.evaluate("document.body.classList.remove('pm-history')")
        tab('stats'); pg.click('#stPrint'); pg.wait_for_timeout(200); assert not bad(pg.inner_html('#printArea'))
        pg.evaluate("document.body.classList.remove('pm-history')")
        pg.evaluate("printFull=true"); pg.evaluate("renderActive()"); pg.wait_for_timeout(300)
        assert not bad(pg.inner_text('#activeList')); pg.evaluate("printFull=false")
        # CSV（日別一覧・集計・ひな形）
        tab('history')
        pg.evaluate("setDay(toDateInput(Date.now()-3*86400000));$('#hTo').value=toDateInput(Date.now());renderHistory()")
        for btn, t in [('#csvBtn', 'history'), ('#stCsv', 'stats'), ('#ptCsvTpl', 'patients')]:
            tab(t)
            if t == 'history':
                pg.evaluate("setDay(toDateInput(Date.now()-3*86400000));$('#hTo').value=toDateInput(Date.now());renderHistory()")
            with pg.expect_download() as d:
                pg.click(btn)
            txt = open(d.value.path(), encoding='utf-8-sig').read()
            assert not bad(txt), (btn, txt[:200])
            if btn == '#csvBtn':
                assert 'テスト 七郎' in txt and '201' not in txt.split('テスト 七郎')[1].split('\n')[0]
        # 部屋・病室の列があるCSVも取り込める（無視する）
        csvp = os.path.join(OUT, 'v1110_room.csv')
        open(csvp, 'w', encoding='utf-8-sig').write('氏名,患者ID,病棟,部屋,病室,入院形態\r\nテスト 八郎,P0008,東1,301,301,任意入院\r\n')
        tab('patients'); pg.set_input_files('#ptCsvFile', csvp); pg.wait_for_timeout(500)
        assert 'CSVを取り込めません' not in pg.inner_text('#dlgTitle')
        pg.click('#dlgActions button.pri'); pg.wait_for_timeout(500)
        h8 = P('P0008')
        assert h8 and h8['ward'] == '東1' and not h8.get('room'), h8

        # ================= H8 行き先の3つ（新しいiPad） =================
        dp = pg.evaluate('settings.destPresets')
        assert all(x in dp for x in ['喫煙', '図書館', '加古川のイオン']), dp
        assert len(dp) == len(set(dp))
        tab('new'); chips = pg.inner_text('.pchips[data-preset=dest]')
        assert '加古川のイオン' in chips and '喫煙' in chips
        ctx.close()

        # 既存の設定（1.10.0 まで）にも1回だけ足す。消したものは再び足さない
        ctx2 = b.new_context(viewport={'width': 1024, 'height': 1366})
        pg = open_app(ctx2)
        pg.evaluate("""async()=>{const s=await dbGet('settings','main')||{};s.destPresets=['自宅','見本の公園'];delete s.destAdded1110;await dbPut('settings',s,'main');}""")
        pg.reload(); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(200)
        assert pg.evaluate('settings.destPresets') == ['自宅', '見本の公園', '喫煙', '図書館', '加古川のイオン'], pg.evaluate('settings.destPresets')
        pg.click('nav button[data-tab=settings]'); pg.fill('#sDest', '自宅\n見本の公園\n図書館\n加古川のイオン'); pg.click('#sPresetSave'); pg.wait_for_timeout(300)
        pg.reload(); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(200)
        assert pg.evaluate('settings.destPresets') == ['自宅', '見本の公園', '図書館', '加古川のイオン'], '消した「喫煙」がまた入った'

        # ================= H9 看護師名60人 =================
        names = [f'(デモ) 看護 {i:02d}' for i in range(1, 63)] + ['(デモ) 看護 05']   # 62人＋重複1行
        pg.click('nav button[data-tab=settings]'); pg.fill('#nurseBulk', '\n'.join(names)); pg.click('#nurseBulkBtn'); pg.wait_for_timeout(300)
        nl = pg.evaluate('settings.nurses')
        assert len(nl) == 60 and len(set(nl)) == 60 and nl[0] == '(デモ) 看護 01' and nl[-1] == '(デモ) 看護 60', (len(nl), nl[:2], nl[-2:])
        assert '60人を超える' in pg.inner_text('#toast')
        pg.reload(); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(200)
        assert pg.evaluate('settings.nurses.length') == 60, '再読み込みで60人が残っていない'
        pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(200)
        box = pg.locator('input[name=departNurse] + .nchips')
        assert box.locator(':scope > [data-nurse]').count() == 8
        more = box.locator('[data-nmore]'); assert 'ほかの看護師' in more.inner_text()
        more.click(); pg.wait_for_timeout(150)
        assert box.locator('.nall [data-nurse]').count() == 60
        assert pg.evaluate("(()=>{const a=document.querySelector('#newForm .nall');return a.scrollHeight>a.clientHeight})()"), '枠の中でスクロールしない'
        box.locator('.nall [data-nurse="(デモ) 看護 55"]').click()
        assert pg.input_value('input[name=departNurse]') == '(デモ) 看護 55' and box.locator('.nall').count() == 0
        # 使った人は最近の8人の先頭に来る
        pg.evaluate("rememberNurse('(デモ) 看護 55');attachNurseChips(nf)")
        assert pg.locator('input[name=departNurse] + .nchips > [data-nurse]').first.inner_text() == '(デモ) 看護 55'
        assert pg.evaluate('settings.nurses.length') == 60
        ctx2.close(); b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
