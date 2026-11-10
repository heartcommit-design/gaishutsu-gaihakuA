"""1.12.0（第2部）集計：病棟の切り替え・まとめ・時間・曜日別・時間帯別・行き先の上位5・単独／同行・患者別・印刷・CSV。
架空のデータ（2026年9月）で件数・割合・平均・患者別の数を assert で確かめる。
月をまたぐ外出（8/31出発）、予定・誤登録の取消・翌月の外出は9月に数えない。
"""
import os, csv, io, datetime
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html'

# 出発 (月,日,時,分)・帰院予定までの分・帰院までの分（None=未帰院）
ROWS = [
    # key, pid, name, ward, kind, depart, due_min, ret_min, alone, dest, tag, search, status
    ('A', 'P0001', 'テスト 太郎', '東1', '外出', (9, 7, 9, 0), 120, 120, True, '図書館', 'T-01', False, 'returned'),
    ('B', 'P0001', 'テスト 太郎', '東1', '外出', (9, 8, 10, 30), 120, 150, False, '図書館', '', False, 'returned'),
    ('C', 'P0002', 'テスト 花子', '東2', '外泊', (9, 12, 14, 0), 1440, 1530, False, '自宅', 'T-02', True, 'returned'),
    ('D', 'P0002', 'テスト 花子', '東2', '外出', (9, 20, 16, 30), 90, 60, True, '喫煙', '', False, 'returned'),
    ('E', 'P0003', 'テスト 次郎', '東1', '外出', (9, 30, 15, 0), 120, 180, True, '図書館', '', False, 'returned'),
    # 9月に数えないもの
    ('F', 'P0003', 'テスト 次郎', '東1', '外泊', (8, 31, 10, 0), 1440, 1440, True, '自宅', '', False, 'returned'),   # 月をまたぐ（8月出発）
    ('G', 'P0001', 'テスト 太郎', '東1', '外出', (9, 15, 11, 0), 120, None, True, '図書館', '', False, 'cancelled'),
    ('H', 'P0002', 'テスト 花子', '東2', '外出', (9, 25, 11, 0), 120, None, True, '図書館', '', False, 'planned'),
    ('I', 'P0001', 'テスト 太郎', '東1', '外出', (10, 1, 9, 0), 120, 300, True, '図書館', '', False, 'returned'),
]
JSDAY = lambda m, d: (datetime.date(2026, m, d).weekday() + 1) % 7   # JS の getDay（日=0）


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1180, 'height': 820}, accept_downloads=True)
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(200)
        pg.evaluate("""async(rows)=>{const M=60000;
          const pts={};for(const [pid,name,ward] of [['P0001','テスト 太郎','東1'],['P0002','テスト 花子','東2'],['P0003','テスト 次郎','東1']]){
            const x={id:uid(),pid,name,ward,adm:'任意入院',count:0,dests:[],createdAt:Date.now()};pts[pid]=x;patients.push(x);await dbPut('patients',x);}
          for(const r of rows){const [k,pid,name,ward,kind,[mo,d,h,mi],dueMin,retMin,alone,dest,tag,search,status]=r;
            const t=new Date(2026,mo-1,d,h,mi).getTime();
            const o={id:'st'+k,patientId:pts[pid].id,name,pid,ward,adm:pid==='P0002'?'医療保護入院':'任意入院',kind,departAt:t,dueAt:t+dueMin*M,dueAtOriginal:t+dueMin*M,
              returnedAt:retMin===null?undefined:t+retMin*M,dest,alone,compName:alone?'':'テスト 家族',tagId:tag,status,departNurse:'(デモ) 看護師A',hasPhoto:false,
              log:[{at:t,text:kind+'に出発',by:'(デモ) 看護師A'}].concat(search?[{at:t+60*M,text:'捜索開始（連絡：本人）',by:'(デモ) 看護師A'}]:[])};
            if(status==='cancelled')o.cancelledAt=t+10*M;outings.push(o);await saveOuting(o);}
          window.print=()=>{};}""", [list(r) for r in ROWS])
        pg.click('nav button[data-tab=stats]'); pg.wait_for_timeout(200)
        pg.evaluate("stY=2026;stM=8;stWard='';renderStats()")
        assert pg.inner_text('#stTitle') == '2026年9月の集計（全病棟）'
        assert pg.locator('#stWard [data-stw]').all_inner_texts()[:3] == ['全病棟', '東1', '東2']
        card = lambda k: pg.inner_text(f'#stCards [data-k={k}]')
        cell = lambda k: pg.inner_text(f'[data-k={k}]')

        # ---- 全病棟：A〜E の5件
        d = pg.evaluate("(()=>{const d=statsData();return {n:d.total.n,out:d.total.out,stay:d.total.stay,people:d.nPeople,late:d.total.late,rate:d.total.rate,search:d.total.search,tag:d.total.tag,avg:d.avgOut,nRet:d.nRet,lateAvg:d.lateAvg,lateMax:d.lateMax,wd:d.wd,tb:d.tb.map(x=>x.n),dests:d.dests,alone:d.alone,comp:d.comp,people2:d.people.map(r=>[r.name,r.pid,r.ward,r.out,r.stay,r.late,r.maxLate,r.search,r.last])}})()")
        assert (d['n'], d['out'], d['stay'], d['people']) == (5, 4, 1, 3), d
        assert (d['late'], d['rate'], d['search'], d['tag']) == (3, '60.0', 1, 2), d
        # 外出の平均時間：帰院済みの外出 A120・B150・D60・E180 分 → 127.5分
        assert d['nRet'] == 4 and abs(d['avg'] - 127.5 * 60000) < 1, d['avg']
        assert (d['lateAvg'], d['lateMax']) == (60, 90), d          # 遅れ B30・C90・E60
        wd = [0] * 7
        for r in ROWS[:5]:
            wd[JSDAY(r[5][0], r[5][1])] += 1
        assert d['wd'] == wd, (d['wd'], wd)
        assert d['tb'] == [1, 1, 2, 1], d['tb']                     # 9:00／10:30／14:00・15:00／16:30
        assert d['dests'][0] == ['図書館', 3] and sorted(d['dests'][1:]) == [['喫煙', 1], ['自宅', 1]], d['dests']
        assert (d['alone'], d['comp']) == (3, 2)
        ppl = {r[0]: r for r in d['people2']}
        assert [r[0] for r in d['people2']][2] == 'テスト 次郎', d['people2']   # 回数の多い順（2・2・1）
        assert ppl['テスト 太郎'][1:8] == ['P0001', '東1', 2, 0, 1, 30, 0], ppl['テスト 太郎']
        assert ppl['テスト 花子'][1:8] == ['P0002', '東2', 1, 1, 1, 90, 1], ppl['テスト 花子']
        assert ppl['テスト 次郎'][1:8] == ['P0003', '東1', 1, 0, 1, 60, 0], ppl['テスト 次郎']
        assert ppl['テスト 次郎'][8] == pg.evaluate("new Date(2026,8,30,15,0).getTime()"), '最後の外出に8月の外出が入っている'
        # 画面の表示
        assert '5件' in card('n') and '外出 4・外泊 1' in card('n')
        assert '3人' in card('people') and '3件' in card('late') and '60.0%' in card('late')
        assert '1件' in card('search') and '2件' in card('tag')
        assert cell('avgOut').startswith('2時間7分') and cell('lateAvg') == '60分' and cell('lateMax') == '90分'
        assert (cell('alone'), cell('comp')) == ('3件', '2件')
        assert pg.locator('#stPt tbody tr').count() == 3 and pg.locator('#stWardBox').is_visible()
        assert pg.locator('#stTable tbody tr.tot td').nth(3).inner_text() == '5'
        assert pg.locator('#stTable tbody tr', has_text='東2').locator('td').nth(3).inner_text() == '2'
        # 患者別の氏名 → 過去の記録
        pg.locator('#stPt [data-stpt]', has_text='テスト 花子').click(); pg.wait_for_timeout(200)
        assert 'テスト 花子 さんの過去の記録' in pg.inner_text('#dlgTitle')
        pg.click('#dlgActions button'); pg.wait_for_timeout(100)

        # ---- 病棟の切り替え：東1 は A・B・E
        pg.click('#stWard [data-stw="東1"]'); pg.wait_for_timeout(200)
        assert pg.inner_text('#stTitle') == '2026年9月の集計（東1）'
        assert '3件' in card('n') and '外出 3・外泊 0' in card('n') and '2人' in card('people')
        assert '2件' in card('late') and '66.7%' in card('late') and '0件' in card('search') and '1件' in card('tag')
        assert cell('avgOut').startswith('2時間30分') and cell('lateAvg') == '45分' and cell('lateMax') == '60分'
        assert pg.locator('#stPt tbody tr').count() == 2 and 'テスト 花子' not in pg.inner_text('#stPt')
        assert not pg.locator('#stWardBox').is_visible(), '病棟を選んだ時に病棟別の表が出ている'
        assert pg.locator('#stTable2 tbody tr.tot td').nth(3).inner_text() == '3'
        # 印刷：病棟と増やした項目
        pg.click('#stPrint'); pg.wait_for_timeout(200)
        pa = pg.inner_text('#printArea')
        for w in ['2026年9月', '東1', 'まとめ', '曜日別の出発件数', '時間帯別の出発件数', '行き先の上位5', '単独・同行', '患者別', '入院形態別', 'テスト 太郎', 'テスト 次郎']:
            assert w in pa, w
        assert 'テスト 花子' not in pa and '病棟別' not in pa
        pg.evaluate("document.body.classList.remove('pm-history')")
        # CSV：病棟と増やした項目
        with pg.expect_download() as dl:
            pg.click('#stCsv')
        assert dl.value.suggested_filename == '外出外泊集計_2026-09_東1.csv', dl.value.suggested_filename
        rows = list(csv.reader(io.StringIO(open(dl.value.path(), encoding='utf-8-sig').read())))
        flat = {r[0]: r[1:] for r in rows if r}
        assert rows[0][0] == '2026年9月の集計（東1）'
        assert flat['合計（件）'] == ['3'] and flat['出た人数（実人数）'] == ['2'] and flat['遅れの割合(%)'] == ['66.7']
        assert flat['外出の平均時間（分）'] == ['150'] and flat['遅れの平均（分）'] == ['45'] and flat['遅れの最大（分）'] == ['60']
        i = rows.index(['患者別'])
        assert rows[i + 1] == ['氏名', '患者ID', '病棟', '外出', '外泊', '遅れ', '最大の遅れ(分)', '捜索', '最後の外出']
        assert rows[i + 2][:8] == ['テスト 太郎', 'P0001', '東1', '2', '0', '1', '30', '0'], rows[i + 2]
        assert ['病棟別'] not in rows and ['入院形態別'] in rows
        j = rows.index(['時間帯別の出発件数']); assert rows[j + 2] == ['1', '1', '1', '0']
        # 全病棟の CSV には病棟別が入る
        pg.click('#stWard [data-stw=""]'); pg.wait_for_timeout(150)
        with pg.expect_download() as dl:
            pg.click('#stCsv')
        rows = list(csv.reader(io.StringIO(open(dl.value.path(), encoding='utf-8-sig').read())))
        assert ['病棟別'] in rows and dl.value.suggested_filename == '外出外泊集計_2026-09.csv'
        # ---- 8月：月をまたぐ F だけ（9月に帰院しても8月に数える）
        pg.click('#stPrev'); pg.wait_for_timeout(150)
        assert pg.evaluate("statsData().total.n") == 1 and pg.evaluate("statsData().total.stay") == 1
        # ---- 10月：I だけ（遅れ 180分）
        pg.click('#stNext'); pg.click('#stNext'); pg.wait_for_timeout(150)
        assert pg.evaluate("[statsData().total.n,statsData().lateMax]") == [1, 180]
        ctx.close(); b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
