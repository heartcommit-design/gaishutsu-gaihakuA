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
        await pg.click('nav button[data-tab=active]'); await pg.wait_for_timeout(300)
        c=pg.locator('#activeList .card').first
        ae="(()=>{const a=document.activeElement;return a.id||a.tagName+'['+(a.name||'')+']'})()"
        for act in ['return','lost','extend','edit','log']:
            await c.locator(f'[data-act={act}]').click(); await pg.wait_for_timeout(250)
            print(act,'focus ->', await pg.evaluate(ae)); 
            if act!='log': await pg.click('#dlgActions button >> nth=0'); await pg.wait_for_timeout(150)
        # log: quick button then cancel
        await pg.fill('#dlgBody input[name=staff]','看護 A'); await pg.locator('#logQuick [data-q]').nth(4).click(); await pg.wait_for_timeout(300)
        print('cancel btns:', await pg.locator('#dlgBody [data-logx]').count())
        await pg.locator('#dlgBody [data-logx]').first.click(); await pg.wait_for_timeout(200)
        print('confirm msg:', (await pg.inner_text('#cdlgMsg')).replace('\n',' / '))
        await pg.click('#cdlgYes'); await pg.wait_for_timeout(400)
        print('after cancel:', await pg.locator('#dlgBody li.lx').count(), '| staff kept', await pg.input_value('#dlgBody input[name=staff]'), '| btns', await pg.locator('#dlgBody [data-logx]').count())
        await pg.screenshot(path='v16_log.png')
        o=await pg.evaluate("outings.find(o=>o.log.some(l=>l.x))"); print('lastLog skips cancelled:', await pg.evaluate("(o=>lastLog(o))(outings.find(o=>o.log.some(l=>l.x)))"))
        await pg.click('#dlgActions button >> nth=0')
        # GO dialog focus
        await pg.click('nav button[data-tab=plan]'); await pg.wait_for_timeout(200); await pg.locator('#planList [data-pact=go]').click(); await pg.wait_for_timeout(250)
        print('go focus ->', await pg.evaluate(ae)); await pg.click('#dlgActions button >> nth=0')
        # presets
        await pg.click('nav button[data-tab=new]'); await pg.wait_for_timeout(200)
        print('dest chips:', await pg.locator('.pchips[data-preset=dest] .nchip').all_inner_texts())
        await pg.locator('.pchips[data-preset=dest] .nchip',has_text='近くのコンビニ').click(); print('dest value:', await pg.input_value('input[name=dest]'), '| focus', await pg.evaluate(ae))
        await pg.locator('.pchips[data-field=famRel] .nchip',has_text='娘').click(); print('famRel:', await pg.input_value('input[name=famRel]'))
        await pg.screenshot(path='v16_form.png',full_page=False)
        await pg.click('nav button[data-tab=settings]'); await pg.fill('#sDest','病院そばのイオン\n自宅\n\n自宅'); await pg.click('#sPresetSave'); await pg.wait_for_timeout(300)
        await pg.click('nav button[data-tab=new]'); await pg.wait_for_timeout(200)
        print('dest chips after:', await pg.locator('.pchips[data-preset=dest] .nchip').all_inner_texts())
        await pg.reload(); await pg.wait_for_timeout(600); await pg.click('#startOv'); await pg.click('nav button[data-tab=new]'); await pg.wait_for_timeout(200)
        print('after reload:', await pg.locator('.pchips[data-preset=dest] .nchip').all_inner_texts())
        print('errors',errs); await b.close()
asyncio.run(main())
