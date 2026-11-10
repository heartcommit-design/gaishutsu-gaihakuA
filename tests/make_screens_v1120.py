"""1.12.0 の集計の画面を3つの幅で撮って docs/screens_v1.12.0/ に入れる（suite には入れない）。
デモデータ（架空）に、今月の帰院済みの外出（架空）を足して撮る。各画面で横にはみ出していないことも確かめる。
"""
import os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
DST = os.path.join(APP, 'docs', 'screens_v1.12.0'); os.makedirs(DST, exist_ok=True)
SIZES = [(1024, 1366, 'ipad_tate'), (1180, 820, 'ipad_yoko'), (390, 844, 'phone')]


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w, h, tag in SIZES:
            ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1, has_touch=True)
            pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.goto('file://' + APP + '/index.html'); pg.wait_for_timeout(700); pg.click('#startOv')
            pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(1500)
            pg.evaluate("""async()=>{let seed=7;const rnd=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;};
              const M=60000,now=new Date(),days=now.getDate(),D=['自宅','実家','図書館','喫煙','近くのコンビニ','病院周辺の散歩','加古川のイオン'];
              const ps=patients.filter(x=>x.demo).slice(4,16);
              for(let i=0;i<26;i++){const p=ps[Math.floor(rnd()*ps.length)];const day=1+Math.floor(rnd()*Math.max(1,days-1));
                const t=new Date(now.getFullYear(),now.getMonth(),day,9+Math.floor(rnd()*8),[0,15,30,45][Math.floor(rnd()*4)]).getTime();
                if(t>Date.now()-6*3600000)continue;const stay=rnd()<0.15,due=stay?1440:60*(1+Math.floor(rnd()*3)),late=rnd()<0.25?10+Math.floor(rnd()*50):-Math.floor(rnd()*20);
                const o={id:uid(),patientId:p.id,name:p.name,pid:p.pid,ward:p.ward,adm:p.adm,kind:stay?'外泊':'外出',departAt:t,dueAt:t+due*M,dueAtOriginal:t+due*M,returnedAt:t+(due+late)*M,
                  dest:D[Math.floor(rnd()*D.length)],alone:rnd()<0.6,compName:'',tagId:rnd()<0.6?'T-0'+(1+Math.floor(rnd()*5)):'',status:'returned',departNurse:'(デモ) 看護師A',hasPhoto:false,demo:true,log:[]};
                outings.push(o);await saveOuting(o);}}""")
            pg.click('nav button[data-tab=stats]'); pg.wait_for_timeout(300)

            def shot(name):
                sw = pg.evaluate('document.documentElement.scrollWidth')
                assert sw <= w, f'{name} {tag}: 横にはみ出し {sw}>{w}'
                pg.evaluate("document.getElementById('toast').style.display='none'")
                pg.screenshot(path=f'{DST}/{name}_{tag}.png')

            shot('01_shukei')
            pg.locator('#stPt').scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0,-120)"); pg.wait_for_timeout(200); shot('02_kanjabetsu')
            pg.evaluate("window.scrollTo(0,0)"); pg.click('#stWard [data-stw="東1"]'); pg.wait_for_timeout(200); shot('03_byoto_higashi1')
            ctx.close()
        b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
