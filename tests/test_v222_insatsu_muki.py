"""2.2.2：日別一覧・集計の印刷で、印刷の画面を開いている間に内容が入れ替わらない。
iPad では afterprint が印刷の画面を開いている間に来ることがあり、用紙の向きを変えると
日別一覧の代わりに「外出・外泊中」の一覧が印刷に出ていた。
- 「印刷」を押すと body に pm-history が付き、afterprint が来ても外れない
- 印刷時（emulate_media print）に見えるのは #printArea（日別一覧）だけ
- 画面に触れる（pointerdown）と外れる／「一覧を印刷」を始めた時も外れる
"""
import os, http.server, threading, functools
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
PORT = 8798


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def has(pg):
    return pg.evaluate("document.body.classList.contains('pm-history')")


def main():
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), functools.partial(Quiet, directory=APP))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    errors = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={'width': 1180, 'height': 820})
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.add_init_script("window.__prints=0;window.print=()=>{window.__prints++;};")
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.click('#startOv')
        pg.click('nav button[data-tab="settings"]')
        pg.click('#demoIn')
        pg.wait_for_timeout(600)
        for sel, tab in (('#hPrint', 'history'), ('#stPrint', 'stats')):
            pg.click(f'nav button[data-tab="{tab}"]')
            pg.wait_for_timeout(300)
            pg.click(sel)
            pg.wait_for_timeout(200)
            assert pg.evaluate('window.__prints') >= 1
            assert has(pg), sel
            # iPad のように、印刷の画面を開いている間に afterprint が来ても外れない
            pg.evaluate("window.dispatchEvent(new Event('afterprint'))")
            pg.wait_for_timeout(1200)
            assert has(pg), sel + ' afterprint で外れた'
            # 印刷時に見えるのは #printArea だけ（外出・外泊中の一覧は出ない）
            pg.emulate_media(media='print')
            vis = pg.evaluate("""[...document.body.children].filter(e=>getComputedStyle(e).display!=='none').map(e=>e.id||e.tagName)""")
            assert vis == ['printArea'], vis
            assert pg.evaluate("document.querySelector('#printArea table')!==null")
            pg.emulate_media(media='screen')
            # 画面に触れたら外れる
            pg.mouse.click(600, 400)
            pg.wait_for_timeout(100)
            assert not has(pg), sel + ' 触れても外れない'
        # 日別一覧の印刷のあと、触れずに「一覧を印刷」を始めても外れる
        pg.click('nav button[data-tab="history"]'); pg.wait_for_timeout(300)
        pg.click('#hPrint'); pg.wait_for_timeout(100)
        assert has(pg)
        pg.evaluate("document.querySelector('#printBtn').click()")
        pg.wait_for_timeout(500)
        assert not has(pg)
        b.close()
    srv.shutdown()
    print('errors', errors)
    assert not errors, errors
    print('OK test_v222_insatsu_muki')


if __name__ == '__main__':
    main()
