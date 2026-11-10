import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1024,'height':1366},has_touch=True)
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('file://'+APP+'/index.html#detail'); await pg.wait_for_timeout(500); await pg.click('#startOv')
        await pg.click('nav button[data-tab=settings]'); await pg.click('#demoIn'); await pg.wait_for_timeout(1500)
        await pg.click('nav button[data-tab=plan]'); await pg.wait_for_timeout(300)
        await pg.locator('#planList [data-pact=go]').click(); await pg.wait_for_timeout(300); await pg.select_option('#goTag',index=1); await pg.fill('#dlgBody input[name=nurse]','看護 C'); await pg.click('#dlgActions button.ok'); await pg.wait_for_timeout(1500)
        c=pg.locator('#activeList .card',has_text=await pg.evaluate("outings.find(o=>o.pid==='D1004').name")); print('undo btn on card:', await c.locator('[data-act=undo]').count(), '| others:', await pg.locator('#activeList [data-act=undo]').count())
        await c.locator('[data-act=undo]').click(); await pg.wait_for_timeout(300); await pg.screenshot(path='undo3.png')
        await pg.fill('#dlgBody input[name=reason]','GOを押し間違えた'); await pg.fill('#dlgBody input[name=staff]','看護 C'); await pg.click('#dlgActions button.pri'); await pg.wait_for_timeout(800)
        o=await pg.evaluate("outings.find(o=>o.pid==='D1004')"); print('after undo:', o['status'], o['tagId'], await pg.evaluate(f"tags.find(t=>t.id==='{o['tagId']}').status"))
        await pg.locator('#planList [data-pact=go]').click(); await pg.wait_for_timeout(300); await pg.fill('#dlgBody input[name=nurse]','看護 C'); await pg.click('#dlgActions button.ok'); await pg.wait_for_timeout(1200)
        await pg.locator('#activeList .card',has_text=await pg.evaluate("outings.find(o=>o.pid==='D1004').name")).locator('[data-act=undo]').click(); await pg.wait_for_timeout(300)
        print('reason chip remembered:', await pg.locator('#dlgBody .mchips .nchip').all_inner_texts())
        print('errors',errs); await b.close()
asyncio.run(main())
