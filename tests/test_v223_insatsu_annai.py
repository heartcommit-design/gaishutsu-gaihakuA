"""2.2.3：日別一覧と集計の「印刷」ボタンの下に、用紙の向きの案内を出す。
iPad の Safari はアプリ側から印刷の初期の向きを決められない（実機 iPadOS 26.5.2 で確認）ため。
- 両方のタブに案内の文が見えている／3つの幅・両配色で横はみ出しなし・言葉が切れずに収まる
- 印刷時（pm-history）には案内は出ない
"""
import os, http.server, threading, functools
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
PORT = 8799
TEXT = '印刷の画面で「方向」が縦向きになっている時は、横向きに切り替えてください。'


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), functools.partial(Quiet, directory=APP))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    errors = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for name, w, h in (('yoko', 1180, 820), ('tate', 1024, 1366), ('phone', 390, 844)):
            pg = b.new_page(viewport={'width': w, 'height': h})
            pg.on('pageerror', lambda e: errors.append(str(e)))
            pg.add_init_script("window.print=()=>{};")
            pg.goto(f'http://127.0.0.1:{PORT}/index.html')
            pg.click('#startOv')
            for theme in ('light', 'dark'):
                pg.evaluate("t=>document.documentElement.setAttribute('data-theme',t)", theme)
                for tab in ('history', 'stats'):
                    pg.evaluate("t=>document.querySelector(`nav button[data-tab=\"${t}\"]`).click()", tab)
                    pg.wait_for_timeout(250)
                    loc = pg.locator(f'#tab-{tab} .printHint') if pg.locator(f'#tab-{tab}').count() else pg.locator('.printHint:visible')
                    vis = pg.locator('.printHint:visible')
                    assert vis.count() == 1, (name, theme, tab, vis.count())
                    assert vis.first.inner_text().strip() == TEXT
                    box = vis.first.bounding_box()
                    assert box['x'] >= 0 and box['x'] + box['width'] <= w + 1, (name, box)
                    sw_, cw = pg.evaluate('[document.documentElement.scrollWidth,document.documentElement.clientWidth]')
                    assert sw_ <= cw + 1, (name, theme, tab, sw_, cw)
                    if theme == 'light':
                        pg.screenshot(path=os.path.join(OUT, f'v223_{tab}_{name}.png'))
            # 印刷時には出ない
            pg.evaluate("document.querySelector('nav button[data-tab=\"history\"]').click()")
            pg.wait_for_timeout(200)
            pg.click('#hPrint')
            pg.emulate_media(media='print')
            assert pg.locator('.printHint:visible').count() == 0
            pg.emulate_media(media='screen')
            pg.close()
        b.close()
    srv.shutdown()
    print('errors', errors)
    assert not errors, errors
    print('OK test_v223_insatsu_annai')


if __name__ == '__main__':
    main()
