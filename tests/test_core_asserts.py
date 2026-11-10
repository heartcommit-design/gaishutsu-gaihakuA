"""中心となる動きを assert で確かめるテスト（失敗すると不合格になる）。
ほかの test_*.py の多くは結果を表示するだけで、JSエラーが出ないことしか自動判定していない。
大事な動きはここに assert で足していくこと。
"""
import os, re, struct, zlib
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html#detail'

def png(path, w=60, h=80):
    raw = b''.join(b'\x00' + b'\x80\x20\x20' * w for _ in range(h))
    ch = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))

def main():
    # 版の番号が index.html と sw.js でそろっている
    html = open(os.path.join(APP, 'index.html'), encoding='utf-8').read()
    sw = open(os.path.join(APP, 'sw.js'), encoding='utf-8').read()
    v = re.search(r"APP_VERSION='([\d.]+)'", html).group(1)
    # 2.0.0（新版）：キャッシュ名は gaishutsu-shisaku-v版（現行の gaishutsu-v版 と分ける）
    assert f"CACHE = 'gaishutsu-shisaku-v{v}'" in sw, f'sw.js のキャッシュ名が版 {v} とそろっていない'
    print('version', v)

    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 820, 'height': 1180}, has_touch=True)
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(800); pg.click('#startOv'); pg.wait_for_timeout(300)

        # デモデータ：東1の54人（2.2.0で歴史上の人物の名前の4人を追加）、外出・外泊中7人、予定1件、超過1人でアラーム帯
        pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(1500)
        r = pg.evaluate("""({pts:patients.length,e1:patients.filter(x=>x.ward==='東1'&&x.demo).length,
            out:outings.filter(o=>o.status==='out').length,plan:outings.filter(o=>o.status==='planned').length,
            names:new Set(patients.map(x=>x.name)).size,fake:patients.every(x=>x.name.startsWith('(デモ) '))})""")
        assert r == {'pts': 54, 'e1': 54, 'out': 7, 'plan': 1, 'names': 54, 'fake': True}, r
        assert pg.locator('.card.st-overdue').count() == 1
        assert pg.locator('#banner.on').count() == 1
        # 2回押しても増えない
        pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(600)
        assert pg.evaluate('patients.length') == 54

        # 新規登録（写真つき）→ 外出中に1枚増える
        pg.click('nav button[data-tab=new]')
        pg.fill('input[name=name]', 'テスト 太郎'); pg.fill('input[name=pid]', 'P0001')
        pg.click('#wardRadios label:has-text("東1")')
        pg.click('#dueQuick button[data-h="2"]')
        pg.select_option('#tagSelect', 'T-05'); pg.check('input[name=consent]')
        pg.fill('input[name=departNurse]', '看護師B')
        png(OUT + '/p.png'); pg.set_input_files('#photoInput', OUT + '/p.png'); pg.wait_for_timeout(600)
        pg.click('#submitBtn'); pg.wait_for_timeout(1200)
        assert pg.evaluate("outings.filter(o=>o.status==='out').length") == 8
        assert pg.evaluate("tags.find(t=>t.id==='T-05').status") == 'inuse'
        assert pg.evaluate("dbKeys('photos').then(k=>k.length)") == 5  # デモ4人の写真＋新規1枚
        assert pg.evaluate("dbKeys('photos').then(k=>k.includes(outings.find(o=>o.pid==='P0001').id))")

        # 帰院 → 写真が消え、タグが空く
        card = pg.locator('.card', has_text='テスト 太郎')
        card.locator('[data-act=return]').click()
        pg.fill('#dlgForm input[name=nurse]', '看護師C'); pg.click('#dlgActions button.ok'); pg.wait_for_timeout(1200)
        assert not pg.evaluate("dbKeys('photos').then(k=>k.includes(outings.find(o=>o.pid==='P0001').id))"), '帰院後も写真が残っている'
        assert pg.evaluate("dbKeys('photos').then(k=>k.length)") == 4, '外出中のデモ4人の写真まで消えた'
        assert pg.evaluate("tags.find(t=>t.id==='T-05').status") == 'available'
        assert pg.evaluate("outings.find(o=>o.pid==='P0001').status") == 'returned'

        # 再読み込みしても残る（データはこの端末の中）
        pg.reload(); pg.wait_for_timeout(800); pg.click('#startOv'); pg.wait_for_timeout(800)
        assert pg.evaluate('[patients.length,outings.length]') == [55, 9]

        # デモデータを消すと、デモ分だけ消える
        pg.click('nav button[data-tab=settings]'); pg.click('#demoOut'); pg.wait_for_timeout(1000)
        assert pg.evaluate('[patients.length,outings.length]') == [1, 1]
        assert pg.evaluate("dbKeys('photos').then(k=>k.length)") == 0
        b.close()
    print('errors', errs)
    assert not errs

if __name__ == '__main__':
    main()
