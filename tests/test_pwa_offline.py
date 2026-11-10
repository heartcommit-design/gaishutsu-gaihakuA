import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio, http.server, threading, functools
from playwright.async_api import async_playwright
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=APP)
class Q(http.server.ThreadingHTTPServer): pass
srv=Q(('127.0.0.1',8790),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':1024,'height':1366},service_workers='allow')
        pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('http://localhost:8790/'); await pg.wait_for_timeout(500)
        await pg.evaluate("navigator.serviceWorker.ready.then(()=>true)")
        await pg.reload(); await pg.wait_for_timeout(800)
        print('SW controlling:', await pg.evaluate("!!navigator.serviceWorker.controller"))
        await pg.click('#startOv')
        # 記録を1件登録
        await pg.click('nav button[data-tab=new]')
        await pg.fill('input[name=name]','見本 太郎'); await pg.fill('input[name=pid]','Z001'); await pg.click('#wardRadios label:has-text("東1")')
        await pg.click('#dueQuick button[data-h="2"]'); await pg.fill('input[name=departNurse]','看護 A子'); await pg.click('#submitBtn'); await pg.wait_for_timeout(800)
        print('cards online:', await pg.locator('#activeList .card').count())
        # ネットを切る（サーバー停止＋オフライン）
        srv.shutdown(); await ctx.set_offline(True)
        pg2=await ctx.new_page(); pg2.on('pageerror',lambda e:errs.append(str(e)))
        await pg2.goto('http://localhost:8790/'); await pg2.wait_for_timeout(1000)
        print('offline title:', await pg2.title())
        await pg2.click('#startOv'); await pg2.wait_for_timeout(800)
        print('cards offline (data kept):', await pg2.locator('#activeList .card').count())
        print('icon offline:', await pg2.evaluate("fetch('icon-192.png').then(r=>r.status).catch(e=>'ERR')"))
        await pg2.click('nav button[data-tab=settings]'); await pg2.wait_for_timeout(300)
        print('swInfo:', await pg2.inner_text('#swInfo'))
        print('errors',errs); await b.close()
asyncio.run(main())
