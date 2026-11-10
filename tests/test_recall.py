import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
SP=OUT
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':820,'height':1180},has_touch=True)
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.on('dialog',lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto('file://'+APP+'/index.html#detail'); await pg.wait_for_timeout(600); await pg.click('#startOv')
        await pg.click('nav button[data-tab=settings]'); await pg.click('#demoIn'); await pg.wait_for_timeout(1200)
        # first registration
        await pg.click('nav button[data-tab=new]'); await pg.wait_for_timeout(300)
        print('chips', await pg.locator('#pChips .chip').count())
        await pg.fill('input[name=name]','高橋 三郎'); await pg.fill('input[name=pid]','P'+str(abs(hash('高橋 三郎'))%1000)); await pg.fill('input[name=pid]','1234')
        await pg.click('#wardRadios label:has-text("西1")')
        await pg.fill('input[name=dest]','明石駅のコンビニ'); await pg.fill('input[name=selfTel]','080-1111-2222')
        await pg.fill('input[name=famName]','高橋 花'); await pg.fill('input[name=famRel]','妻'); await pg.fill('input[name=famTel]','080-3333-4444')
        await pg.click('#dueQuick button[data-h="1"]'); await pg.fill('input[name=departNurse]','看護師B')
        await pg.click('#submitBtn'); await pg.wait_for_timeout(1000)
        c=pg.locator('.card',has_text='高橋 三郎')
        print('card sub:', await c.locator('.sub').first.inner_text())
        await c.locator('[data-act=return]').click(); await pg.fill('#dlgForm input[name=nurse]','看護師C'); await pg.click('#dlgActions button.ok'); await pg.wait_for_timeout(800)
        # second time: recall
        await pg.click('nav button[data-tab=new]'); await pg.wait_for_timeout(300)
        await pg.fill('#pSearch','高橋'); await pg.wait_for_timeout(200)
        await pg.click('#pChips .chip'); await pg.wait_for_timeout(300)
        vals=await pg.evaluate("()=>{const f=document.getElementById('newForm').elements;return [f.name.value,f.pid.value,f.ward.value,f.dest.value,f.selfTel.value,f.famName.value,f.famTel.value]}")
        print('recalled', vals)
        await pg.screenshot(path=SP+'/n1.png',full_page=True)
        await pg.click('#dueQuick button[data-h="2"]'); await pg.fill('input[name=departNurse]','看護師B')
        await pg.click('#submitBtn'); await pg.wait_for_timeout(800)
        print('patients', await pg.evaluate("patients.map(p=>p.name+':'+p.count).join(', ')"))
        await pg.click('nav button[data-tab=patients]'); await pg.wait_for_timeout(300)
        await pg.screenshot(path=SP+'/n2.png',full_page=True)
        await pg.click('nav button[data-tab=active]'); await pg.wait_for_timeout(800)
        await pg.screenshot(path=SP+'/n3.png')
        print('errors',errs); await b.close()
asyncio.run(main())
