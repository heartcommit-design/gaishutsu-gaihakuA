"""1.11.0 で変えた画面を3つの幅で撮って docs/screens_v1.11.0/ に入れる（suite には入れない。画面を確かめる時に手で動かす）。
データはデモデータ（架空）だけ。各画面で横にはみ出していないことも確かめる。
"""
import os, struct, zlib
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
DST = os.path.join(APP, 'docs', 'screens_v1.11.0'); os.makedirs(DST, exist_ok=True)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
SIZES = [(1024, 1366, 'ipad_tate'), (1180, 820, 'ipad_yoko'), (390, 844, 'phone')]
NURSES = [f'(デモ) 看護 {chr(0x3042 + i * 2)}子' for i in range(20)]


def png(path, w=60, h=80):
    raw = b''.join(b'\x00' + b'\x50\x60\x80' * w for _ in range(h))
    ch = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))


def main():
    png(OUT + '/shot_p.png')
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w, h, tag in SIZES:
            ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1, has_touch=True)
            pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.goto('file://' + APP + '/index.html'); pg.wait_for_timeout(700); pg.click('#startOv')
            pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(1500)
            pg.evaluate("""async(ns)=>{settings.nurses=ns;await saveSettings();renderNurseList();attachNurseChips(nf);
              const d=patients.filter(x=>x.demo);d[5].status='discharged';d[5].dischargedAt=toDateInput(Date.now()-5*86400000);d[5].ledger=[{at:Date.now()-5*86400000,text:'退院（退院日 '+ymd(d[5].dischargedAt)+'・東1）',by:ns[1]}];
              d[0].ledger=[{at:Date.now()-2*86400000,text:'修正：病棟 東2 → 東1',by:ns[0]}];
              for(const x of [d[0],d[5]])await dbPut('patients',x);}""", NURSES)

            def shot(name):
                sw = pg.evaluate('document.documentElement.scrollWidth')
                assert sw <= w, f'{name} {tag}: 横にはみ出し {sw}>{w}'
                pg.evaluate("document.getElementById('toast').style.display='none'")
                pg.screenshot(path=f'{DST}/{name}_{tag}.png')

            def close():
                pg.evaluate("document.getElementById('dlg').close()"); pg.wait_for_timeout(100)

            # 患者台帳（入院中）
            pg.click('nav button[data-tab=patients]'); pg.wait_for_timeout(300); shot('01_daicho')
            row = pg.locator('#ptTable tbody tr').nth(1)
            # 修正
            pg.locator('#ptTable tbody tr').first.locator('[data-ptedit]').click(); pg.wait_for_timeout(300); shot('02_shusei'); close()
            # 退院
            row.locator('[data-ptdis]').click(); pg.wait_for_timeout(300); shot('03_taiin'); close()
            # 同意の撤回
            pg.locator('#ptTable [data-ptwd]').first.click(); pg.wait_for_timeout(300); shot('04_tekkai'); close()
            # 退院の一覧・再入院
            pg.click('#ptSeg [data-pts=discharged]'); pg.wait_for_timeout(200); shot('05_taiin_ichiran')
            pg.locator('#ptTable [data-ptre]').first.click(); pg.wait_for_timeout(300); shot('06_sainyuin'); close()
            # 出発（GO）
            pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(300)
            pg.locator('#planList [data-pact=go]').first.click(); pg.wait_for_timeout(300)
            pg.set_input_files('#goPhotoInput', OUT + '/shot_p.png'); pg.wait_for_timeout(400); shot('07_go'); close()
            # 新規登録の服装欄（前回の記入）と看護師名
            pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(300)
            pg.locator('#pChips [data-pt]').first.click(); pg.wait_for_timeout(300)
            pg.locator('#fsClothes').scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0,-90)"); pg.wait_for_timeout(200); shot('08_fukuso')
            pg.locator('input[name=departNurse] + .nchips [data-nmore]').click(); pg.wait_for_timeout(200)
            pg.locator('#submitBtn').scroll_into_view_if_needed(); pg.wait_for_timeout(200); shot('09_kangoshi')
            # 予定の「内容を確認・変更して出発」の下（変更せずに戻る）
            pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(300)
            pg.locator('#planList [data-pact=edit]').first.click(); pg.wait_for_timeout(500)
            pg.locator('#submitBtn').scroll_into_view_if_needed(); pg.wait_for_timeout(200); shot('10_modoru')
            # 設定：看護師名
            pg.click('nav button[data-tab=settings]'); pg.wait_for_timeout(300)
            pg.locator('#nurseBulk').scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0,150)"); pg.wait_for_timeout(200); shot('11_settei_kangoshi')
            ctx.close()
        b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
