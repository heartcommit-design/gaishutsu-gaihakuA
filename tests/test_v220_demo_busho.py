"""2.2.0：デモデータに、歴史上の人物の名前を使った架空の4人（外出・外泊中、服装写真つき）を足した。
assert で確かめること：
- デモ後に4人が外出・外泊中に出る（時間軸・一覧の両方）。患者台帳にも入る
- 行き先・付き添い・続柄が詳細に出る
- 4人とも写真がある（詳細で画像が表示され、画像として読み込める）
- 4人は予定超過でない（デモ直後のアラームは既存の1人だけ）
- 「帰院した」で写真が消える
- 「デモデータを消す」で4人と写真が消える（デモで足したタグも消える）
- デモを入れ直しても重複しない
- 3つの幅・両配色で横はみ出しなし
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'
SIZES = [(1180, 820), (1024, 1366), (390, 844)]
BUSHO = [  # pid, 氏名, 種別, 行き先, 付き添い, 続柄, 服装
    ('D1051', '(デモ) 明智 光秀', '外出', '本能寺', '安田 国継', '家臣', '薄桃色の着物、赤い柄の襟'),
    ('D1052', '(デモ) 織田 信長', '外出', '比叡山延暦寺', '藤吉郎', '家臣', '緑の肩衣、白い着物'),
    ('D1053', '(デモ) 徳川 家康', '外泊', '江戸', '徳川 秀忠', '子', '黒い装束'),
    ('D1054', '(デモ) 石田 三成', '外出', '関ヶ原', '大谷 吉継', '友', '青の肩衣、緑の着物'),
]
PIDS = [x[0] for x in BUSHO]


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1180, 'height': 820}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(300)
        pg.evaluate("window.tone=function(){}")
        pg.click('nav button[data-tab=settings]')
        hint = pg.locator('#demoIn').locator('xpath=../..').inner_text()
        assert '54人' in hint and '外出・外泊中7人' in hint and '予定1件' in hint, hint
        pg.click('#demoIn'); pg.wait_for_timeout(1500)
        assert '54人・外出・外泊中7人・予定1件' in pg.inner_text('#toast'), pg.inner_text('#toast')

        # 台帳と外出・外泊中
        r = pg.evaluate("""(pids)=>pids.map(pid=>{const o=outings.find(x=>x.pid===pid);const pt=patients.find(x=>x.pid===pid);
            return {pt:!!pt&&pt.demo&&pt.ward==='東1'&&pt.sex==='男'&&!!pt.age&&pt.count===1&&pt.famName===o.compName&&pt.famRel===o.compRel,
              name:o.name,kind:o.kind,status:o.status,demo:o.demo,dest:o.dest,comp:o.compName,rel:o.compRel,alone:o.alone,clothes:o.clothes,
              tag:o.tagId,tagOk:!!o.tagId&&tags.find(t=>t.id===o.tagId).outingId===o.id,hasPhoto:o.hasPhoto,
              st:stateOf(o,Date.now()),mins:Math.round((o.dueAt-Date.now())/60000),
              log:o.log.map(l=>l.text).join('|'),nurse:o.departNurse}})""", PIDS)
        print('busho', r)
        for (pid, name, kind, dest, comp, rel, clothes), x in zip(BUSHO, r):
            assert x['pt'], (pid, '台帳')
            assert (x['name'], x['kind'], x['status'], x['demo'], x['dest'], x['comp'], x['rel'], x['alone'], x['clothes']) == \
                (name, kind, 'out', True, dest, comp, rel, False, clothes), x
            assert x['tagOk'] and x['hasPhoto'] and x['nurse'] == '(デモ) 看護師A', x
            assert x['st'] not in ('overdue', 'search'), (pid, '予定超過になっている', x)
            assert '出発（デモ）' in x['log'] and '服装写真を登録' in x['log'], x
        mins = [x['mins'] for x in r]
        assert 35 <= mins[0] <= 40 and 115 <= mins[1] <= 120 and 2 * 1440 - 5 <= mins[2] <= 2 * 1440 and 175 <= mins[3] <= 180, mins
        assert sorted(x['tag'] for x in r) == ['T-06', 'T-07', 'T-08', 'T-09']
        # 練習用に T-04・T-05 は空いている
        assert pg.evaluate("['T-04','T-05'].map(i=>tags.find(t=>t.id===i).status)") == ['available', 'available']
        # 既存のデモ3人・予定1件はそのまま。超過は既存の1人だけ
        assert pg.evaluate("outings.filter(o=>o.status==='out').length") == 7
        assert pg.evaluate("outings.filter(o=>o.status==='planned').length") == 1
        assert pg.evaluate("dbKeys('photos').then(k=>k.length)") == 4

        # 時間軸（既定）に4人が出る・超過でない
        pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(500)
        assert pg.evaluate('settings.activeView') == 'timeline'
        assert pg.locator('#activeList .card.tl').count() == 7
        assert pg.locator('#activeList .card.st-overdue').count() == 1
        for _, name, *_ in BUSHO:
            row = pg.locator('#activeList .card', has_text=name)
            assert row.count() == 1, name
            assert 'st-overdue' not in row.get_attribute('class'), name
        # 一覧表示でも出る
        pg.click('#viewSeg [data-view=list]'); pg.wait_for_timeout(400)
        for _, name, *_ in BUSHO:
            assert pg.locator('#activeList .card.crow', has_text=name).count() == 1, name
        pg.click('#viewSeg [data-view=timeline]'); pg.wait_for_timeout(400)

        # 詳細：行き先・付き添い（続柄）・服装・写真（画像として読み込める）
        for pid, name, kind, dest, comp, rel, clothes in BUSHO:
            row = pg.locator('#activeList .card', has_text=name)
            row.locator('[data-act=open]').click(); pg.wait_for_timeout(500)
            card = pg.locator('#activeList .card:not(.crow)', has_text=name)
            assert card.count() == 1, name
            t = card.inner_text()
            assert dest in t and f'{comp}（{rel}）' in t and clothes in t and kind in t, t
            img = card.locator('img.thumb')
            assert img.count() == 1, (name, '写真が出ない')
            img.scroll_into_view_if_needed(); pg.wait_for_timeout(200)
            nat = img.evaluate("e=>e.decode().then(()=>[e.naturalWidth,e.naturalHeight,e.complete])")
            assert nat[0] > 200 and nat[1] > 200 and nat[2], (name, nat)
            assert img.is_visible() and img.bounding_box()['width'] > 40, name
            # 写真を大きく開ける
            img.click(); pg.wait_for_timeout(300)
            assert pg.locator('#dlg[open] img').count() == 1, (name, '写真の拡大が開かない')
            pg.keyboard.press('Escape'); pg.wait_for_timeout(250)
            if pg.locator('#dlg[open]').count():
                pg.click('#dlgActions button >> nth=0'); pg.wait_for_timeout(250)
            card.locator('[data-act=close]').click(); pg.wait_for_timeout(300)
        # 写真のサイズ（埋め込みの JPEG：長辺480px程度・40KB以下）
        sizes = pg.evaluate("""(pids)=>Promise.all(pids.map(pid=>dbGet('photos',outings.find(o=>o.pid===pid).id).then(b=>[b.size,b.type])))""", PIDS)
        print('photo sizes', sizes)
        assert all(s <= 40 * 1024 and t == 'image/jpeg' for s, t in sizes), sizes

        # 3つの幅・両配色で横はみ出しなし（時間軸・一覧・詳細）
        for w, h in SIZES:
            pg.set_viewport_size({'width': w, 'height': h}); pg.wait_for_timeout(300)
            for th in ['light', 'dark']:
                pg.click('nav button[data-tab=settings]'); pg.click(f'#thmSeg [data-thm={th}]'); pg.wait_for_timeout(200)
                pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(300)
                for view in ['timeline', 'list', 'detail']:
                    if view == 'detail':
                        pg.evaluate("(pids)=>{for(const pid of pids)openUntil[outings.find(o=>o.pid===pid).id]=Date.now()+120000;lastSig='';tick();}", PIDS)
                    else:
                        pg.click(f'#viewSeg [data-view={view}]')
                    pg.wait_for_timeout(400)
                    sw = pg.evaluate('[document.documentElement.scrollWidth,document.documentElement.clientWidth]')
                    assert sw[0] <= sw[1], (w, th, view, '横にはみ出し', sw)
                    if view == 'detail':
                        assert pg.locator('#activeList .card:not(.crow) img.thumb').count() == 4, (w, th)
                        pg.evaluate("(pids)=>{for(const pid of pids)delete openUntil[outings.find(o=>o.pid===pid).id];lastSig='';tick();}", PIDS)
                pg.click('#viewSeg [data-view=timeline]'); pg.wait_for_timeout(200)
        pg.set_viewport_size({'width': 1180, 'height': 820})

        # 入れ直しても重複しない（入っている間は増えない）
        pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(800)
        assert pg.evaluate("[patients.length,outings.length,tags.length]") == [54, 8, 9]

        # 「帰院した」で写真が消える（光秀）
        pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(300)
        pg.locator('#activeList .card', has_text='明智 光秀').locator('[data-act=return]').click(); pg.wait_for_timeout(300)
        assert '服装写真は削除' in pg.inner_text('#dlg')
        pg.fill('#dlgForm input[name=nurse]', '看護 C'); pg.click('#dlgActions button.ok'); pg.wait_for_timeout(1200)
        o = pg.evaluate("(()=>{const o=outings.find(x=>x.pid==='D1051');return {st:o.status,hp:o.hasPhoto,del:!!o.photoDeletedAt,tag:tags.find(t=>t.id==='T-06').status}})()")
        assert o == {'st': 'returned', 'hp': False, 'del': True, 'tag': 'available'}, o
        assert not pg.evaluate("dbKeys('photos').then(k=>k.includes(outings.find(x=>x.pid==='D1051').id))")
        assert pg.evaluate("dbKeys('photos').then(k=>k.length)") == 3

        # 「デモデータを消す」で4人と写真が消える。デモで足したタグ（T-06〜T-09）も消える
        pg.click('nav button[data-tab=settings]'); pg.click('#demoOut'); pg.wait_for_timeout(1000)
        r = pg.evaluate("""({pts:patients.length,outs:outings.length,busho:patients.filter(p=>/^D105/.test(p.pid)).length,tags:tags.map(t=>t.id+':'+t.status)})""")
        assert r == {'pts': 0, 'outs': 0, 'busho': 0, 'tags': ['T-01:available', 'T-02:available', 'T-03:available', 'T-04:available', 'T-05:available']}, r
        assert pg.evaluate("dbKeys('photos').then(k=>k.length)") == 0
        assert pg.evaluate("dbAll('tags').then(l=>l.length)") == 5
        pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(300)
        assert pg.locator('#activeList .card').count() == 0

        # 消したあと入れ直すと、もとどおり（重複なし）
        pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(1500)
        r = pg.evaluate("""({pts:patients.length,pids:new Set(patients.map(p=>p.pid)).size,out:outings.filter(o=>o.status==='out').length,
            busho:outings.filter(o=>/^D105/.test(o.pid)).length,tags:tags.length})""")
        assert r == {'pts': 54, 'pids': 54, 'out': 7, 'busho': 4, 'tags': 9}, r
        assert pg.evaluate("dbKeys('photos').then(k=>k.length)") == 4

        # 再読み込みしても写真が残る（端末の中）
        pg.reload(); pg.wait_for_timeout(800); pg.click('#startOv'); pg.wait_for_timeout(800)
        assert pg.evaluate("dbKeys('photos').then(k=>k.length)") == 4
        b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
