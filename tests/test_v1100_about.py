"""1.10.0：設定に「このアプリについて」（作成者・版）を表示する。"""
import os
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
errs = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in [(1024, 1366), (1180, 820), (390, 844)]:
        pg = b.new_page(viewport={'width': w, 'height': h})
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('file://' + APP + '/index.html'); pg.wait_for_timeout(700); pg.click('#startOv')
        pg.click('nav button[data-tab=settings]'); pg.wait_for_timeout(300)
        ver = pg.evaluate('APP_VERSION')
        panel = pg.locator('#aboutPanel')
        assert panel.is_visible()
        t = panel.inner_text()
        assert 'このアプリについて' in t and '黒田 優' in t and ver in t, t
        assert 'ハートコミット' not in pg.content()
        assert '黒田 優' in pg.locator('.foot').inner_text()
        assert pg.evaluate('document.documentElement.scrollWidth') <= w, 'はみ出し'
        panel.scroll_into_view_if_needed(); panel.screenshot(path=f'{OUT}/about_{w}.png')
        pg.close()
    b.close()
print('errors', errs)
assert not errs
