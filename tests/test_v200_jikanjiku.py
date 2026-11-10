"""2.0.0（試作版）：「外出・外泊中」を時間軸で現す。
時計を固定して架空の患者を入れ、バーの左端・幅が出発／帰院予定の時刻と軸の範囲から計算した値に一致すること（許容 2px）、
現在線の位置、時刻を進めると範囲と位置が動くこと（行は作り直さない）、範囲外のバーが端で切れ日時が出ること、
予定超過の継ぎ足し、「時間軸／一覧」の切り替えと保存、3つの幅で横はみ出しなし、
時間軸のまま「帰院した」「詳細」が現行どおり動くことを assert で確かめる。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst, ms

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'
H = 3600000
D = lambda d, h, mi=0: ms(2026, 11, d, h, mi)

# 架空の患者（出発・帰院予定は 2026/11/10 の日本時間）
PTS = [
    ('t1', '(デモ) 佐藤 一郎', 'T-07', '東1', '外出', D(10, 13, 0), D(10, 14, 10)),   # 予定超過
    ('t2', '(デモ) 鈴木 花子', 'T-12', '東1', '外出', D(10, 12, 30), D(10, 15, 0)),   # まもなく
    ('t3', '(デモ) 渡辺 久美子', '', '本3', '外出', D(10, 13, 45), D(10, 15, 30)),   # 外出中（タグなし）
    ('t4', '(デモ) 高橋 健', 'T-03', '東2', '外出', D(10, 13, 30), D(10, 16, 30)),
    ('t5', '(デモ) 伊藤 誠', 'T-09', '東1', '外出', D(10, 14, 0), D(10, 17, 0)),
    ('t6', '(デモ) 田中 美咲', 'T-15', '西1', '外泊', D(9, 10, 0), D(11, 17, 0)),     # 両端が範囲の外
    ('t7', '(デモ) 山本 修', 'T-04', '東3', '外出', D(10, 9, 0), D(10, 10, 30)),     # 帰院予定が範囲より前
]


def add_pts(pg):
    pg.evaluate("""async(L)=>{for(const [id,name,tag,ward,kind,dep,due] of L){
        const o={id,name,pid:'P'+id,kana:'',ward,adm:'任意入院',kind,departAt:dep,dueAt:due,dueAtOriginal:due,dest:'見本の行き先',alone:true,
          selfTel:'',famName:'',famRel:'',famTel:'',clothes:'見本の服装',tagId:tag,consent:!!tag,departNurse:'見本 看護師',status:'out',createdAt:dep,hasPhoto:false,log:[]};
        await saveOuting(o);outings.push(o);}lastSig='';await tick();}""", PTS)


def geo(pg):
    """各行の軸・バー・継ぎ足し・現在線の位置（画面上の px）と、見出しの目盛り"""
    return pg.evaluate("""()=>{const R=e=>{if(!e||e.hidden||!e.offsetParent)return null;const r=e.getBoundingClientRect();return {x:r.x,w:r.width};};
      const rows=[...document.querySelectorAll('#activeList .crow.tl')].map(r=>({id:r.dataset.id,ax:R(r.querySelector('.tlaxis')),bar:R(r.querySelector('.tlbar')),
        ext:R(r.querySelector('.tlext')),now:R(r.querySelector('.tlnow')),l:r.querySelector('.tlbar .cl-l').textContent,rr:r.querySelector('.tlbar .cl-r').textContent,
        el:r.querySelector('.tlext .cl-l').textContent,
        clip:[...r.querySelectorAll('.tlbar,.tlext')].some(e=>!e.hidden&&e.textContent.trim()&&e.scrollWidth>e.clientWidth+1),
        barCls:r.querySelector('.tlbar').className,lbl:r.querySelector('.lbl').textContent,count:r.querySelector('[data-count]').textContent}));
      const h=document.querySelector('#activeList .tlhead');
      return {rows,head:h?{ax:R(h.querySelector('.tlhaxis')),now:R(h.querySelector('.tlnow')),lbl:h.querySelector('.tlnowlbl').textContent,
        ticks:[...h.querySelectorAll('.tlticks span')].map(s=>s.textContent)}:null};}""")


def near(a, b, tol=2.0):
    return abs(a - b) <= tol


def check_positions(g, now, start):
    W = 6 * H
    end = start + W
    by = {r['id']: r for r in g['rows']}
    for (id_, name, tag, ward, kind, dep, due) in PTS:
        r = by.get(id_)
        if r is None:
            continue
        ax = r['ax']; px = lambda t: ax['x'] + (t - start) / W * ax['w']
        x1, x2 = max(dep, start), min(due, end)
        if x2 > x1:
            assert r['bar'], (id_, 'バーが出ていない')
            assert near(r['bar']['x'], px(x1)), (id_, 'バーの左端', r['bar']['x'], px(x1))
            assert near(r['bar']['w'], px(x2) - px(x1)), (id_, 'バーの幅', r['bar']['w'], px(x2) - px(x1))
        else:
            assert r['bar'] is None, (id_, '範囲外のバーが出ている')
        # 範囲の外に出る部分は端で切り、切れている側に日時を文字で示す（バーに入りきる時だけ。文字が途中で切れない）
        assert r['l'] == '' or (dep < start and r['l'].startswith('◀ ')), (id_, r['l'])
        assert r['rr'] == '' or (due > end and r['rr'].endswith(' ▶')), (id_, r['rr'])
        if r['bar'] and r['bar']['w'] >= 260:
            assert (r['l'] != '') == (dep < start) and (r['rr'] != '') == (due > end), (id_, r['l'], r['rr'])
        assert not r['clip'], (id_, 'バーの中の文字が切れている')
        assert ('cut-l' in r['barCls']) == (dep < start) and ('cut-r' in r['barCls']) == (due > end), (id_, r['barCls'])
        # 予定超過：帰院予定から現在までを継ぎ足す
        if now > due:
            e1, e2 = max(due, start), min(now, end)
            assert r['ext'], (id_, '継ぎ足しがない')
            assert near(r['ext']['x'], px(e1)) and near(r['ext']['w'], px(e2) - px(e1)), (id_, '継ぎ足し', r['ext'], px(e1), px(e2) - px(e1))
            assert r['el'] == '' or (due < start and r['el'].startswith('◀ 予定 ')), (id_, r['el'])
            if r['ext']['w'] >= 120:
                assert (r['el'] != '') == (due < start), (id_, r['el'])
        else:
            assert r['ext'] is None, (id_, '超過していないのに継ぎ足しがある')
        # 現在線（各行）
        assert near(r['now']['x'] + r['now']['w'] / 2, px(now)), (id_, '現在線', r['now'], px(now))
    # 見出しの現在線と目盛り
    hx = g['head']['ax']
    assert near(g['head']['now']['x'] + g['head']['now']['w'] / 2, hx['x'] + (now - start) / W * hx['w'])
    # 全行の軸が同じ位置（見出しとも）にそろっている＝現在線が全行を貫く
    for r in g['rows']:
        assert near(r['ax']['x'], hx['x'], 1) and near(r['ax']['w'], hx['w'], 1), ('軸の位置がそろっていない', r['ax'], hx)


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1180, 'height': 820}, timezone_id='Asia/Tokyo', device_scale_factor=1)
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.clock.set_fixed_time(jst(2026, 11, 10, 14, 50))
        pg.goto(URL); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(200)
        assert pg.evaluate('settings.activeView') == 'timeline'
        add_pts(pg); pg.wait_for_timeout(300)
        pg.evaluate("document.getElementById('toast').style.display='none'")
        assert pg.get_attribute('#viewSeg [data-view=timeline]', 'aria-pressed') == 'true'

        now, start = D(10, 14, 50), D(10, 12, 0)
        g = geo(pg)
        assert len(g['rows']) == 7 and pg.locator('#activeList .card').count() == 7
        # 件数バッジ・並び順（緊急度順）は現行のまま
        assert pg.inner_text('#cntActive') == '7' and pg.inner_text('#cntAlert') == '⚠2'
        assert [r['id'] for r in g['rows']] == ['t7', 't1', 't2', 't3', 't4', 't5', 't6'], [r['id'] for r in g['rows']]
        assert [r['lbl'] for r in g['rows']] == ['帰院時刻超過', '帰院時刻超過', 'まもなく帰院時刻', '外出中', '外出中', '外出中', '外泊中']
        assert g['rows'][1]['count'] == '40分 超過' and g['rows'][2]['count'] == 'あと 10分'
        # 目盛り：現在の2時間前（正時に切り下げ）から6時間、1時間ごと
        assert g['head']['ticks'] == ['12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00'], g['head']['ticks']
        assert g['head']['lbl'] == '現在 14:50'
        check_positions(g, now, start)
        by = {r['id']: r for r in g['rows']}
        assert by['t6']['l'] == '◀ 11/9 10:00' and by['t6']['rr'] == '11/11 17:00 ▶', by['t6']
        assert near(by['t6']['bar']['x'], by['t6']['ax']['x']) and near(by['t6']['bar']['w'], by['t6']['ax']['w'])
        assert by['t7']['bar'] is None and by['t7']['el'] == '◀ 予定 10:30', by['t7']
        # 状態の文字ラベルは別に残る（色だけに頼らない）・氏名・残り時間・ボタン
        t1 = pg.locator('#activeList .crow.tl[data-id=t1]')
        assert t1.locator('.name').inner_text() == '(デモ) 佐藤 一郎'
        assert t1.locator('[data-act=return]').inner_text() == '帰院した' and t1.locator('[data-act=open]').inner_text() == '対応・詳細'
        assert pg.locator('#activeList .crow.tl[data-id=t3] .tagbadge.none').inner_text() == 'タグなし'
        assert pg.locator('#activeList .crow.tl[data-id=t4] [data-act=open]').inner_text() == '詳細'
        pg.screenshot(path=OUT + '/v200_tl_1180.png')

        # ---- 時刻を進める：範囲と位置が動く。行は作り直さない（毎秒は位置だけを動かす）
        pg.clock.set_fixed_time(jst(2026, 11, 10, 15, 40)); pg.wait_for_timeout(1400)   # t3 が超過に変わる（ここでは作り直してよい）
        if pg.locator('#gapBar').is_visible():
            pg.click('#gapOk')
        pg.evaluate("document.querySelectorAll('#activeList .crow.tl').forEach(r=>r.__keep=1)")
        check_positions(geo(pg), D(10, 15, 40), D(10, 13, 0))
        pg.clock.set_fixed_time(jst(2026, 11, 10, 16, 2)); pg.wait_for_timeout(1400)
        g2 = geo(pg)
        assert g2['head']['ticks'] == ['14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00'], g2['head']['ticks']
        assert g2['head']['lbl'] == '現在 16:02'
        check_positions(g2, D(10, 16, 2), D(10, 14, 0))
        assert pg.evaluate("[...document.querySelectorAll('#activeList .crow.tl')].every(r=>r.__keep===1)"), '時刻が進んだだけで行が作り直された'
        # 継ぎ足しが伸びている（t1：14:10 → 16:02）
        e_before = [r for r in geo(pg)['rows'] if r['id'] == 't1'][0]['ext']['w']
        pg.clock.set_fixed_time(jst(2026, 11, 10, 16, 32)); pg.wait_for_timeout(1300)
        e_after = [r for r in geo(pg)['rows'] if r['id'] == 't1'][0]['ext']['w']
        assert e_after > e_before + 10, (e_before, e_after)

        # ---- 時間軸のまま「詳細」：その行だけ現行の詳細カードになり、閉じると戻る
        pg.locator('#activeList .crow.tl[data-id=t4] [data-act=open]').click(); pg.wait_for_timeout(400)
        full = pg.locator('#activeList .card:not(.crow)')
        assert full.count() == 1 and full.first.get_attribute('data-id') == 't4'
        assert '見本の服装' in full.first.inner_text() and full.locator('[data-act=close]').count() == 1
        assert pg.locator('#activeList .crow.tl').count() == 6 and pg.locator('#activeList .tlhead').count() == 1
        pg.screenshot(path=OUT + '/v200_tl_detail.png')
        full.locator('[data-act=close]').click(); pg.wait_for_timeout(400)
        assert pg.locator('#activeList .card:not(.crow)').count() == 0 and pg.locator('#activeList .crow.tl').count() == 7

        # ---- 時間軸のまま「帰院した」
        pg.locator('#activeList .crow.tl[data-id=t5] [data-act=return]').click(); pg.wait_for_timeout(300)
        assert '伊藤 誠' in pg.inner_text('#dlgTitle'), pg.inner_text('#dlgTitle')
        pg.fill('#dlgForm input[name=nurse]', '見本 看護師'); pg.click('#dlgActions button.ok'); pg.wait_for_timeout(900)
        assert pg.evaluate("outings.find(o=>o.id==='t5').status") == 'returned'
        assert pg.locator('#activeList .crow.tl[data-id=t5]').count() == 0 and pg.inner_text('#cntActive') == '6'

        # ---- 目隠し表示：時間軸の行でも氏名が頭文字だけ
        pg.evaluate("(async()=>{settings.mask=true;await saveSettings();lastSig='';await tick();})()"); pg.wait_for_timeout(300)
        assert pg.locator('#activeList .crow.tl[data-id=t1] .name').inner_text() == '(○○○ 佐○ 一○'
        assert 'ID' not in pg.locator('#activeList .crow.tl[data-id=t1] .sub').inner_text()
        pg.evaluate("(async()=>{settings.mask=false;await saveSettings();lastSig='';await tick();})()"); pg.wait_for_timeout(300)

        # ---- 「時間軸／一覧」の切り替えと保存
        pg.click('#viewSeg [data-view=list]'); pg.wait_for_timeout(400)
        assert pg.locator('#activeList .tlhead').count() == 0 and pg.locator('#activeList .crow.tl').count() == 0
        assert pg.locator('#activeList .crow .times').count() == 6
        assert pg.evaluate("dbGet('settings','main').then(s=>s.activeView)") == 'list'
        pg.reload(); pg.wait_for_timeout(800); pg.click('#startOv'); pg.wait_for_timeout(300)
        assert pg.locator('#activeList .crow .times').count() == 6 and pg.locator('#activeList .tlhead').count() == 0
        assert pg.get_attribute('#viewSeg [data-view=list]', 'aria-pressed') == 'true'
        pg.click('#viewSeg [data-view=timeline]'); pg.wait_for_timeout(400)
        assert pg.locator('#activeList .crow.tl').count() == 6 and pg.locator('#activeList .tlhead').count() == 1
        assert pg.evaluate("dbGet('settings','main').then(s=>s.activeView)") == 'timeline'

        # ---- 3つの幅で横にはみ出さない・言葉の途中で折り返さない
        for (w, h, axis) in [(1180, 820, True), (1024, 1366, True), (390, 844, False)]:
            pg.set_viewport_size({'width': w, 'height': h}); pg.wait_for_timeout(400)
            for th in ['light', 'dark']:
                pg.evaluate(f"(async()=>{{settings.themeMode='{th}';applyTheme();}})()"); pg.wait_for_timeout(150)
                r = pg.evaluate("""()=>{const d=document.documentElement;const rows=[...document.querySelectorAll('#activeList .crow.tl')];
                  const vis=e=>!!(e&&e.offsetParent&&e.getBoundingClientRect().width>0);
                  // 1行のはずの文字（氏名・状態ラベル・残り時間・ボタン）が2行になっていない
                  const oneLine=[...document.querySelectorAll('#activeList .crow.tl .name,#activeList .crow.tl .lbl,#activeList .crow.tl .count,#activeList .crow.tl .btn,#activeList .tlticks span,#viewSeg .btn')]
                    .filter(vis).filter(e=>{const lh=parseFloat(getComputedStyle(e).lineHeight)||parseFloat(getComputedStyle(e).fontSize)*1.5;return e.getBoundingClientRect().height>lh*1.6+22;}).map(e=>e.textContent);
                  return {sw:d.scrollWidth,cw:d.clientWidth,rowsOver:rows.filter(x=>x.scrollWidth>x.clientWidth+1).length,
                    axis:rows.every(x=>vis(x.querySelector('.tlaxis'))),mini:rows.every(x=>vis(x.querySelector('.tlmini'))),head:vis(document.querySelector('.tlhead')),oneLine};}""")
                assert r['sw'] <= r['cw'], (w, th, '横にはみ出し', r)
                assert r['rowsOver'] == 0, (w, th, r)
                assert r['oneLine'] == [], (w, th, '折り返し', r['oneLine'])
                if axis:
                    assert r['axis'] and r['head'] and not r['mini'], (w, r)
                    check_positions(geo(pg), D(10, 16, 32), D(10, 14, 0))
                else:
                    assert not r['axis'] and not r['head'] and r['mini'], (w, r)
                pg.screenshot(path=f'{OUT}/v200_tl_{w}_{th}.png')
        # スマホ幅：進み具合のバー（予定超過は満タン、外出中は出発からの割合）
        mini = pg.evaluate("""()=>Object.fromEntries([...document.querySelectorAll('#activeList .crow.tl')].map(r=>[r.dataset.id,parseFloat(r.querySelector('.tlmini i').style.width)]))""")
        assert mini['t1'] == 100 and mini['t4'] == 100, mini
        assert abs(mini['t3'] - 100) < 0.01 and 0 < mini['t2'] <= 100, mini
        assert abs(mini['t6'] - (D(10, 16, 32) - D(9, 10, 0)) / (D(11, 17, 0) - D(9, 10, 0)) * 100) < 0.5, mini

        # ---- #detail で開くと、全カードが詳細表示（時間軸の行・見出しは出ない）
        pg.set_viewport_size({'width': 1180, 'height': 820})
        pg.goto(URL + '#detail'); pg.reload(); pg.wait_for_timeout(800); pg.click('#startOv'); pg.wait_for_timeout(300)
        assert pg.locator('#activeList .card').count() == 6 and pg.locator('#activeList .crow').count() == 0
        assert pg.locator('#activeList .tlhead').count() == 0
        # 印刷（写真なし一覧）は現行の体裁：全員の詳細カード、時間軸の見出しなし
        pg.goto(URL); pg.reload(); pg.wait_for_timeout(800); pg.click('#startOv'); pg.wait_for_timeout(300)
        pr = pg.evaluate("(async()=>{printFull=true;await renderActive();const r=[document.querySelectorAll('#activeList .card:not(.crow)').length,document.querySelectorAll('#activeList .tlhead').length,document.querySelectorAll('#activeList [data-act=close]').length];printFull=false;lastSig='';await tick();return r})()")
        assert pr == [6, 0, 0], pr
        assert pg.locator('#activeList .crow.tl').count() == 6
        ctx.close(); b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
