"""2.0.0（新版：ガラス調・時間軸）：現行と同じドメインに置かれても、データ（IndexedDB）とキャッシュ（Cache Storage）が混ざらないこと。
- DB 名は gaishutsu_kanri_shisaku。現行の gaishutsu_kanri を作らない・読まない・書かない
- sw.js は自分の古いキャッシュ（gaishutsu-shisaku-…）だけを消し、現行の gaishutsu-v… は消さない
- 版（index.html と sw.js）がそろっている／manifest の名前は現行と同じ（外出・外泊管理／外出管理）
- 2.0.1：利用者に見える所（画面・title・manifest・バックアップのファイル名）に「試作」が出ない
- 現行のバックアップを読み込める。書き出すファイル名は現行と同じ形（外出管理バックアップ_日付.json）
"""
import os, re, json, http.server, threading, functools
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
PORT = 8791


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    html = open(os.path.join(APP, 'index.html'), encoding='utf-8').read()
    sw = open(os.path.join(APP, 'sw.js'), encoding='utf-8').read()
    man = json.load(open(os.path.join(APP, 'manifest.webmanifest'), encoding='utf-8'))
    v = re.search(r"APP_VERSION='([\d.]+)'", html).group(1)
    assert v == '2.1.0', v
    assert re.search(r"const CACHE = '([^']+)'", sw).group(1) == f'gaishutsu-shisaku-v{v}'
    assert "const DB_NAME='gaishutsu_kanri_shisaku'" in html
    assert "indexedDB.open('gaishutsu_kanri'" not in html, '現行の DB 名で開いている'
    # 新版は localStorage/sessionStorage のキーを必ず shisaku 付きにする（現行と混ざらない）
    for k in re.findall(r"(?:localStorage|sessionStorage)\.(?:getItem|setItem|removeItem)\('([^']+)'", html):
        assert 'shisaku' in k, k
    assert man['name'] == '外出・外泊管理' and man['short_name'] == '外出管理', man
    assert '試作' not in json.dumps(man, ensure_ascii=False), man
    # index.html（画面・ダイアログ・印刷・通知・title・aria-label を含む）と sw.js には「試作」の文字を置かない
    assert '試作' not in html and '試作' not in sw
    assert '<title>外出・外泊管理</title>' in html and 'content="外出管理"' in html
    print('version', v)

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), functools.partial(Quiet, directory=APP))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f'http://localhost:{PORT}/'
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1180, 'height': 820}, service_workers='allow', accept_downloads=True)
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        # 同じオリジンに、現行の版のキャッシュ・DB（見本の記録1件）と、新版の古いキャッシュがすでにある状態を作る
        pg.goto(base + 'manifest.webmanifest')
        pg.evaluate("""async()=>{
          await (await caches.open('gaishutsu-v1.12.0')).put('/genkou', new Response('genkou'));
          await (await caches.open('gaishutsu-shisaku-v1.0.0')).put('/old', new Response('old'));
          await new Promise((res,rej)=>{const r=indexedDB.open('gaishutsu_kanri',2);
            r.onupgradeneeded=()=>{const d=r.result;['outings','tags','patients'].forEach(n=>d.createObjectStore(n,{keyPath:'id'}));['photos','settings'].forEach(n=>d.createObjectStore(n));};
            r.onsuccess=()=>{const d=r.result;const t=d.transaction('outings','readwrite');
              t.objectStore('outings').put({id:'genkou1',name:'見本 現行',status:'out',kind:'外出',departAt:Date.now()-3600000,dueAt:Date.now()+3600000,dueAtOriginal:Date.now()+3600000,log:[]});
              t.oncomplete=()=>{d.close();res();};};r.onerror=()=>rej(r.error);});}""")

        pg.goto(base); pg.wait_for_timeout(600)
        pg.evaluate("navigator.serviceWorker.ready.then(()=>true)")
        pg.reload(); pg.wait_for_timeout(900)
        assert pg.evaluate('!!navigator.serviceWorker.controller'), 'SW が動いていない'
        keys = pg.evaluate('caches.keys()')
        print('caches', keys)
        assert 'gaishutsu-v1.12.0' in keys, '現行のキャッシュが消された'
        assert 'gaishutsu-shisaku-v2.1.0' in keys
        assert 'gaishutsu-shisaku-v1.0.0' not in keys, '新版の古いキャッシュが残っている'
        assert pg.evaluate("caches.open('gaishutsu-v1.12.0').then(c=>c.match('/genkou')).then(r=>r&&r.text())") == 'genkou'

        pg.click('#startOv'); pg.wait_for_timeout(300)
        # 画面に「試作」が出ない（ヘッダー・開始画面・下の帯・title）
        assert '外出・外泊管理' in pg.inner_text('header') and '試作' not in pg.inner_text('header'), pg.inner_text('header')
        assert '試作' not in pg.inner_text('body'), '画面に「試作」が出ている'
        assert '試作' not in pg.evaluate('document.title'), pg.evaluate('document.title')
        # 現行の記録は読まない
        assert pg.evaluate('outings.length') == 0
        assert pg.locator('#activeList .card').count() == 0
        # 新版の DB に書く
        pg.click('nav button[data-tab=settings]'); pg.click('#demoIn'); pg.wait_for_timeout(1500)
        assert pg.evaluate('outings.length') == 4
        names = pg.evaluate("indexedDB.databases().then(l=>l.map(x=>x.name).sort())")
        print('dbs', names)
        assert 'gaishutsu_kanri_shisaku' in names
        n_shisaku = pg.evaluate("""new Promise(res=>{const r=indexedDB.open('gaishutsu_kanri_shisaku');r.onsuccess=()=>{const d=r.result;
            const q=d.transaction('outings').objectStore('outings').count();q.onsuccess=()=>{d.close();res(q.result);};};})""")
        assert n_shisaku == 4, n_shisaku
        # 現行の DB は手つかず（見本の1件だけ）
        n_genkou = pg.evaluate("""new Promise(res=>{const r=indexedDB.open('gaishutsu_kanri');r.onsuccess=()=>{const d=r.result;
            const q=d.transaction('outings').objectStore('outings').getAll();q.onsuccess=()=>{d.close();res(q.result.map(x=>x.id));};};})""")
        assert n_genkou == ['genkou1'], n_genkou

        # このアプリについて：版は出るが「試作」は出ない
        pg.click('nav button[data-tab=settings]'); pg.wait_for_timeout(200)
        about = pg.inner_text('#aboutPanel')
        assert '試作' not in about and v in about and '外出・外泊管理' in about, about

        # バックアップ：書き出すファイル名は現行と同じ形（「試作」なし）、中身も現行と同じ形（app=gaishutsu_kanri）
        with pg.expect_download() as dl:
            pg.click('#bkOut')
        fn = dl.value.suggested_filename
        assert re.fullmatch(r'外出管理バックアップ_\d{4}-\d{2}-\d{2}\.json', fn) and '試作' not in fn, fn
        data = json.load(open(dl.value.path(), encoding='utf-8'))
        assert data['app'] == 'gaishutsu_kanri' and data['variant'] == 'shisaku' and len(data['outings']) == 4

        # 現行の形のバックアップ（variant なし）を読み込める
        fp = os.path.join(OUT, 'v200_genkou_backup.json')
        json.dump({'app': 'gaishutsu_kanri', 'version': 1, 'exportedAt': 0, 'settings': {'nurses': ['見本 看護師']}, 'tags': [{'id': 'T-09', 'status': 'available'}],
                   'patients': [], 'outings': [{'id': 'bk1', 'name': '見本 復元', 'status': 'returned', 'kind': '外出', 'departAt': 0, 'dueAt': 1, 'dueAtOriginal': 1, 'returnedAt': 1, 'log': []}]},
                  open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
        pg.set_input_files('#bkIn', fp); pg.wait_for_timeout(300); pg.click('#cdlgYes'); pg.wait_for_timeout(900)
        assert '復元しました' in pg.inner_text('#toast')
        assert pg.evaluate("[outings.map(o=>o.id),tags.map(t=>t.id),settings.nurses]") == [['bk1'], ['T-09'], ['見本 看護師']]
        # 復元しても現行の DB は変わらない
        n_genkou = pg.evaluate("""new Promise(res=>{const r=indexedDB.open('gaishutsu_kanri');r.onsuccess=()=>{const d=r.result;
            const q=d.transaction('outings').objectStore('outings').count();q.onsuccess=()=>{d.close();res(q.result);};};})""")
        assert n_genkou == 1
        ctx.close(); b.close()
    srv.shutdown()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
