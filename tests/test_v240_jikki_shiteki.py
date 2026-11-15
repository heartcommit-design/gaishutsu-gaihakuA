"""2.4.0：iPad 実機で出た指摘 1〜5 を assert で確かめる。
1 入れ忘れ・入力の誤りの知らせが、開いているダイアログの中の、その欄のすぐそばに出て見えている（トーストに頼らない）。
  出発（GO）・帰院の登録・はぐれ・帰院予定の変更・捜索終了・対応記録・登録内容の修正（3つのボタン）・GOの取消・患者情報の修正・退院・再入院・
  同意の撤回・同意書の取得日・タグの登録（画面）・内容を確認・変更して出発（画面）。ダイアログの間に出たトーストはダイアログより手前。
  GO の必須の見た目（未入力／✓ 入力済み）とタグのボタン。
2 予定：ふだんは1行（タグ・氏名・病棟と区分・出発予定・帰院予定・出発まで・GO と詳細だけ）、「詳細」で開閉、日付の見出し、使い方のたたみ、過ぎた予定。
3 新規登録：選んだ患者の要約（見出し・氏名26px以上・濃い面に白・コントラスト4.5以上）、候補のボタンの選択中、下のバーの氏名。
4 タブの帯が全タブでスクロールしても見えている・移動先が帯やバーに隠れない・最悪の場合の本文の高さ・印刷では出ない。
5 デモ：件数・30日先までの分布・同行者の割合と続柄・他院受診・職員30人・消した時に利用者の看護師名が残る・入れ直しで重複しない・すべて消える。
両配色 × iPad 横 1180×820・縦 1024×1366 で横はみ出しなし。時計は 2026/11/13(金) 10:00（日本時間）に固定する。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst, contrast

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'
N_ASSERT = [0]
INFO = {}


def ok(cond, msg=''):
    N_ASSERT[0] += 1
    assert cond, msg


def open_page(b, w=1180, h=820, t=None):
    ctx = b.new_context(viewport={'width': w, 'height': h}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
    pg = ctx.new_page()
    pg.clock.set_fixed_time(t or jst(2026, 11, 13, 10, 0))
    pg.goto(URL); pg.wait_for_timeout(600); pg.click('#startOv'); pg.wait_for_timeout(200)
    pg.evaluate("window.tone=function(){}")
    return ctx, pg


def demo_in(pg):
    pg.click('nav button[data-tab=settings]'); pg.click('#demoIn')
    pg.wait_for_function("document.getElementById('toast').textContent.includes('デモデータを入れました')", timeout=30000)
    pg.wait_for_timeout(200)


def theme(pg, th):
    pg.click('nav button[data-tab=settings]'); pg.click(f'#thmSeg [data-thm={th}]'); pg.wait_for_timeout(150)


def ns(t):
    return ''.join(t.split())


def no_hscroll(pg, tag):
    sw = pg.evaluate('[document.documentElement.scrollWidth,document.documentElement.clientWidth]')
    ok(sw[0] <= sw[1], (tag, '横にはみ出し', sw))


def quiet_toast(pg):
    pg.evaluate("toastHide();document.getElementById('toast').textContent=''")


# ダイアログの中の知らせ：[欄のセレクタ, …] の順に、知らせが欄のすぐ上にある・ダイアログの中・欄が赤枠。最初の知らせと欄は見えていて、フォーカスはその欄
ERRCHK = """(sels)=>{const d=document.querySelector('dialog[open]')||document.body;const es=[...d.querySelectorAll('.ferr')];const dr=d.getBoundingClientRect();
  const out={n:es.length,texts:es.map(e=>e.textContent),open:!!document.querySelector('#dlg[open]'),pairs:[]};
  sels.forEach((s,i)=>{const f=d.querySelector(s);const e=es[i];if(!f||!e){out.pairs.push({s,missing:true});return;}
    const mark=f.closest('[data-ferr]')||f;const er=e.getBoundingClientRect(),fr=mark.getBoundingClientRect();
    out.pairs.push({s,gap:fr.top-er.bottom,inDlg:d.contains(e),inv:mark.classList.contains('invalid'),color:getComputedStyle(e).color,
      vis:er.height>0&&er.top>=dr.top-1&&er.bottom<=dr.bottom+1&&fr.top>=dr.top-1&&fr.top<=dr.bottom-10&&er.top>=0&&er.bottom<=innerHeight,
      hit:(()=>{const t=document.elementFromPoint(er.left+Math.min(er.width/2,60),er.top+er.height/2);return !!t&&(t===e||e.contains(t));})()});});
  const ae=document.activeElement;const f0=d.querySelector(sels[0]);const m0=f0&&(f0.closest('[data-ferr]')||f0);
  out.focus=!!m0&&(ae===f0||m0.contains(ae));
  const t=document.getElementById('toast');out.toast=getComputedStyle(t).display!=='none'&&!!t.textContent;
  return out;}"""


def check_errs(pg, sels, tag, need_focus=True):
    r = pg.evaluate(ERRCHK, sels)
    ok(r['n'] >= len(sels), (tag, '知らせの数', r))
    for i, x in enumerate(r['pairs']):
        ok(not x.get('missing'), (tag, '知らせ・欄がない', x, r))
        ok(x['inDlg'] and x['inv'] and 0 <= x['gap'] <= 12, (tag, '欄のすぐそばでない／赤枠でない', x))
        ok(x['color'] not in ('rgb(0, 0, 0)',), (tag, x))
        if i == 0:
            ok(x['vis'] and x['hit'], (tag, '知らせ・欄が見えていない（何かの裏）', x))
    if need_focus:
        ok(r['focus'], (tag, 'フォーカスが欄に移っていない'))
    ok(not r['toast'], (tag, 'トーストで知らせている'))
    return r


def toast_front(pg):
    """トーストが最前面（popover）で、ダイアログの暗い幕（::backdrop）がかかっていない：画面上の色がトーストの地の色そのまま"""
    r = pg.evaluate("""()=>{const t=document.getElementById('toast');const r=t.getBoundingClientRect();const m=getComputedStyle(t).backgroundColor.match(/[\\d.]+/g).map(Number);
      return {x:r.left+8,y:r.top+r.height/2,bg:m.slice(0,3),open:t.matches(':popover-open'),dlg:!!document.querySelector('dialog[open]')};}""")
    png = pg.screenshot(clip={'x': r['x'], 'y': r['y'], 'width': 1, 'height': 1}, animations='disabled')
    from PIL import Image
    import io
    px = Image.open(io.BytesIO(png)).convert('RGB').getpixel((0, 0))
    return r['open'] and r['dlg'] and all(abs(px[i] - r['bg'][i]) <= 8 for i in range(3))


def click_ok(pg, label=None):
    if label:
        pg.locator('#dlgActions button', has_text=label).click()
    else:
        pg.locator('#dlgActions button').last.click()
    pg.wait_for_timeout(250)


# ------------------------------------------------------------ 1
def part1(b, errs):
    for w, h, tg in [(1180, 820, 'yoko'), (1024, 1366, 'tate')]:
        for th in ['light', 'dark']:
            tag = f'{tg}-{th}'
            ctx, pg = open_page(b, w, h); pg.on('pageerror', lambda e: errs.append(str(e)))
            theme(pg, th); demo_in(pg)
            if pg.locator('#prLater').is_visible():
                pg.click('#prLater')
            # 同意書のない患者の予定（GO でタグを渡す時に同意書の欄を出す）
            pg.evaluate("""async()=>{const now=Date.now();const p={id:'ptnc',pid:'P0009',name:'テスト 同意なし',kana:'てすと',sex:'男',age:'40',ward:'東2',adm:'任意入院',consentDate:'',consentWithdrawn:'',consentLog:[],dests:[],count:0,lastOutAt:0,createdAt:now};
              patients.push(p);await dbPut('patients',p);
              const o={id:'plnc',name:p.name,pid:p.pid,ward:'東2',adm:'任意入院',kind:'外出',departAt:now+3*3600000,dueAt:now+6*3600000,dueAtOriginal:now+6*3600000,dest:'見本の公園',alone:true,
                selfTel:'',famName:'',famRel:'',famTel:'',clothes:'',tagId:'',consent:false,departNurse:'(デモ) 看護師 青木',status:'planned',createdAt:now,hasPhoto:false,log:[],patientId:'ptnc'};
              outings.push(o);await saveOuting(o);}""")
            pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(300)
            # --- 出発（GO）：タグも看護師も未入力
            card = pg.locator('#planList .card').first
            ok(not card.locator('.tagbadge:not(.none)').count(), '先頭の予定はタグ未予約のはず')
            card.locator('[data-pact=go]').click(); pg.wait_for_timeout(300)
            # 必須の見た目（新規登録と同じ：未入力）とタグのボタン（選択欄は隠して残す）
            st = pg.evaluate("""()=>({tag:[...document.querySelector('#goTagRq').classList],tagSt:document.querySelector('#goTagRq .rqst').textContent,
              nurse:[...document.querySelector('#goNurseRq').classList],nurseSt:document.querySelector('#goNurseRq .rqst').textContent,
              btns:[...document.querySelectorAll('#goTagBtns [data-gotag]')].map(b=>b.textContent),selHidden:document.getElementById('goTag').classList.contains('vh'),
              opts:[...document.getElementById('goTag').options].map(o=>o.value)})""")
            ok('rqempty' in st['tag'] and st['tagSt'] == '未入力' and 'rqempty' in st['nurse'] and st['nurseSt'] == '未入力', st)
            ok(st['selHidden'] and st['opts'][0] == '__' and len(st['btns']) == len(st['opts']) - 1 and st['btns'][-1].startswith('タグなし'), st)
            quiet_toast(pg); click_ok(pg, '出発（GO）')
            r = check_errs(pg, ['#goTagBtns', 'input[name=nurse]'], tag + ' GO')
            ok(r['open'] and '渡すタグを選んで' in r['texts'][0] and '看護師' in r['texts'][1], r)
            # ダイアログの間に出たトーストは手前に見える
            pg.evaluate("toast('見本のお知らせです',6000)"); pg.wait_for_timeout(100)
            ok(toast_front(pg), (tag, 'トーストがダイアログの裏（暗い幕がかかっている）'))
            ok(pg.evaluate("""()=>{const t=document.getElementById('toast').getBoundingClientRect();return [...document.querySelectorAll('#dlgActions button')].every(b=>{const r=b.getBoundingClientRect();return r.bottom<=t.top||r.top>=t.bottom||r.right<=t.left||r.left>=t.right;});}"""), (tag, 'トーストがダイアログのボタンに重なる'))
            quiet_toast(pg)
            # タグのボタンを押すと知らせが消え、「✓ 入力済み」になる
            pg.locator('#goTagBtns [data-gotag="T-04"]').click(); pg.wait_for_timeout(100)
            r2 = pg.evaluate("""()=>({v:document.getElementById('goTag').value,on:document.querySelector('#goTagBtns .tb.on')?.dataset.gotag,st:document.querySelector('#goTagRq .rqst').textContent,
              ferr:document.querySelectorAll('#dlg .ferr').length,inv:document.querySelectorAll('#goTagBtns.invalid').length})""")
            ok(r2 == {'v': 'T-04', 'on': 'T-04', 'st': '✓ 入力済み', 'ferr': 1, 'inv': 0}, r2)
            no_hscroll(pg, tag + ' GO')
            pg.screenshot(path=os.path.join(OUT, f'v240_go_{tag}.png'))
            # 看護師名のボタンで入れると、知らせが消えて「✓ 入力済み」
            pg.locator('#dlgBody .nchips [data-nurse]').first.click(); pg.wait_for_timeout(100)
            ok(pg.evaluate("[document.querySelectorAll('#dlg .ferr').length,document.querySelector('#goNurseRq .rqst').textContent]") == [0, '✓ 入力済み'])
            click_ok(pg, 'やめる')
            # --- GO：同意書の欄（取得日を消し・チェックなし）
            pg.locator('#planList .card', has_text='テスト 同意なし').locator('[data-pact=go]').click(); pg.wait_for_timeout(300)
            pg.locator('#goTagBtns [data-gotag="T-04"]').click(); pg.wait_for_timeout(100)
            pg.evaluate("document.querySelector('#dlgBody input[name=gcDate]').value=''")
            pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 青木')
            quiet_toast(pg); click_ok(pg, '出発（GO）')
            r = check_errs(pg, ['input[name=gcDate]', 'input[name=gcOk]'], tag + ' GO 同意書')
            ok('取得日' in r['texts'][0] and 'チェック' in r['texts'][1], r)
            click_ok(pg, 'やめる')
            # --- 外出中の人の各ダイアログ（直接開く）
            oid = "outings.find(o=>o.pid==='D1052')"
            cases = [
                ('帰院の登録', f"dlgReturn({oid})", None, ['input[name=nurse]']),
                ('はぐれ・行方不明', f"dlgLost({oid})", None, ['input[name=staff]']),
                ('帰院予定の変更', f"dlgExtend({oid},false)", None, ['input[name=reason]', 'input[name=staff]']),
                ('所在確認・捜索終了', f"dlgExtend({oid},true)", None, ['input[name=reason]', 'input[name=staff]']),
                ('対応記録', f"dlgLog({oid})", '内容を記録', ['textarea[name=memo]']),
                ('登録内容の修正', f"dlgEdit({oid})", '修正を保存', ['input[name=reason]', 'input[name=staff]']),
                ('誤登録の取消', f"dlgEdit({oid})", '誤登録として取り消す', ['input[name=reason]', 'input[name=staff]']),
            ]
            for name, js, btn, sels in cases:
                pg.evaluate(js); pg.wait_for_timeout(250); quiet_toast(pg)
                click_ok(pg, btn)
                check_errs(pg, sels, f'{tag} {name}')
                no_hscroll(pg, f'{tag} {name}')
                pg.keyboard.press('Escape'); pg.wait_for_timeout(150)
            # 帰院時刻が出発より前
            pg.evaluate(f"dlgReturn({oid})"); pg.wait_for_timeout(250)
            pg.fill('#dlgBody input[name=nurse]', '(デモ) 看護師 青木')
            pg.evaluate("""(()=>{const i=document.querySelector('#dlgBody input[name=at]');i.value=toLocalInput(Date.now()-3*86400000);})()""")
            quiet_toast(pg); click_ok(pg)
            r = check_errs(pg, ['input[name=at]'], tag + ' 帰院時刻', need_focus=False)
            ok('出発時刻' in r['texts'][0], r)
            pg.keyboard.press('Escape'); pg.wait_for_timeout(150)
            # 修正で何も変えない → ボタンのすぐ上に「変更はありません」
            pg.evaluate(f"dlgEdit({oid})"); pg.wait_for_timeout(250)
            pg.fill('#dlgBody input[name=reason]', '見本の理由'); pg.fill('#dlgBody input[name=staff]', '(デモ) 看護師 青木')
            quiet_toast(pg); click_ok(pg, '修正を保存')
            r = pg.evaluate("""()=>{const e=document.querySelector('#dlg .ferr.fgen');const a=document.getElementById('dlgActions');if(!e)return null;
              const er=e.getBoundingClientRect(),ar=a.getBoundingClientRect();return {t:e.textContent,gap:ar.top-er.bottom,open:document.getElementById('dlg').open};}""")
            ok(r and '変更はありません' in r['t'] and 0 <= r['gap'] <= 20 and r['open'], r)
            pg.keyboard.press('Escape'); pg.wait_for_timeout(150)
            # GO の取消（GO した直後の予定）
            pg.evaluate("""async()=>{const o=outings.find(x=>x.status==='planned'&&x.id!=='plnc');await goPlan(o,'(デモ) 看護師 青木','',null,{});window.__undo=o.id;}"""); pg.wait_for_timeout(300)
            pg.evaluate("dlgUndo(outings.find(o=>o.id===window.__undo))"); pg.wait_for_timeout(250); quiet_toast(pg)
            click_ok(pg, '予定に戻す')
            check_errs(pg, ['input[name=reason]', 'input[name=staff]'], tag + ' GOの取消')
            pg.keyboard.press('Escape'); pg.wait_for_timeout(150)
            # 台帳のダイアログ
            pid = "patients.find(p=>p.pid==='D1040')"
            pg.evaluate(f"dlgPtEdit({pid})"); pg.wait_for_timeout(250)
            pg.fill('#dlgBody input[name=name]', ''); quiet_toast(pg); click_ok(pg, '修正を保存')
            check_errs(pg, ['input[name=name]', 'input[name=staff]'], tag + ' 患者情報の修正')
            # ID の重複は欄のそばに
            pg.fill('#dlgBody input[name=name]', '(デモ) 見本 修正'); pg.fill('#dlgBody input[name=pid]', 'D1041'); pg.fill('#dlgBody input[name=staff]', '(デモ) 看護師 青木')
            quiet_toast(pg); click_ok(pg, '修正を保存')
            r = check_errs(pg, ['input[name=pid]'], tag + ' IDの重複')
            ok('D1041' in r['texts'][0], r)
            pg.keyboard.press('Escape'); pg.wait_for_timeout(150)
            for name, js, btn, sels in [('退院', f"dlgDischarge({pid})", '退院にする', ['input[name=staff]']),
                                        ('同意の撤回', f"dlgWithdraw({pid})", '撤回を記録', ['input[name=staff]']),
                                        ('同意書の取得日', f"dlgConsentDate({pid})", '取得日を保存', ['input[name=staff]'])]:
                pg.evaluate(js); pg.wait_for_timeout(250); quiet_toast(pg); click_ok(pg, btn)
                check_errs(pg, sels, f'{tag} {name}')
                pg.keyboard.press('Escape'); pg.wait_for_timeout(150)
            # 再入院（病棟を外した状態）
            pg.evaluate(f"(()=>{{const p={pid};p.status='discharged';dlgReadmit(p);document.querySelectorAll('#dlgBody input[name=ward]').forEach(r=>r.checked=false);}})()"); pg.wait_for_timeout(250)
            quiet_toast(pg); click_ok(pg, '再入院にする')
            check_errs(pg, ['.radios.wards', 'input[name=staff]'], tag + ' 再入院')
            pg.keyboard.press('Escape'); pg.wait_for_timeout(150)
            pg.evaluate(f"{pid}.status='in'")
            # タグの登録（画面）：空・重複
            pg.click('nav button[data-tab=tags]'); pg.wait_for_timeout(200)
            quiet_toast(pg); pg.click('#tAdd'); pg.wait_for_timeout(200)
            r = check_errs(pg, ['#tNewId'], tag + ' タグの登録')
            pg.fill('#tNewId', 'T-01'); quiet_toast(pg); pg.click('#tAdd'); pg.wait_for_timeout(200)
            r = check_errs(pg, ['#tNewId'], tag + ' タグの重複')
            ok('すでに' in r['texts'][0], r)
            # 内容を確認・変更して出発（画面）：看護師を入れずに登録 → 欄のそばに知らせ、帯やバーに隠れない
            pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(300)
            pg.locator('#planList .card').nth(1).locator('[data-pact=toggle]').click(); pg.wait_for_timeout(300)
            pg.locator('#planList .card').nth(1).locator('[data-pact=edit]').click(); pg.wait_for_timeout(500)
            pg.click('#rbBtn'); pg.wait_for_timeout(900)
            r = pg.evaluate("""()=>{const e=document.querySelector('#newForm .ferr');const f=document.querySelector('input[name=departNurse]');if(!e)return null;const er=e.getBoundingClientRect(),fr=f.getBoundingClientRect();
              const rb=document.body.classList.contains('kbd')?innerHeight:document.querySelector('#regBar .rbin').getBoundingClientRect().top;return {t:e.textContent,gap:fr.top-er.bottom,top:er.top,st:stickTop(),fb:fr.bottom,rb};}""")
            ok(r and '看護師' in r['t'] and 0 <= r['gap'] <= 12 and r['top'] >= r['st'] and r['fb'] <= r['rb'], (tag, '新規登録の知らせ', r))
            ctx.close()


# ------------------------------------------------------------ 2
HELP = '出発日時が先の登録はここに入ります。予定の段階で服装写真を撮っておけば、出発の時は「出発（GO）」を押し、渡すタグと看護師名を選ぶだけです。タグは予定で予約しておくこともできます（予約すると出発日まで他の患者には使えません）。帰院予定は、出発が早まっても遅れても変わりません。写真を直したい時は「内容を確認・変更して出発」を使います。'


def part2(b, errs):
    for w, h, tg in [(1180, 820, 'yoko'), (1024, 1366, 'tate')]:
        for th in ['light', 'dark']:
            tag = f'{tg}-{th}'
            ctx, pg = open_page(b, w, h); pg.on('pageerror', lambda e: errs.append(str(e)))
            theme(pg, th); demo_in(pg)
            pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(400)
            # 使い方：初めは閉じていて、押すと開く（文言はそのまま）
            ok(not pg.locator('#planHelp').is_visible() and pg.inner_text('#planHelpBtn') == '使い方')
            pg.click('#planHelpBtn'); pg.wait_for_timeout(100)
            ok(pg.locator('#planHelp').is_visible() and ''.join(pg.inner_text('#planHelp').split()) == ''.join(HELP.split()), pg.inner_text('#planHelp'))
            pg.click('#planHelpBtn'); pg.wait_for_timeout(100); ok(not pg.locator('#planHelp').is_visible())
            rows = pg.evaluate("""()=>[...document.querySelectorAll('#planList .card.prow')].map(c=>{const o=outings.find(x=>x.id===c.dataset.id);const vis=e=>!!e&&e.getClientRects().length>0;
              return {tag:c.querySelector('.tagbadge').textContent.trim(),name:c.querySelector('.name').textContent,sub:c.querySelector('.who .sub').textContent,times:c.querySelector('.times').textContent,
                cnt:c.querySelector('[data-pcount]').textContent,btns:[...c.querySelectorAll('button')].filter(vis).map(b=>b.textContent),body:vis(c.querySelector('.prbody')),
                h:c.getBoundingClientRect().height,o:{tag:o.tagId,name:o.name,ward:o.ward,kind:o.kind,dep:fmt(o.departAt),due:fmt(o.dueAt),t:o.departAt}};})""")
            ok(len(rows) == pg.evaluate("outings.filter(o=>o.status==='planned').length") >= 16, len(rows))
            for r in rows:
                o = r['o']
                ok(r['tag'] == (o['tag'] or 'タグ出発時'), r)
                ok(r['name'] == o['name'] and r['sub'] == f"{o['ward']}・{o['kind']}", r)
                ok(f"出発予定 {o['dep']}" in r['times'] and f"帰院予定 {o['due']}" in r['times'], r)
                ok(r['cnt'].startswith('出発まで '), r)
                ok(r['btns'] == ['出発（GO）', '詳細'] and not r['body'], r)
                ok(r['h'] <= 100, ('1行にたたまれていない', r))
            ok([r['o']['t'] for r in rows] == sorted(r['o']['t'] for r in rows), '出発予定の早い順でない')
            # 日付の見出し：今日・明日・11/15(日)…、件数も合う
            heads = pg.evaluate("""()=>[...document.querySelectorAll('#planList .pday')].map(h=>({t:h.textContent,day:h.dataset.day,n:[...document.querySelectorAll('#planList .card.prow')].filter(c=>{const o=outings.find(x=>x.id===c.dataset.id);return toDateInput(o.departAt)===h.dataset.day;}).length}))""")
            ok(heads[0]['t'].startswith('今日') and '11/13(金)' in heads[0]['t'] and heads[1]['t'].startswith('明日') and heads[2]['t'].startswith('11/15(日)'), heads)
            ok(all(f"{x['n']}件" in x['t'] for x in heads) and sum(x['n'] for x in heads) == len(rows), heads)
            ok(pg.evaluate("""()=>{const L=[...document.querySelectorAll('#planList>*')];let d=null;return L.every(e=>{if(e.classList.contains('pday')){d=e.dataset.day;return true;}const o=outings.find(x=>x.id===e.dataset.id);return toDateInput(o.departAt)===d;});}"""))
            no_hscroll(pg, tag + ' 予定たたみ')
            # 詳細で開く・もう一度で閉じる
            c = pg.locator('#planList .card.prow').nth(1)
            c.locator('[data-pact=toggle]').click(); pg.wait_for_timeout(300)
            c = pg.locator('#planList .card.prow').nth(1)
            t = c.inner_text()
            ok(c.locator('.prbody').is_visible() and all(x in t for x in ['行き先', '同行', '準備', '登録', '内容を確認・変更して出発', '予定を修正（出発しない）', '予定を取り消す']), t)
            ok(c.locator('img.thumb, .nophoto').count() == 1 and c.locator('[data-pact=toggle]').get_attribute('aria-expanded') == 'true' and c.locator('[data-pact=toggle]').inner_text() == '閉じる')
            ok(pg.locator('#planList .prbody').count() == 1, 'ほかの予定まで開いた')
            no_hscroll(pg, tag + ' 予定ひらく')
            c.locator('[data-pact=toggle]').click(); pg.wait_for_timeout(300)
            ok(pg.locator('#planList .prbody').count() == 0 and pg.locator('#planList .card.prow').nth(1).locator('[data-pact=toggle]').inner_text() == '詳細')
            # 時刻が進み、出発予定を過ぎた予定：たたんだ行でも分かる（今の表示・色）
            pg.clock.set_fixed_time(jst(2026, 11, 13, 11, 50)); pg.wait_for_timeout(1300)
            late = pg.evaluate("""()=>{const c=document.querySelector('#planList .card.prow');return {cls:[...c.classList],lbl:c.querySelector('.lbl').textContent,cnt:c.querySelector('[data-pcount]').textContent,
              bg:getComputedStyle(c).backgroundColor,bd:getComputedStyle(c).borderTopColor,other:getComputedStyle(document.querySelectorAll('#planList .card.prow')[2]).backgroundColor,
              warn:getComputedStyle(document.documentElement).getPropertyValue('--warn').trim()};}""")
            ok('late' in late['cls'] and late['lbl'] == '出発予定時刻を過ぎています' and late['cnt'] == '20分 経過' and late['bg'] != late['other'], late)
            # 「出発まで」が毎秒進む
            pg.clock.set_fixed_time(jst(2026, 11, 13, 11, 55)); pg.wait_for_timeout(1300)
            ok(pg.evaluate("document.querySelector('#planList .card.prow [data-pcount]').textContent") == '25分 経過')
            pg.screenshot(path=os.path.join(OUT, f'v240_plan_{tag}.png'))
            ctx.close()


# ------------------------------------------------------------ 3
def part3(b, errs):
    for w, h, tg in [(1180, 820, 'yoko'), (1024, 1366, 'tate')]:
        ctx, pg = open_page(b, w, h); pg.on('pageerror', lambda e: errs.append(str(e)))
        dec = ctx.new_page()
        demo_in(pg)
        for th in ['light', 'dark']:
            tag = f'{tg}-{th}'
            theme(pg, th)
            pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(300)
            pg.fill('#pSearch', 'D1030'); pg.wait_for_timeout(150)
            # 未選択：下のバーは「患者未選択」
            ok(ns(pg.inner_text('#rbWho')) == '登録する患者患者未選択', pg.inner_text('#rbWho'))
            pg.locator('#pChips [data-pt]').first.click(); pg.wait_for_timeout(900)
            nm = pg.input_value('input[name=name]')
            r = pg.evaluate("""()=>{const s=document.getElementById('pSum'),n=s.querySelector('.pnm'),cs=getComputedStyle(n),ss=getComputedStyle(s);
              return {vis:!s.hidden,cap:s.querySelector('.pcap').textContent,name:n.textContent,fs:parseFloat(cs.fontSize),fw:+cs.fontWeight,bg:ss.backgroundColor,col:cs.color,
                meta:s.querySelector('.pmeta').textContent,open:!!s.querySelector('#pOpen')};}""")
            ok(r['vis'] and r['cap'] == '登録する患者' and r['name'] == nm and r['fs'] >= 26 and r['fw'] >= 700 and r['open'], r)
            ok('ID D1030' in r['meta'] and '東1' in r['meta'], r)
            bg = [int(x) for x in r['bg'][r['bg'].index('(') + 1:r['bg'].index(')')].split(',')[:3]]
            ok(sum(bg) / 3 < 110 and bg[2] > bg[0], ('濃紺の面でない', r['bg']))
            ok(r['col'] == 'rgb(255, 255, 255)', r)
            for sel in ['#pSum .pnm', '#pSum .pcap', '#pSum .pmeta', '#pSum .pok', '#pOpen', '#pChips .chip.sel b']:
                c = contrast(pg, pg.locator(sel).first, dec)
                ok(c >= 4.5, (tag, sel, round(c, 2)))
            # 候補のボタン：選んだ人だけ選択中
            sel = pg.evaluate("[...document.querySelectorAll('#pChips [data-pt]')].map(b=>[b.classList.contains('sel'),b.getAttribute('aria-pressed'),b.querySelector('b').textContent])")
            ok(sel[0][0] and sel[0][1] == 'true' and sel[0][2] == nm and all(not x[0] for x in sel[1:]), sel)
            # 下のバー：氏名 さん（どこまでスクロールしても）。未入力のボタンと重ならない・iPad 縦でも収まる
            for y in ['0', 'document.documentElement.scrollHeight']:
                pg.evaluate(f'window.scrollTo(0,{y})'); pg.wait_for_timeout(200)
                rb = pg.evaluate("""()=>{const R=s=>document.querySelector(s).getBoundingClientRect();const w=R('#rbWho'),c=R('#rbCnt'),b=R('#rbBtn'),i=R('#regBar .rbin');
                  const n=document.querySelector('#rbWho .rbwn');
                  return {t:document.getElementById('rbWho').innerText,wr:w.right,cl:c.left,bl:b.left,br:b.right,ih:i.height,vw:innerWidth,bt:i.top,vh:innerHeight,trunc:n.scrollWidth>n.clientWidth,
                    miss:[...document.querySelectorAll('#rbMiss button')].every(x=>{const r=x.getBoundingClientRect();return r.left>=w.right&&r.right<=b.left;})};}""")
                ok(ns(rb['t']) == ns(f'登録する患者{nm}さん') and not rb['trunc'], rb)
                ok(rb['wr'] <= rb['cl'] and rb['br'] <= rb['vw'] and rb['miss'] and rb['ih'] <= 140 and rb['bt'] < rb['vh'], (tag, rb))
            # 手入力：入れた氏名が出る。選択中の印は外れる
            pg.click('#pOpen'); pg.fill('input[name=name]', 'テスト 手入力'); pg.evaluate('document.activeElement.blur()'); pg.wait_for_timeout(1200)
            ok(ns(pg.inner_text('#rbWho')) == '登録する患者テスト手入力さん' and pg.locator('#pChips .chip.sel').count() == 0)
            pg.locator('#pChips [data-pt]').first.click(); pg.wait_for_timeout(700)
            no_hscroll(pg, tag + ' 新規登録')
            pg.click('#pUnload'); pg.wait_for_timeout(1200)
            ok(ns(pg.inner_text('#rbWho')) == '登録する患者患者未選択' and pg.locator('#pChips .chip.sel').count() == 0)
        ctx.close()


# ------------------------------------------------------------ 4
def part4(b, errs):
    for w, h, tg in [(1180, 820, 'yoko'), (1024, 1366, 'tate')]:
        ctx, pg = open_page(b, w, h); pg.on('pageerror', lambda e: errs.append(str(e)))
        demo_in(pg)
        if pg.locator('#prLater').is_visible():
            pg.click('#prLater')
        pg.evaluate("settings.soundOff=true;updateSoundBtn();lastSig='';tick()"); pg.wait_for_timeout(1200)
        ok(pg.locator('#banner').is_visible() and pg.locator('#muteBar').is_visible(), '帯2本が出ていない')
        for th in ['light', 'dark']:
            theme(pg, th)
            for t in ['active', 'plan', 'new', 'calendar', 'history', 'stats', 'patients', 'tags', 'settings']:
                pg.click(f'nav button[data-tab={t}]'); pg.wait_for_timeout(250)
                if t == 'plan':
                    pg.locator('#planList [data-pact=toggle]').nth(2).click(); pg.wait_for_timeout(200)
                for y in ['600', 'document.documentElement.scrollHeight']:
                    pg.evaluate(f'window.scrollTo(0,{y})'); pg.wait_for_timeout(150)
                    r = pg.evaluate("""()=>{const tb=document.querySelector('.topbar').getBoundingClientRect(),n=document.querySelector('nav').getBoundingClientRect();
                      const hits=[...document.querySelectorAll('nav button')].map(b=>{const r=b.getBoundingClientRect();const e=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return !!e&&b.contains(e)&&r.height>=44;});
                      return {sy:scrollY,tb:tb.bottom,nt:n.top,nb:n.bottom,hits,stuck:document.getElementById('navWrap').classList.contains('stuck')};}""")
                    ok(r['nt'] >= r['tb'] - 1 and r['nt'] <= r['tb'] + 12 and all(r['hits']), (t, th, 'タブの帯が見えない・押せない', r))
                    if r['sy'] > 5:
                        ok(r['stuck'], (t, r))
                no_hscroll(pg, f'{tg} {th} {t}')
            # 最悪の場合（アラーム帯＋音無効の帯＋タブ＋下のバー）：新規登録の本文の見える高さ
            pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(300)
            pg.evaluate('window.scrollTo(0,700)'); pg.wait_for_timeout(1200)
            m = pg.evaluate("""()=>{const n=document.getElementById('navWrap').getBoundingClientRect(),i=document.querySelector('#regBar .rbin').getBoundingClientRect(),tb=document.querySelector('.topbar').getBoundingClientRect();
              return {top:Math.round(n.bottom),bar:Math.round(i.top),body:Math.round(i.top-n.bottom),topbar:Math.round(tb.height),nav:Math.round(n.height),regbar:Math.round(innerHeight-i.top),vh:innerHeight};}""")
            INFO[f'{tg}-{th}'] = m
            ok(m['body'] >= 380, ('本文の見える高さが足りない', m))
            pg.screenshot(path=os.path.join(OUT, f'v240_saiaku_{tg}_{th}.png'))
            # 未入力の欄へ移るボタン：移った先が上の帯・タブと下のバーに隠れない
            for k in pg.evaluate("[...document.querySelectorAll('#rbMiss [data-go]')].map(b=>b.dataset.go)"):
                pg.evaluate('document.activeElement&&document.activeElement.blur();window.scrollTo(0,0)'); pg.wait_for_timeout(450)   # 文字の欄にフォーカスがある間は下のバーが隠れる
                pg.click(f'#rbMiss [data-go={k}]'); pg.wait_for_timeout(900)
                r = pg.evaluate("""(k)=>{const b=rqBox(k).getBoundingClientRect();const top=stickTop(),bot=document.body.classList.contains('kbd')?innerHeight:document.querySelector('#regBar .rbin').getBoundingClientRect().top;
                  return {bt:b.top,bb:b.bottom,top,bot};}""", k)
                ok(r['bt'] >= r['top'] - 1 and min(r['bb'], r['top'] + 200) <= r['bot'], (tg, th, k, '移った先が帯・バーに隠れる', r))
            pg.evaluate('document.activeElement&&document.activeElement.blur()'); pg.wait_for_timeout(400)
        # 印刷では出さない（タブの帯の固定は印刷に影響しない）
        pg.emulate_media(media='print')
        ok(pg.evaluate("getComputedStyle(document.getElementById('navWrap')).display") == 'none')
        pg.emulate_media(media='screen')
        ctx.close()
    print('最悪の場合の本文の高さ', INFO)


# ------------------------------------------------------------ 5
def part5(b, errs):
    ctx, pg = open_page(b); pg.on('pageerror', lambda e: errs.append(str(e)))
    ok('他院受診' in pg.evaluate('settings.destPresets'))
    # 利用者が登録した看護師名
    pg.click('nav button[data-tab=settings]')
    pg.fill('#nurseBulk', '見本 看護師X\n見本 看護師Y'); pg.click('#nurseBulkBtn'); pg.wait_for_timeout(200)
    ok(pg.evaluate('settings.nurses') == ['見本 看護師X', '見本 看護師Y'])
    hint = ' '.join(pg.locator('#demoIn').locator('xpath=../..').inner_text().split())
    ok(all(x in hint for x in ['54人', '外出・外泊中7人', '予定19件', '帰院済みの記録10件', '架空の職員30人', '看護師24人', 'PSW 6人']), hint)
    demo_in(pg)
    toast = pg.inner_text('#toast')
    ok('54人・外出・外泊中7人・予定19件・帰院済みの記録10件・架空の職員30人' in toast, toast)
    d = pg.evaluate("""()=>{const now=Date.now(),day0=tkDayStart(now),P=outings.filter(o=>o.status==='planned'),A=outings.filter(isActive),R=outings.filter(o=>o.status==='returned');
      const dn=settings.demoNurses||[];
      return {pts:patients.length,plan:P.length,act:A.length,ret:R.length,
        days:P.map(o=>Math.round((tkDayStart(o.departAt)-day0)/86400000)),past:P.filter(o=>o.departAt<=now).length,
        wk:P.map(o=>[new Date(o.departAt).getDay(),o.kind]),rsv:P.filter(o=>o.tagId&&tags.find(t=>t.id===o.tagId&&t.status==='reserved'&&t.outingId===o.id)).length,
        noph:P.filter(o=>!o.hasPhoto).length,comp:[...A,...P].filter(o=>!o.alone).length,all:A.length+P.length,
        rels:[...new Set([...A,...P].filter(o=>!o.alone).map(o=>o.compRel))],tels:[...A,...P].filter(o=>!o.alone).every(o=>/^090-0000-\\d{4}$/.test(o.compTel)),
        names:[...A,...P].filter(o=>!o.alone).every(o=>!!o.compName.trim()),
        hosp:P.filter(o=>/^他院受診（.+）$/.test(o.dest)).map(o=>o.dest),
        nurses:settings.nurses.slice(),dn,
        dep:[...A,...P,...R].every(o=>dn.includes(o.departNurse)),retN:R.every(o=>dn.includes(o.returnNurse)),
        calPlan:(()=>{showTab('calendar');return document.querySelectorAll('#calGrid .f.plan').length;})(),
        photos:P.filter(o=>o.hasPhoto).length};}""")
    print('demo', {k: v for k, v in d.items() if k not in ('nurses', 'dn', 'wk')})
    ok(d['pts'] == 54 and d['act'] == 7 and 16 <= d['plan'] <= 20 and d['ret'] == 10, d)
    ok(d['past'] == 0 and min(d['days']) == 0 and max(d['days']) == 30 and len(set(d['days'])) >= 15, d['days'])
    ok(len({x // 7 for x in d['days']}) >= 5, ('1か月に散らばっていない', d['days']))
    we = [k for wd, k in d['wk'] if wd in (0, 5, 6)]; wd_ = [k for wd, k in d['wk'] if wd not in (0, 5, 6)]
    ok(we.count('外泊') > len(we) / 2 and wd_.count('外出') > len(wd_) / 2, d['wk'])
    ok(2 <= d['rsv'] <= 5 and 2 <= d['noph'] <= 6, d)
    ok(d['comp'] / d['all'] >= 0.5, (d['comp'], d['all']))
    ok(set(['母', '父', '妻', '夫', '兄', '姉', '弟', '妹', '息子', '娘', 'その他の親族', '施設職員']) <= set(d['rels']) and d['tels'] and d['names'], d['rels'])
    ok(len(d['hosp']) >= 3 and len(set(d['hosp'])) >= 3, d['hosp'])
    dn = d['dn']
    ok(len(dn) == 30 and sum(x.startswith('(デモ) 看護師 ') for x in dn) == 24 and sum(x.startswith('(デモ) PSW ') for x in dn) == 6, dn)
    sur = [x.split(' ')[-1] for x in dn]
    psur = set(pg.evaluate("patients.map(p=>p.name.replace('(デモ) ','').split(' ')[0])"))
    ok(len(set(sur)) == 30 and not (set(sur) & psur), (sur, psur & set(sur)))
    ok(d['nurses'][:2] == ['見本 看護師X', '見本 看護師Y'] and d['nurses'][2:] == dn, d['nurses'])
    ok(d['dep'] and d['retN'], '出発確認・帰院確認・登録者が職員30人の中から使われていない')
    ok(d['calPlan'] >= 12, ('カレンダーに予定が出ない', d['calPlan']))
    ok(pg.evaluate("dbKeys('photos').then(k=>k.length)") == 4 + d['photos'])
    # 看護師名の候補：先頭8人＋ほか（全32人）。「ほか」は名前の順・広い枠
    pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(300)
    box = pg.locator('input[name=departNurse] + .nchips')
    ok(box.locator('[data-nurse]').count() == 8 and box.locator('[data-nmore]').inner_text() == 'ほかの看護師（全32人）')
    box.locator('[data-nmore]').click(); pg.wait_for_timeout(200)
    al = pg.evaluate("""()=>{const a=document.querySelector('#newForm .nall');const L=[...a.querySelectorAll('[data-nurse]')].map(b=>b.dataset.nurse);
      const cols=new Set([...a.querySelectorAll('[data-nurse]')].map(b=>Math.round(b.getBoundingClientRect().left))).size;return {L,cols,w:a.getBoundingClientRect().width,
      trunc:[...a.querySelectorAll('[data-nurse]')].filter(b=>b.scrollWidth>b.clientWidth).length};}""")
    coll = pg.evaluate("(L)=>[...L].sort(NURSE_COLL.compare)", al['L'])
    ok(len(al['L']) == 32 and al['L'] == coll and al['cols'] >= 4 and al['trunc'] == 0, al)
    box.locator('.nall [data-nurse="(デモ) PSW 土屋"]').click()
    ok(pg.input_value('input[name=departNurse]') == '(デモ) PSW 土屋')
    # 入っている間は入れ直しても増えない
    demo_in_again = pg.evaluate("document.querySelector('#demoIn').click()"); pg.wait_for_timeout(600)
    ok(pg.evaluate('[patients.length,settings.nurses.length]') == [54, 32])
    # 消すと：デモの職員名だけ消え、利用者の看護師名と順番は残る。予定・記録・写真・タグも消える
    pg.click('nav button[data-tab=settings]'); pg.click('#demoOut'); pg.wait_for_timeout(1200)
    r = pg.evaluate("""async()=>({n:settings.nurses.slice(),dn:settings.demoNurses||null,o:outings.length,p:patients.length,ph:(await dbKeys('photos')).length,
      t:tags.map(t=>t.id+':'+t.status),db:(await dbGet('settings','main')).nurses,mgr:document.getElementById('nurseMgr').innerText})""")
    ok(r['n'] == ['見本 看護師X', '見本 看護師Y'] and r['db'] == r['n'] and r['dn'] is None, r)
    ok(r['o'] == 0 and r['p'] == 0 and r['ph'] == 0 and r['t'] == [f'T-0{i}:available' for i in range(1, 6)], r)
    ok('(デモ)' not in r['mgr'], r['mgr'])
    # 入れ直しても重複しない
    demo_in(pg)
    r = pg.evaluate("({n:settings.nurses.length,u:new Set(settings.nurses).size,p:patients.length,pl:outings.filter(o=>o.status==='planned').length,t:tags.length})")
    ok(r == {'n': 32, 'u': 32, 'p': 54, 'pl': 19, 't': 12}, r)
    # 30人を足すと60人を超える時は、超えない分だけ足し、足した分だけを覚える
    pg.click('nav button[data-tab=settings]'); pg.click('#demoOut'); pg.wait_for_timeout(1200)
    pg.evaluate("settings.nurses=[...Array(45)].map((_,i)=>'見本 職員'+(i+1));saveSettings()")
    demo_in(pg)
    r = pg.evaluate("[settings.nurses.length,(settings.demoNurses||[]).length,settings.nurses[0]]")
    ok(r == [60, 15, '見本 職員1'], r)
    pg.click('nav button[data-tab=settings]'); pg.click('#demoOut'); pg.wait_for_timeout(1200)
    ok(pg.evaluate("settings.nurses.length") == 45)
    ctx.close()


def part6(b, errs):
    """スマホ幅（作り込まない）：横にはみ出さない"""
    ctx, pg = open_page(b, 390, 844); pg.on('pageerror', lambda e: errs.append(str(e)))
    demo_in(pg)
    for t in ['plan', 'new']:
        pg.click(f'nav button[data-tab={t}]'); pg.wait_for_timeout(300)
        if t == 'plan':
            pg.locator('#planList [data-pact=toggle]').first.click(); pg.wait_for_timeout(200)
        if t == 'new':
            pg.locator('#pChips [data-pt]').first.click(); pg.wait_for_timeout(600)
        no_hscroll(pg, 'phone ' + t)
    ctx.close()


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for f in [part1, part2, part3, part4, part5, part6]:
            f(b, errs); print(f.__name__, 'ok', N_ASSERT[0])
        b.close()
    print('asserts', N_ASSERT[0])
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
