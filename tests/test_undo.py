import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
SP=OUT+'/'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1024,'height':1366},has_touch=True)
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('file://'+APP+'/index.html#detail'); await pg.wait_for_timeout(500); await pg.click('#startOv')
        setdt="([n,v])=>{const i=nf.elements[n];i.value=v;i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}))}"
        await pg.click('nav button[data-tab=new]')
        await pg.fill('input[name=name]','予定 太郎'); await pg.fill('input[name=pid]','Y1'); await pg.click('#wardRadios label:has-text("東1")')
        await pg.evaluate(setdt,['departAt',await pg.evaluate("toLocalInput(Date.now()+86400000)")])
        await pg.click('#dueQuick button[data-d="1"]'); await pg.select_option('#tagSelect','T-02'); await pg.check('#consentBox input[name=consent]')
        await pg.fill('input[name=departNurse]','看護 A'); await pg.click('#submitBtn'); await pg.wait_for_timeout(600)
        o=await pg.evaluate("outings.find(o=>o.pid==='Y1')"); print('1 plan', o['status'], o['tagId'], await pg.evaluate("tags.find(t=>t.id==='T-02').status"))
        # back button from departure route
        await pg.locator('#planList [data-pact=edit]').click(); await pg.wait_for_timeout(300)
        print('2 back btn visible', await pg.locator('#planBack').is_visible()); await pg.click('#planBack'); await pg.wait_for_timeout(300)
        print('  after back: tab plan active', await pg.evaluate("document.getElementById('sec-plan').classList.contains('active')"), '| status', await pg.evaluate("outings.find(o=>o.pid==='Y1').status"), '| form name cleared', await pg.input_value('input[name=name]')=='' )
        # plan edit route
        await pg.locator('#planList [data-pact=planedit]').click(); await pg.wait_for_timeout(300)
        print('3 edit btn text', await pg.inner_text('#submitBtn'), '| tag preselected', await pg.input_value('#tagSelect'))
        newdep=await pg.evaluate("toLocalInput(Date.now()+2*86400000)"); await pg.evaluate(setdt,['departAt',newdep]); await pg.click('#dueQuick button[data-d="2"]')
        await pg.select_option('#tagSelect',''); await pg.fill('input[name=dest]','実家'); await pg.fill('input[name=departNurse]','看護 B'); await pg.click('#submitBtn'); await pg.wait_for_timeout(700)
        L=await pg.evaluate("outings.filter(o=>o.pid==='Y1')"); o=L[0]
        print('  plans for Y1:', len(L), o['status'], 'dest', o['dest'], 'tag', repr(o['tagId']), '| T-02', await pg.evaluate("tags.find(t=>t.id==='T-02').status"), '| departAtPlanned', o.get('departAtPlanned'))
        print('  log:', [x['text'][:40] for x in o['log']])
        # GO then undo
        await pg.click('nav button[data-tab=plan]'); await pg.wait_for_timeout(200)
        await pg.locator('#planList [data-pact=go]').click(); await pg.wait_for_timeout(300); await pg.select_option('#goTag','T-03'); await pg.wait_for_timeout(100)
        if await pg.locator('#goConsent input[name=gcOk]').count(): await pg.check('#goConsent input[name=gcOk]')
        await pg.locator('#dlgBody .nchip').first.click(); await pg.click('#dlgActions button.ok'); await pg.wait_for_timeout(700)
        print('4 GO:', await pg.evaluate("outings.find(o=>o.pid==='Y1').status"), '| toast', (await pg.inner_text('#toast'))[:70])
        c=pg.locator('#activeList .card',has_text='予定 太郎'); await c.locator('[data-act=edit]').click(); await pg.wait_for_timeout(300)
        print('  undo button:', await pg.locator('#dlgActions button',has_text='予定に戻す').count())
        await pg.screenshot(path=SP+'undo1.png')
        await pg.locator('#dlgActions button',has_text='予定に戻す').click(); await pg.wait_for_timeout(200)
        print('  no reason -> stays open', await pg.evaluate("document.getElementById('dlg').open"))
        await pg.fill('#dlgBody input[name=reason]','GOを押し間違えた'); await pg.locator('#dlgBody .nchip').first.click()
        await pg.locator('#dlgActions button',has_text='予定に戻す').click(); await pg.wait_for_timeout(300); await pg.click('#cdlgYes'); await pg.wait_for_timeout(700)
        o=await pg.evaluate("outings.find(o=>o.pid==='Y1')")
        print('5 undo:', o['status'], 'departAt=newdep', await pg.evaluate(f"toLocalInput({o['departAt']})")==newdep, '| tag', o['tagId'], await pg.evaluate("tags.find(t=>t.id==='T-03').status"), '| active cards', await pg.locator('#activeList .card').count(), '| plan tab', await pg.inner_text('#cntPlan'))
        print('  log:', o['log'][-1]['text'])
        await pg.screenshot(path=SP+'undo2.png')
        # GO again works
        await pg.locator('#planList [data-pact=go]').click(); await pg.wait_for_timeout(300)
        print('6 GO again default tag', await pg.input_value('#goTag')); await pg.locator('#dlgBody .nchip').first.click(); await pg.click('#dlgActions button.ok'); await pg.wait_for_timeout(600)
        print('  status', await pg.evaluate("outings.find(o=>o.pid==='Y1').status"), await pg.evaluate("tags.find(t=>t.id==='T-03').status"))
        # normal outing (not from plan) has no undo button
        c=pg.locator('#activeList .card').first
        print('errors', errs); await b.close()
asyncio.run(main())
