"""2.3.0：新規登録の画面（必須の見分け・下の登録バー・患者欄と連絡先のたたみ・備考のボタン・時刻ボタン・見た目）を assert で確かめる。
A 必須6つの「未入力→✓ 入力済み」、下のバーの数（n／6、同行ありで7）、未入力の名前のボタンでその欄が見える位置に来る、
  すべて入ると「必須はすべて入力済み」、予定の時はバーのボタンの文言が変わる、バーのボタンで登録できる、他のタブではバーが出ない
B 患者を呼び出すと患者欄が1行にたたまれる（氏名・ID・病棟）／「変更」で開く／必須が欠けた患者・手入力ではたたまれない／登録後は開いた状態
  連絡先は入っている時だけたたむ・「変更」で開く／備考は「＋ 備考を書く」で出る
C 出発の8つのボタン・外出の+1〜+10時間・外泊の日付×時刻で入る日時、区分で並びが切り替わる、結果の表示の文言、選択欄にも同じ値が入る
D 両配色 × iPad 横・縦で、主な文字のコントラスト比 4.5 以上・横はみ出しなし・押す部品の高さ 44px 以上
E 赤いアラーム帯・アラーム音無効の帯が、新規登録タブで下のバーやトーストに隠れない
時計は 2026/11/13(金) 10:00（日本時間）に固定する（Date.now が動かないので、ボタンで入る日時がちょうどの値になる）。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst, contrast

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'
NURSE = '(デモ) 看護師A'
N_ASSERT = [0]


def ok(cond, msg=''):
    N_ASSERT[0] += 1
    assert cond, msg


PATIENTS = """async()=>{const L=[
  {pid:'P0001',name:'テスト 太郎',kana:'てすと たろう',sex:'男',age:'45',ward:'東2',adm:'医療保護入院',selfTel:'090-0000-0001',famName:'(デモ) 家族',famRel:'母',famTel:'090-0000-0002',lastDest:'見本の公園'},
  {pid:'',name:'テスト 花子',kana:'てすと はなこ',sex:'女',ward:'東1',adm:'任意入院'},
  {pid:'P0003',name:'テスト 次郎',kana:'てすと じろう',ward:'西1',adm:'任意入院'},
  {pid:'P0004',name:'テスト 三郎',kana:'てすと さぶろう',ward:'',adm:'任意入院'}];
  let i=0;for(const x of L){const p={id:'pt'+(++i),count:1,dests:[],lastOutAt:Date.now()-i*3600000,createdAt:Date.now(),...x};patients.push(p);await dbPut('patients',p);}
  renderPatientChips();}"""


def open_page(b, w=1180, h=820):
    ctx = b.new_context(viewport={'width': w, 'height': h}, timezone_id='Asia/Tokyo', device_scale_factor=1)
    pg = ctx.new_page()
    pg.clock.set_fixed_time(jst(2026, 11, 13, 10, 0))
    pg.goto(URL); pg.wait_for_timeout(600); pg.click('#startOv'); pg.wait_for_timeout(200)
    pg.evaluate("window.tone=function(){}")
    return ctx, pg


def new_tab(pg):
    pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(150)


def vis(pg, sel):
    return pg.locator(sel).is_visible()


def rq_state(pg):
    """必須の欄ごとの [done, rqempty, 札の文字]"""
    return pg.evaluate("""()=>Object.fromEntries(RQ.map(r=>{const b=rqBox(r.k);return [r.k,[b.classList.contains('done'),b.classList.contains('rqempty'),b.querySelector('.rqst').textContent]];}))""")


def bar(pg):
    pg.wait_for_timeout(60)
    return pg.evaluate("""()=>({cnt:document.getElementById('rbCnt').textContent,all:document.getElementById('rbCnt').classList.contains('all'),
      miss:[...document.querySelectorAll('#rbMiss [data-go]')].map(b=>b.textContent),btn:document.getElementById('rbBtn').textContent,
      shown:getComputedStyle(document.getElementById('regBar')).display!=='none'&&!document.getElementById('regBar').hidden})""")


def wait_out(pg, pid):
    for _ in range(40):
        st = pg.evaluate(f"(outings.find(o=>o.pid==='{pid}')||{{}}).status||null")
        if st:
            return st
        pg.wait_for_timeout(50)
    return None


def res_text(pg, sel):
    return ' '.join(pg.inner_text(sel).split())


def val(pg, name):
    return pg.input_value(f'input[name={name}]')


def tp(pg, name):
    """選択欄（日付・時刻）の値"""
    return pg.evaluate(f"(()=>{{const w=nf.elements.{name}._tp;return [w.querySelector('.tp-d').value,w.querySelector('.tp-t').value];}})()")


# ------------------------------------------------------------ A
def part_a(b, errs):
    ctx, pg = open_page(b); pg.on('pageerror', lambda e: errs.append(str(e)))
    new_tab(pg)
    s = bar(pg)
    ok(s['shown'], '新規登録タブで下のバーが出ていない')
    # 開いた直後：出発日時（今）だけ入っている
    ok(s['cnt'] == '必須 1／6', s)
    ok(s['miss'] == ['患者氏名', '患者ID', '病棟', '帰院予定日時', '確認した看護師'], s)
    st = rq_state(pg)
    for k in ['name', 'pid', 'ward', 'dueAt', 'departNurse']:
        ok(st[k] == [False, True, '未入力'], (k, st[k]))
    ok(st['departAt'] == [True, False, '✓ 入力済み'], st['departAt'])
    ok(st['compName'][:2] == [False, False], '単独なのに同行者氏名が必須に出ている')
    ok(pg.locator('#newForm .req').count() == 7, pg.locator('#newForm .req').count())  # 6つ＋同行者氏名（同行ありの時だけ）
    # 任意の印（年齢・行き先・備考など）
    ok(pg.locator('#newForm label:has(input[name=age]) .opt').inner_text() == '任意')
    ok(pg.locator('#newForm label:has(input[name=dest]) .opt').count() == 1)
    ok(pg.locator('#newForm label:has(input[name=name]) .opt').count() == 0, '必須の欄に任意の印')

    # 1つずつ入れる
    pg.fill('input[name=name]', 'テスト 太郎'); s = bar(pg)
    ok(rq_state(pg)['name'] == [True, False, '✓ 入力済み']); ok(s['cnt'] == '必須 2／6', s)
    pg.fill('input[name=pid]', 'P0101'); ok(bar(pg)['cnt'] == '必須 3／6')
    pg.click('#wardRadios label:has-text("東3")'); s = bar(pg)
    ok(rq_state(pg)['ward'][0] and s['cnt'] == '必須 4／6', s)
    ok(s['miss'] == ['帰院予定日時', '確認した看護師'], s)
    # 消すと未入力に戻る
    pg.fill('input[name=pid]', ''); s = bar(pg)
    ok(rq_state(pg)['pid'] == [False, True, '未入力'] and s['cnt'] == '必須 3／6', s)
    pg.fill('input[name=pid]', 'P0101')

    # 未入力の名前のボタン → その欄が画面の見える所に来る（上の帯と下のバーの間）・入力欄にフォーカス
    for k, focus_js in [('departNurse', "document.activeElement===nf.elements.departNurse"),
                        ('dueAt', "document.activeElement&&document.activeElement.classList.contains('tb')&&document.getElementById('dueCol').contains(document.activeElement)")]:
        pg.evaluate('document.activeElement&&document.activeElement.blur()'); pg.wait_for_timeout(450)   # 文字の入力中はバーが隠れる
        pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(100)
        pg.click(f'#rbMiss [data-go={k}]'); pg.wait_for_timeout(900)
        r = pg.evaluate(f"""()=>{{const b=rqBox('{k}').getBoundingClientRect();const top=document.querySelector('.topbar').getBoundingClientRect().bottom;
          const rb=document.getElementById('regBar').querySelector('.rbin').getBoundingClientRect();const bot=rb.height?rb.top:innerHeight;return [b.top,b.bottom,top,bot];}}""")
        ok(r[0] >= r[2] - 1 and r[1] <= r[3] + 1, (k, r))
        ok(pg.evaluate(focus_js), (k, 'フォーカスが移っていない'))
    pg.evaluate('document.activeElement&&document.activeElement.blur()'); pg.wait_for_timeout(450)
    # 患者欄がたたまれている時に「患者氏名」を押すと開いて見える（手入力ではたたまれないので、ここでは表示のままを確かめる）
    ok(vis(pg, '#pFields'))

    # 同行あり → 必須が7つに、同行者氏名が未入力に出る
    pg.click('#newForm .radios label:has(input[name=alone][value="0"])'); s = bar(pg)
    ok(s['cnt'] == '必須 4／7' and '同行者氏名' in s['miss'], s)
    ok(rq_state(pg)['compName'] == [False, True, '未入力'])
    pg.fill('input[name=compName]', '(デモ) 同行者'); s = bar(pg)
    ok(s['cnt'] == '必須 5／7' and '同行者氏名' not in s['miss'], s)
    pg.click('#newForm .radios label:has(input[name=alone][value="1"])'); s = bar(pg)
    ok(s['cnt'] == '必須 4／6', s)

    # 帰院予定・看護師 → すべて入力済み
    pg.click('#dueQuick [data-h="2"]'); ok(bar(pg)['cnt'] == '必須 5／6')
    pg.fill('input[name=departNurse]', NURSE); pg.evaluate('document.activeElement&&document.activeElement.blur()'); pg.wait_for_timeout(450)
    s = bar(pg)
    ok(s['cnt'] == '✓ 必須はすべて入力済み' and s['all'] and s['miss'] == [], s)
    ok(s['btn'] == 'この内容で出発を登録' == pg.inner_text('#submitBtn'), s)
    # 予定の時は文言が変わる（看護師の名前も「登録した看護師」に）
    pg.click('#depQuick [data-m="60"]'); s = bar(pg)
    ok(s['btn'] == '予定として登録' == pg.inner_text('#submitBtn'), s)
    pg.fill('input[name=departNurse]', ''); pg.evaluate('document.activeElement&&document.activeElement.blur()'); pg.wait_for_timeout(450)
    ok(bar(pg)['miss'] == ['登録した看護師'], bar(pg))
    pg.fill('input[name=departNurse]', NURSE); pg.evaluate('document.activeElement&&document.activeElement.blur()'); pg.wait_for_timeout(450)
    pg.click('#depQuick [data-m="0"]'); ok(bar(pg)['btn'] == 'この内容で出発を登録')
    # バーのボタンで登録
    pg.click('#rbBtn')
    ok(wait_out(pg, 'P0101') == 'out', '下のバーのボタンで登録できない')
    o = pg.evaluate("outings.find(o=>o.pid==='P0101')")
    ok(o['ward'] == '東3' and o['dueAt'] - o['departAt'] == 2 * 3600000, o)
    # 他のタブではバーが出ない
    for t in ['active', 'plan', 'calendar', 'history', 'stats', 'patients', 'tags', 'settings']:
        if pg.locator(f'nav button[data-tab={t}]').count() == 0:
            continue
        pg.click(f'nav button[data-tab={t}]'); pg.wait_for_timeout(80)
        ok(not vis(pg, '#regBar') and not pg.evaluate("document.body.classList.contains('rbon')"), t)
    new_tab(pg); ok(vis(pg, '#regBar'))
    # 登録後は入力が空に戻っている
    ok(bar(pg)['cnt'] == '必須 1／6', bar(pg))
    ctx.close()


# ------------------------------------------------------------ B
def part_b(b, errs):
    ctx, pg = open_page(b); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.evaluate(PATIENTS)
    new_tab(pg)
    chip = lambda name: pg.locator('#pChips [data-pt]', has_text=name).first
    ok(vis(pg, '#pFields') and not vis(pg, '#pSum') and not vis(pg, '#cSum'))
    ok(vis(pg, '#noteAdd') and not vis(pg, '#noteLab'))

    # 揃った患者 → たたむ
    chip('テスト 太郎').click(); pg.wait_for_timeout(150)
    ok(vis(pg, '#pSum') and not vis(pg, '#pFields'))
    t = res_text(pg, '#pSum')
    for w in ['テスト 太郎', 'ID P0001', '東2', '医療保護入院', '男 45歳', '✓ 入力済み', '変更']:
        ok(w in t, (w, t))
    ok(vis(pg, '#cSum') and not vis(pg, '#cFields'))
    t = res_text(pg, '#cSum')
    for w in ['連絡先', '本人 090-0000-0001', '家族 (デモ) 家族（母） 090-0000-0002', '変更']:
        ok(w in t, (w, t))
    ok(bar(pg)['cnt'] == '必須 4／6', bar(pg))
    # 患者の「変更」で開く（入力欄の値は消えていない）
    pg.click('#pOpen'); pg.wait_for_timeout(100)
    ok(vis(pg, '#pFields') and not vis(pg, '#pSum'))
    ok(val(pg, 'name') == 'テスト 太郎' and val(pg, 'pid') == 'P0001' and pg.evaluate('nf.elements.ward.value') == '東2')
    ok(pg.evaluate("document.activeElement===nf.elements.name"))
    # 連絡先の「変更」で開く（患者欄はたたんだまま）
    chip('テスト 太郎').click(); pg.wait_for_timeout(150)
    pg.click('#cOpen'); pg.wait_for_timeout(100)
    ok(vis(pg, '#cFields') and not vis(pg, '#cSum') and vis(pg, '#pSum'))
    ok(val(pg, 'famTel') == '090-0000-0002')
    # たたんだ状態で未入力の「患者氏名」を押すと開く
    chip('テスト 太郎').click(); pg.wait_for_timeout(150)
    pg.evaluate("goField('name')"); pg.wait_for_timeout(500)
    ok(vis(pg, '#pFields') and not vis(pg, '#pSum'), 'goField で患者欄が開かない')

    # ID のない患者・病棟のない患者 → たたまない
    for nm in ['テスト 花子', 'テスト 三郎']:
        chip(nm).click(); pg.wait_for_timeout(150)
        ok(vis(pg, '#pFields') and not vis(pg, '#pSum'), nm)
    # 連絡先のない患者 → 患者はたたむ・連絡先は開いたまま
    chip('テスト 次郎').click(); pg.wait_for_timeout(150)
    ok(vis(pg, '#pSum') and vis(pg, '#cFields') and not vis(pg, '#cSum'))
    # 取り消して手入力 → たたまない
    pg.click('#pUnload'); pg.wait_for_timeout(150)
    ok(vis(pg, '#pFields') and not vis(pg, '#pSum') and val(pg, 'name') == '')
    pg.fill('input[name=name]', 'テスト 四郎'); pg.fill('input[name=pid]', 'P0005'); pg.click('#wardRadios label:has-text("東1")')
    pg.fill('input[name=selfTel]', '090-0000-0005'); pg.evaluate('document.activeElement&&document.activeElement.blur()'); pg.wait_for_timeout(1100)
    ok(vis(pg, '#pFields') and not vis(pg, '#pSum') and vis(pg, '#cFields') and not vis(pg, '#cSum'), '手入力でたたまれた')

    # 備考のボタン
    pg.click('#noteAdd'); pg.wait_for_timeout(100)
    ok(vis(pg, '#noteLab') and not vis(pg, '#noteAdd') and pg.evaluate("document.activeElement===nf.elements.note"))
    pg.fill('input[name=note]', '見本の備考')
    # たたんだ状態から登録 → 登録後は開いた状態・備考はボタンに戻る
    chip('テスト 次郎').click(); pg.wait_for_timeout(150)
    ok(vis(pg, '#pSum'))
    pg.click('#dueQuick [data-h="3"]'); pg.fill('input[name=departNurse]', NURSE); pg.evaluate('document.activeElement&&document.activeElement.blur()'); pg.wait_for_timeout(450)
    pg.click('#rbBtn'); ok(wait_out(pg, 'P0003') == 'out')
    o = pg.evaluate("outings.find(o=>o.pid==='P0003')")
    ok(o['name'] == 'テスト 次郎' and o['ward'] == '西1' and o['note'] == '見本の備考', o)
    new_tab(pg)
    ok(vis(pg, '#pFields') and not vis(pg, '#pSum') and vis(pg, '#cFields') and not vis(pg, '#cSum'))
    ok(vis(pg, '#noteAdd') and not vis(pg, '#noteLab'))
    ok(not vis(pg, '#depMan') and not vis(pg, '#dueMan'))
    ctx.close()


# ------------------------------------------------------------ C
def part_c(b, errs):
    ctx, pg = open_page(b); pg.on('pageerror', lambda e: errs.append(str(e)))
    new_tab(pg)
    # 開いた直後
    ok(res_text(pg, '#depRes') == '今日 11/13(金) 10:00', res_text(pg, '#depRes'))
    ok(res_text(pg, '#dueRes') == 'まだ選んでいません', res_text(pg, '#dueRes'))
    ok(pg.locator('#depQuick .tb').all_inner_texts() == ['今から', '10分後', '20分後', '30分後', '1時間後', '2時間後', '3時間後', '明日'])
    ok(pg.locator('#depQuick .tb.on').inner_text() == '今から')
    ok(not vis(pg, '#depTimes'))
    # 出発の8つ
    for m, want in [('0', '10:00'), ('10', '10:10'), ('20', '10:20'), ('30', '10:30'), ('60', '11:00'), ('120', '12:00'), ('180', '13:00')]:
        pg.click(f'#depQuick [data-m="{m}"]'); pg.wait_for_timeout(30)
        ok(val(pg, 'departAt') == '2026-11-13T' + want, (m, val(pg, 'departAt')))
        ok(tp(pg, 'departAt') == ['2026-11-13', want], (m, tp(pg, 'departAt')))
        ok(pg.locator('#depQuick .tb.on').get_attribute('data-m') == m)
        plan = int(m) > 30
        ok(res_text(pg, '#depRes') == f'今日 11/13(金) {want}' + (' 予定として登録' if plan else ''), res_text(pg, '#depRes'))
        ok(pg.evaluate("document.getElementById('depCol').classList.contains('isplan')") == plan)
    pg.click('#depQuick [data-tmr="1"]'); pg.wait_for_timeout(30)
    ok(val(pg, 'departAt') == '2026-11-14T13:00', val(pg, 'departAt'))  # 時刻はそれまでの値（13:00）を引き継ぐ
    ok(vis(pg, '#depTimes') and pg.locator('#depTimes .tb').all_inner_texts() == ['09:00', '10:00', '13:00', '15:00'])
    ok(pg.evaluate('document.activeElement===document.querySelector("#depTimes .tb")'), '明日の後、時刻のボタンにフォーカスが移らない')
    for t in ['09:00', '15:00']:
        pg.click(f'#depTimes [data-t="{t}"]'); pg.wait_for_timeout(30)
        ok(val(pg, 'departAt') == '2026-11-14T' + t and tp(pg, 'departAt') == ['2026-11-14', t])
        ok(pg.locator('#depTimes .tb.on').inner_text() == t and pg.locator('#depQuick .tb.on').get_attribute('data-tmr') == '1')
    ok(res_text(pg, '#depRes') == '明日 11/14(土) 15:00 予定として登録', res_text(pg, '#depRes'))
    pg.click('#depQuick [data-m="0"]'); pg.wait_for_timeout(30)
    ok(not vis(pg, '#depTimes') and val(pg, 'departAt') == '2026-11-13T10:00')

    # 外出：+1〜+10時間（出発 10:00 から）
    grp = lambda k: pg.locator(f'#dueQuick [data-kind="{k}"]')
    ok(grp('外出').count() == 1 and grp('外出').is_visible() and all(not grp('外泊').nth(i).is_visible() for i in range(grp('外泊').count())))
    ok(grp('外出').locator('.tb').all_inner_texts() == ['+1時間', '+2時間', '+3時間', '+4時間', '+6時間', '+8時間', '+10時間'])
    for h in [1, 2, 3, 4, 6, 8, 10]:
        pg.click(f'#dueQuick [data-h="{h}"]'); pg.wait_for_timeout(30)
        want = f'{10 + h:02d}:00'
        ok(val(pg, 'dueAt') == '2026-11-13T' + want and tp(pg, 'dueAt') == ['2026-11-13', want], (h, val(pg, 'dueAt'), tp(pg, 'dueAt')))
        ok(pg.locator('#dueQuick [data-h].on').get_attribute('data-h') == str(h))
        ok(res_text(pg, '#dueRes') == f'今日 11/13(金) {want} 出発から {h}時間', res_text(pg, '#dueRes'))
    # 出発を後ろにずらすと「出発から」の表示も変わる・帰院より後なら「出発より前です」
    pg.click('#depQuick [data-m="120"]'); pg.wait_for_timeout(30)
    ok(res_text(pg, '#dueRes') == '今日 11/13(金) 20:00 出発から 8時間', res_text(pg, '#dueRes'))
    pg.evaluate("(()=>{const i=nf.elements.dueAt;i.value='2026-11-13T11:30';i.dispatchEvent(new Event('input',{bubbles:true}))})()"); pg.wait_for_timeout(60)
    ok(res_text(pg, '#dueRes') == '今日 11/13(金) 11:30 出発より前です', res_text(pg, '#dueRes'))
    pg.evaluate("(()=>{const i=nf.elements.dueAt;i.value='2026-11-13T15:10';i.dispatchEvent(new Event('input',{bubbles:true}))})()"); pg.wait_for_timeout(60)
    ok(res_text(pg, '#dueRes') == '今日 11/13(金) 15:10 出発から 約3時間15分', res_text(pg, '#dueRes'))
    ok(pg.locator('#dueQuick .tb.on').count() == 0)
    pg.click('#depQuick [data-m="0"]')

    # 外泊：日付 × 時刻
    pg.click('#kindRadios label:has-text("外泊")'); pg.wait_for_timeout(60)
    ok(not grp('外出').is_visible() and grp('外泊').count() == 2 and grp('外泊').nth(0).is_visible() and grp('外泊').nth(1).is_visible(), '区分で並びが切り替わらない')
    ok([' '.join(x.split()) for x in grp('外泊').nth(0).locator('.tb').all_inner_texts()] == ['明日 11/14(土)', '明後日 11/15(日)', '3日後 11/16(月)'],
       grp('外泊').nth(0).locator('.tb').all_inner_texts())
    ok(grp('外泊').nth(1).locator('.tb').all_inner_texts() == ['10:00', '13:00', '15:00', '17:00'])
    pg.evaluate("(()=>{const i=nf.elements.dueAt;i.value='';i.dispatchEvent(new Event('input',{bubbles:true}))})()")
    pg.click('#dueQuick [data-d="1"]'); pg.wait_for_timeout(30)
    ok(val(pg, 'dueAt') == '2026-11-14T10:00', val(pg, 'dueAt'))   # 時刻が無ければ出発の時刻
    pg.click('#dueQuick [data-t="15:00"]'); pg.wait_for_timeout(30)
    ok(val(pg, 'dueAt') == '2026-11-14T15:00' and tp(pg, 'dueAt') == ['2026-11-14', '15:00'], tp(pg, 'dueAt'))
    pg.click('#dueQuick [data-d="3"]'); pg.wait_for_timeout(30)
    ok(val(pg, 'dueAt') == '2026-11-16T15:00', val(pg, 'dueAt'))   # 時刻はそのまま
    pg.click('#dueQuick [data-t="17:00"]'); pg.wait_for_timeout(30)
    ok(val(pg, 'dueAt') == '2026-11-16T17:00' and tp(pg, 'dueAt') == ['2026-11-16', '17:00'])
    ok(pg.locator('#dueQuick [data-d].on').get_attribute('data-d') == '3' and pg.locator('#dueQuick [data-t].on').inner_text() == '17:00')
    ok(res_text(pg, '#dueRes') == '3日後 11/16(月) 17:00 出発から 3日7時間', res_text(pg, '#dueRes'))
    pg.click('#dueQuick [data-d="2"]'); pg.wait_for_timeout(30)
    ok(res_text(pg, '#dueRes') == '明後日 11/15(日) 17:00 出発から 2日7時間', res_text(pg, '#dueRes'))
    # 外出に戻すと +時間 の並び
    pg.click('#kindRadios label:has-text("外出")'); pg.wait_for_timeout(60)
    ok(grp('外出').is_visible() and not grp('外泊').nth(0).is_visible())

    # 「細かく選ぶ」で選択欄を開くと、ボタンで入れた値がそのまま見える。選択欄で変えた値も結果の表示に出る
    pg.click('.tfine[data-man="dueMan"]')
    ok(vis(pg, '#dueMan') and pg.inner_text('.tfine[data-man="dueMan"]') == '細かい選択を閉じる')
    ok(pg.locator('#dueMan .tp-d').evaluate("s=>s.selectedOptions[0].text") == '明後日 11/15(日)' and pg.locator('#dueMan .tp-t').input_value() == '17:00')
    pg.select_option('#dueMan .tp-t', '18:15'); pg.wait_for_timeout(60)
    ok(val(pg, 'dueAt') == '2026-11-15T18:15' and res_text(pg, '#dueRes').startswith('明後日 11/15(日) 18:15'), res_text(pg, '#dueRes'))
    pg.click('.tfine[data-man="dueMan"]'); ok(not vis(pg, '#dueMan') and pg.inner_text('.tfine[data-man="dueMan"]') == '細かく選ぶ')
    # 時刻の候補は定数から作られている
    ok(pg.evaluate("JSON.stringify([DEP_TMR_TIMES,GAIHAKU_DUE_TIMES])") == '[["09:00","10:00","13:00","15:00"],["10:00","13:00","15:00","17:00"]]')
    ctx.close()


# ------------------------------------------------------------ D
CT = ['#sec-new>h2', '#newForm legend', '#newForm label:has(input[name=age])', '#newForm .rq.rqempty .rqst', '#newForm .rq.done .rqst',
      '#newForm .req', '#newForm .opt', '#depRes .d', '#depRes .t', '#dueRes .s', '#depQuick .tb:not(.on)', '#depQuick .tb.on',
      '#kindRadios label:has(input:checked)', '#kindRadios label:not(:has(input:checked))', '.tfine', '#tagBtns .tb.on', '#tagBtns .tb:not(.on)',
      '#pSum .pst', '#pSum .pok', '#pOpen', '#cSum .ch', '#cSum .pst span:not(.ch)', '#noteAdd', '#newForm .hint',
      '#rbCnt', '#rbMiss button', '#rbMiss .rblab', '#rbBtn', '#submitBtn', '#wardRadios label:has(input:checked)', '#pChips .chip b']
CT_PLAN = ['#tagBtns .tb.two small', '#depRes .plan', '#depRes .t', '#depTimes .tb.on', '#depTimes .tb:not(.on)']
CT_GAIHAKU = ['#dueQuick [data-d].on', '#dueQuick [data-d]:not(.on) small', '#dueQuick [data-t]:not(.on)']
CT_ALL = ['#rbCnt']


def part_d(b, errs):
    for w, h, tag in [(1180, 820, 'yoko'), (1024, 1366, 'tate')]:
        ctx, pg = open_page(b, w, h); pg.on('pageerror', lambda e: errs.append(str(e)))
        dec = ctx.new_page()
        pg.evaluate(PATIENTS)
        for th in ['light', 'dark']:
            pg.click('nav button[data-tab=settings]'); pg.click(f'#thmSeg [data-thm={th}]'); pg.wait_for_timeout(150)
            ok(pg.evaluate('document.documentElement.dataset.theme') == th)
            new_tab(pg)
            pg.locator('#pChips [data-pt]', has_text='テスト 太郎').first.click(); pg.wait_for_timeout(900)   # 呼び出しの後のなめらかな移動が終わるまで待つ
            pg.evaluate("window.scrollTo({top:0,behavior:'instant'})"); pg.wait_for_timeout(100)
            bad = []

            def check(sels, state):
                for sel in sels:
                    loc = pg.locator(sel)
                    n = loc.count()
                    ok(n > 0, f'{state} {sel} が無い')
                    for i in range(min(n, 3)):
                        el = loc.nth(i)
                        if not el.is_visible():
                            continue
                        r = contrast(pg, el, dec)
                        if r < 4.5:
                            bad.append((state, sel, i, round(r, 2)))
                    N_ASSERT[0] += 1

            # 「未入力」の前の小さな点（::before）は文字の背景ではないので、測る間だけ見えなくする（場所は変わらない）
            pg.evaluate("(()=>{const st=document.createElement('style');st.id='__dot';st.textContent='#newForm .rqst::before{visibility:hidden!important}';document.head.appendChild(st);})()")
            check(['#dueRes .e'], 'empty')
            pg.evaluate("(()=>{const i=nf.elements.dueAt;i.value='2026-11-13T09:00';i.dispatchEvent(new Event('input',{bubbles:true}))})()")
            pg.wait_for_timeout(1100)
            check(['#dueRes .s.warn'], 'warn')
            pg.click('#dueQuick [data-h="2"]'); pg.wait_for_timeout(1100)
            check(CT, 'basic')
            pg.click('#depQuick [data-tmr="1"]'); pg.click('#depTimes [data-t="10:00"]'); pg.wait_for_timeout(1100)
            check(CT_PLAN, 'plan')
            pg.click('#kindRadios label:has-text("外泊")'); pg.click('#dueQuick [data-d="1"]'); pg.wait_for_timeout(1100)
            check(CT_GAIHAKU, 'gaihaku')
            pg.fill('input[name=departNurse]', NURSE); pg.evaluate('document.activeElement&&document.activeElement.blur()'); pg.wait_for_timeout(1100)
            check(CT_ALL, 'all')
            ok(not bad, f'{tag} {th} コントラスト不足 {bad}')
            pg.evaluate("document.getElementById('__dot').remove()")
            # 細かく選ぶを開いた状態も含め、横はみ出しなし・押す部品の高さ 44px 以上
            pg.click('.tfine[data-man="depMan"]'); pg.click('.tfine[data-man="dueMan"]'); pg.wait_for_timeout(100)
            sw = pg.evaluate('document.documentElement.scrollWidth')
            ok(sw <= w, f'{tag} {th} 横はみ出し {sw}>{w}')
            small = pg.evaluate("""()=>{const out=[];document.querySelectorAll('#sec-new button,#sec-new .radios label,#sec-new select,#sec-new input:not([type=radio]):not([type=checkbox]):not([type=file]),#regBar button').forEach(e=>{
              if(e.closest('.vh')||e.classList.contains('vh'))return;const r=e.getBoundingClientRect();if(!r.width||!r.height||!e.offsetParent)return;
              if(r.height<44-0.5)out.push((e.id||e.className||e.tagName)+':'+(e.textContent||'').trim().slice(0,12)+':'+Math.round(r.height));});return out;}""")
            ok(not small, f'{tag} {th} 高さ44px未満 {small}')
            # 言葉の途中で折り返さない（ボタン・結果の表示は1行の高さに収まる）
            wrap = pg.evaluate("""()=>{const out=[];document.querySelectorAll('#sec-new .tb:not(.two),#regBar button,#rbCnt,.tres .d,.tres .t,.tfine,#newForm .radios label,#pOpen,#cOpen,#noteAdd').forEach(e=>{
              if(!e.offsetParent)return;const tw=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);let t;
              while((t=tw.nextNode())){if(!t.textContent.trim())continue;const rs=document.createRange();rs.selectNodeContents(t);
                const n=new Set([...rs.getClientRects()].filter(r=>r.width>0).map(r=>Math.round(r.top)));   // 1つの言葉（文字のかたまり）が2行に分かれていないか
                if(n.size>1)out.push((e.id||e.className)+':'+t.textContent.trim().slice(0,12));}});return out;}""")
            ok(not wrap, f'{tag} {th} 折り返し {wrap}')
            pg.click('.tfine[data-man="depMan"]'); pg.click('.tfine[data-man="dueMan"]')
            pg.click('#pUnload'); pg.wait_for_timeout(100)
            pg.click('#kindRadios label:has-text("外出")')
        ctx.close()


# ------------------------------------------------------------ E
def part_e(b, errs):
    for w, h, tag in [(1180, 820, 'yoko'), (1024, 1366, 'tate')]:
        ctx, pg = open_page(b, w, h); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.evaluate("""async()=>{const now=Date.now();const o={id:'ov1',name:'テスト 超過',pid:'P0900',ward:'東1',adm:'任意入院',kind:'外出',departAt:now-3*3600000,dueAt:now-20*60000,dueAtOriginal:now-20*60000,
          dest:'見本の駅',alone:true,selfTel:'',famName:'',famRel:'',famTel:'',clothes:'見本の服装',tagId:'',consent:false,departNurse:'(デモ) 看護師A',status:'out',createdAt:now,hasPhoto:false,log:[]};
          outings.push(o);await saveOuting(o);settings.soundOff=true;updateSoundBtn();lastSig='';await tick();}""")
        pg.wait_for_timeout(1200)
        new_tab(pg)
        ok(vis(pg, '#banner') and vis(pg, '#muteBar') and vis(pg, '#regBar'), tag)
        for scroll in ['top', 'bottom']:
            pg.evaluate('window.scrollTo(0,0)' if scroll == 'top' else 'window.scrollTo(0,document.documentElement.scrollHeight)'); pg.wait_for_timeout(120)
            pg.evaluate("toast('見本のお知らせです。登録しました',8000)"); pg.wait_for_timeout(80)
            r = pg.evaluate("""()=>{const R=s=>{const b=document.querySelector(s).getBoundingClientRect();return {t:b.top,b:b.bottom,l:b.left,r:b.right};};
              const hit=s=>{const e=document.querySelector(s);const b=e.getBoundingClientRect();const pts=[[.1,.5],[.5,.5],[.9,.5],[.5,.15],[.5,.85]];
                return pts.every(([x,y])=>{const t=document.elementFromPoint(b.left+b.width*x,b.top+b.height*y);return t&&e.contains(t);});};
              return {ban:R('#banner'),mute:R('#muteBar'),bar:R('#regBar .rbin'),toast:R('#toast'),vh:innerHeight,banHit:hit('#banner'),muteHit:hit('#muteBar'),
                toastHit:hit('#toast'),btnHit:hit('#bannerAck')&&hit('#muteOn')};}""")
            ok(r['banHit'] and r['muteHit'] and r['btnHit'], (tag, scroll, '帯が何かに隠れている', r))
            ok(r['ban']['t'] >= 0 and r['mute']['b'] <= r['bar']['t'], (tag, scroll, r))
            ok(r['toastHit'] and r['toast']['b'] <= r['bar']['t'] and r['toast']['t'] >= r['mute']['b'], (tag, scroll, 'トーストが帯・バーと重なる', r))
        pg.screenshot(path=os.path.join(OUT, f'v230_alarm_{tag}.png'))
        ctx.close()


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for f in [part_a, part_b, part_c, part_d, part_e]:
            f(b, errs); print(f.__name__, 'ok', N_ASSERT[0])
        b.close()
    print('asserts', N_ASSERT[0])
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
