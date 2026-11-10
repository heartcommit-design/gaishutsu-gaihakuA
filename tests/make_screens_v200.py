"""2.0.0（新版）の画面写真を docs/screens_v2.0.0/ に撮る（suite には入れない）。
全タブ × 2配色（明るい／暗い）× 3つの幅（iPad 横 1180×820・iPad 縦 1024×1366・スマホ 390×844、1倍）。
開始画面・アラームが出ている状態・詳細を開いた状態・設定の「画面の明るさ」・帰院のダイアログも撮る。
時計を 2026/11/10 14:32（日本時間）に固定し、デモデータ（架空）に架空の外出を足して撮る。各画面で横にはみ出していないことも確かめる。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst, ms
try:
    from PIL import Image
except ImportError:
    Image = None

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
DST = os.path.join(APP, 'docs', 'screens_v2.0.0'); os.makedirs(DST, exist_ok=True)
SIZES = [(1180, 820, 'ipad_yoko'), (1024, 1366, 'ipad_tate'), (390, 844, 'phone')]
D = lambda d, h, mi=0: ms(2026, 11, d, h, mi)
EXTRA = [  # 架空（docs の見本と同じ並び）
    ('x3', '(デモ) 渡辺 久美子', '', '本3', '外出', D(10, 13, 45), D(10, 15, 30)),
    ('x4', '(デモ) 高橋 健', 'T-03', '東2', '外出', D(10, 13, 30), D(10, 16, 0)),
    ('x5', '(デモ) 伊藤 誠', '', '東1', '外出', D(10, 14, 0), D(10, 17, 0)),
    ('x6', '(デモ) 田中 美咲', '', '西1', '外泊', D(9, 10, 0), D(11, 17, 0)),
]


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w, h, tag in SIZES:
            ctx = b.new_context(viewport={'width': w, 'height': h}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
            pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.clock.set_fixed_time(jst(2026, 11, 10, 14, 32))
            pg.goto('file://' + APP + '/index.html'); pg.wait_for_timeout(700)

            def shot(name, th):
                sw = pg.evaluate('document.documentElement.scrollWidth')
                assert sw <= w, f'{name} {th} {tag}: 横にはみ出し {sw}>{w}'
                pg.evaluate("document.getElementById('toast').style.display='none'")
                pg.wait_for_timeout(120)
                fp = f'{DST}/{name}_{th}_{tag}.png'
                pg.screenshot(path=fp, animations='disabled')
                if Image:  # 公開リポジトリを重くしないよう、256色に減らして保存（PIL があるときだけ）
                    Image.open(fp).convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(fp, optimize=True)

            for th in ['light', 'dark']:
                pg.evaluate(f"settings.themeMode='{th}';applyTheme()"); pg.wait_for_timeout(200)
                assert pg.evaluate('document.documentElement.dataset.theme') == th
                shot('00_kaishi', th)
            pg.click('#startOv'); pg.wait_for_timeout(200)
            pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(1500)
            pg.evaluate("""async(L)=>{for(const [id,name,tg,ward,kind,dep,due] of L){
                const o={id,name,pid:'',ward,adm:'任意入院',kind,departAt:dep,dueAt:due,dueAtOriginal:due,dest:'見本の行き先',alone:true,selfTel:'',famName:'',famRel:'',famTel:'',
                  clothes:'見本の服装',tagId:tg,consent:!!tg,departNurse:'(デモ) 看護師A',status:'out',createdAt:dep,hasPhoto:false,demo:true,log:[]};
                await saveOuting(o);outings.push(o);}
              let seed=7;const rnd=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;};
              const M=60000,D=['自宅','実家','図書館','喫煙','近くのコンビニ','病院周辺の散歩'];const ps=patients.filter(x=>x.demo).slice(4,16);
              for(let i=0;i<22;i++){const p=ps[Math.floor(rnd()*ps.length)];const day=1+Math.floor(rnd()*9);
                const t=new Date(2026,10,day,9+Math.floor(rnd()*8),[0,15,30,45][Math.floor(rnd()*4)]).getTime();const stay=rnd()<0.15,due=stay?1440:60*(1+Math.floor(rnd()*3)),late=rnd()<0.25?10+Math.floor(rnd()*50):-Math.floor(rnd()*20);
                const o={id:uid(),patientId:p.id,name:p.name,pid:p.pid,ward:p.ward,adm:p.adm,kind:stay?'外泊':'外出',departAt:t,dueAt:t+due*M,dueAtOriginal:t+due*M,returnedAt:t+(due+late)*M,
                  dest:D[Math.floor(rnd()*D.length)],alone:rnd()<0.6,compName:'',tagId:'',status:'returned',departNurse:'(デモ) 看護師A',hasPhoto:false,demo:true,log:[]};
                outings.push(o);await saveOuting(o);}
              lastSig='';await tick();}""", EXTRA)
            pg.wait_for_timeout(400)
            if pg.locator('#prBar').is_visible():
                pg.click('#prLater')

            for th in ['light', 'dark']:
                pg.click('nav button[data-tab=settings]'); pg.click(f'#thmSeg [data-thm={th}]'); pg.wait_for_timeout(200)
                pg.click('nav button[data-tab=active]'); pg.click('#viewSeg [data-view=timeline]'); pg.wait_for_timeout(300)
                shot('01_gaishutsu_jikanjiku', th)
                pg.click('#viewSeg [data-view=list]'); pg.wait_for_timeout(300)
                shot('02_gaishutsu_ichiran', th)
                pg.click('#viewSeg [data-view=timeline]'); pg.wait_for_timeout(300)
                pg.locator('#activeList .card.st-overdue [data-act=open]').first.click(); pg.wait_for_timeout(400)
                pg.locator('#activeList .card.st-overdue:not(.crow)').first.scroll_into_view_if_needed()
                shot('03_shosai', th)
                pg.locator('#activeList [data-act=close]').first.click(); pg.wait_for_timeout(300)
                pg.locator('#activeList .crow [data-act=return]').nth(1).click(); pg.wait_for_timeout(300)
                shot('04_dialog_kiin', th)
                pg.click('#dlgActions button >> nth=0'); pg.wait_for_timeout(200)
                for i, t in [(5, 'yotei:plan'), (6, 'shinki:new'), (7, 'calendar:calendar'), (8, 'nichibetsu:history'), (9, 'shukei:stats'),
                             (10, 'daicho:patients'), (11, 'tag:tags'), (12, 'settei:settings')]:
                    nm, tb = t.split(':')
                    pg.click(f'nav button[data-tab={tb}]'); pg.wait_for_timeout(300)
                    if tb == 'calendar':
                        pg.locator('#calGrid .cday.today').click(); pg.wait_for_timeout(200)
                    shot(f'{i:02d}_{nm}', th)
            ctx.close()
        b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
