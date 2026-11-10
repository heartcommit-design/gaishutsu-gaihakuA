import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
SP=OUT
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1024,'height':1366},has_touch=True)
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('file://'+APP+'/index.html#detail'); await pg.wait_for_timeout(600); await pg.click('#startOv')
        await pg.click('nav button[data-tab=new]'); await pg.wait_for_timeout(300)
        dep=pg.locator('input[name=departAt]'); due=pg.locator('input[name=dueAt]')
        dw=pg.locator('.tp',has=dep); uw=pg.locator('.tp',has=due)
        print('raw inputs hidden:', await dep.is_hidden(), await due.is_hidden())
        print('dep date/time:', await dw.locator('.tp-d').evaluate("s=>s.selectedOptions[0].text"), await dw.locator('.tp-t').input_value(), '| value', await dep.input_value())
        print('due empty:', await uw.locator('.tp-d').evaluate("s=>s.selectedOptions[0].text"), await uw.locator('.tp-t').evaluate("s=>s.selectedOptions[0].text"))
        print('time options count:', await dw.locator('.tp-t option').count())
        await pg.click('#submitBtn'); await pg.wait_for_timeout(300)
        print('due wrap invalid:', await uw.evaluate("e=>e.classList.contains('invalid')"))
        await pg.screenshot(path=SP+'/tp1.png')
        await pg.click('#dueQuick button[data-h="2"]'); await pg.wait_for_timeout(100)
        v=await due.input_value(); print('+2h ->', v, '| on 15 grid:', int(v[-2:])%15==0, '| select shows', await uw.locator('.tp-t').input_value(), '| invalid cleared?', not await uw.evaluate("e=>e.classList.contains('invalid')"))
        # choose time via select only
        await uw.locator('.tp-t').select_option('18:30'); print('select 18:30 ->', await due.input_value())
        await uw.locator('.tp-d').select_option(index=await uw.locator('.tp-d').evaluate("s=>s.selectedIndex+1")); print('next day ->', await due.input_value(), await uw.locator('.tp-d').evaluate("s=>s.selectedOptions[0].text"))
        # fine mode
        await uw.locator('.tp-fine').click(); print('fine mode visible input:', await due.is_visible(), '| btn', await uw.locator('.tp-fine').inner_text())
        await due.fill(v[:11]+'19:07'); await uw.locator('.tp-fine').click(); print('after fine 19:07 -> select', await uw.locator('.tp-t').input_value(), '| value', await due.input_value())
        await pg.screenshot(path=SP+'/tp2.png')
        # register
        await pg.fill('input[name=name]','時刻 太郎'); await pg.fill('input[name=pid]','T1'); await pg.click('#wardRadios label:has-text("東1")')
        await due.evaluate("i=>{}")
        await uw.locator('.tp-d').select_option(index=7)  # today
        await uw.locator('.tp-t').select_option('23:45')
        await pg.fill('input[name=departNurse]','看護 B'); await pg.click('#submitBtn'); await pg.wait_for_timeout(800)
        o=await pg.evaluate("outings.find(o=>o.pid==='T1')"); print('registered:', o and o['status'], o and await pg.evaluate(f"fmt({o['dueAt']})"))
        await pg.click('nav button[data-tab=new]'); await pg.wait_for_timeout(300)
        print('after reset due:', await uw.locator('.tp-t').evaluate("s=>s.selectedOptions[0].text"), repr(await due.input_value()))
        # extend dialog
        await pg.click('nav button[data-tab=active]'); await pg.wait_for_timeout(300)
        c=pg.locator('#activeList .card',has_text='時刻 太郎')
        await c.locator('[data-act=extend]').click(); await pg.wait_for_timeout(300)
        dd=pg.locator('#dlgBody .tp'); print('extend picker:', await dd.count(), await dd.locator('.tp-t').input_value(), '| chips:', await pg.locator('#dlgBody .mchips').count())
        await dd.locator('.tp-t').select_option('23:45'); await dd.locator('.tp-d').select_option(index=8)
        await pg.fill('#dlgBody input[name=reason]','家族から電話、夕食後に戻る'); await pg.fill('#dlgBody input[name=staff]','看護 B')
        await pg.click('#dlgActions button.pri'); await pg.wait_for_timeout(600)
        o=await pg.evaluate("outings.find(o=>o.pid==='T1')"); print('extended to', await pg.evaluate(f"fmt({o['dueAt']})"), '|', o['log'][-1]['text'])
        await c.locator('[data-act=extend]').click(); await pg.wait_for_timeout(300)
        print('chips now:', await pg.locator('#dlgBody .mchips .nchip').all_inner_texts())
        await pg.locator('#dlgBody .mchips .nchip').first.click(); print('reason filled:', await pg.input_value('#dlgBody input[name=reason]'))
        await pg.screenshot(path=SP+'/tp3.png')
        await pg.click('#dlgActions button:not(.pri)')
        await pg.reload(); await pg.wait_for_timeout(700); await pg.click('#startOv')
        await pg.locator('#activeList .card',has_text='時刻 太郎').locator('[data-act=extend]').click(); await pg.wait_for_timeout(300)
        print('chips after reload:', await pg.locator('#dlgBody .mchips .nchip').all_inner_texts())
        print('errors', errs); await b.close()
asyncio.run(main())
