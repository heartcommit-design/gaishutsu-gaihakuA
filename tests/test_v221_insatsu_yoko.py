"""2.2.1：印刷の用紙の向き。iPad の Safari は @page の「landscape」という語を無視して縦向きになるため、
用紙の寸法（A4 横＝297mm×210mm）を数値で指定する。
- 印刷用の @page が 297mm 210mm（横長）になっている／「landscape」の語だけに頼っていない
- 印刷時（emulate_media print）に、Chromium が横長のページとして PDF を作る（幅 > 高さ）
"""
import os, re, io, http.server, threading, functools
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
PORT = 8797


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    html = open(os.path.join(APP, 'index.html'), encoding='utf-8').read()
    pages = re.findall(r'@page\s*\{([^}]*)\}', html)
    assert pages, '@page がない'
    for p in pages:
        m = re.search(r'size\s*:\s*([^;]+)', p)
        assert m, p
        size = m.group(1).strip()
        assert size == '297mm 210mm', size
        assert 'landscape' not in p, p

    srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), functools.partial(Quiet, directory=APP))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    errors = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={'width': 1180, 'height': 820})
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        pg.click('#startOv')
        pdf = pg.pdf(prefer_css_page_size=True)
        box = re.search(rb'/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]', pdf)
        assert box, 'MediaBox が読めない'
        w = float(box.group(3)) - float(box.group(1)); h = float(box.group(4)) - float(box.group(2))
        print('page', w, h)
        assert w > h, (w, h)
        assert abs(w - 841.9) < 3 and abs(h - 595.3) < 3, (w, h)
        b.close()
    srv.shutdown()
    print('errors', errors)
    assert not errors, errors
    print('OK test_v221_insatsu_yoko')


if __name__ == '__main__':
    main()
