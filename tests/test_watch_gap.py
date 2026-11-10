import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
SP=OUT
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':820,'height':1180},has_touch=True)
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('file://'+APP+'/index.html#detail'); await pg.wait_for_timeout(600); await pg.click('#startOv')
        # --- 1st registration with tag: consent required
        await pg.click('nav button[data-tab=new]')
        await pg.fill('input[name=name]','高橋 三郎'); await pg.fill('input[name=pid]','P'+str(abs(hash('高橋 三郎'))%1000)); await pg.click('#wardRadios label:has-text("西1")')
        await pg.click('#dueQuick button[data-h="2"]'); await pg.select_option('#tagSelect','T-01')
        print('consent box:', (await pg.inner_text('#consentBox'))[:40])
        await pg.fill('input[name=departNurse]','看護師A'); await pg.click('#submitBtn'); await pg.wait_for_timeout(400)
        print('err:', 'タグ T-01 を渡すには' in await pg.inner_text('#formErr'))
        await pg.check('#consentBox input[name=consent]'); await pg.click('#submitBtn'); await pg.wait_for_timeout(800)
        print('registered:', await pg.locator('#activeList .card').count(), '| patient consent:', await pg.evaluate("patients[0].consentDate"))
        # --- return with checklist
        c=pg.locator('#activeList .card',has_text='高橋')
        await c.locator('[data-act=return]').click(); await pg.wait_for_timeout(300)
        print('nurse chips in return dlg:', await pg.locator('#dlgBody .nchip').count())
        await pg.locator('#dlgBody .nchip').first.click()
        await pg.check('#dlgBody input[name=rc_belong]'); await pg.fill('#dlgBody input[name=rcm_state]','落ち着いている'); await pg.check('#dlgBody input[name=rc_med]'); await pg.fill('#dlgBody textarea[name=rc_other]','家族より土産あり')
        await pg.click('#dlgActions button.ok'); await pg.wait_for_timeout(700)
        print('rcText:', await pg.evaluate("rcText(outings[0])"))
        # --- 2nd registration: recall, consent ok automatically
        await pg.click('nav button[data-tab=new]'); await pg.wait_for_timeout(200)
        await pg.click('#pChips .chip'); await pg.select_option('#tagSelect','T-02'); await pg.wait_for_timeout(100)
        print('consent box 2nd:', (await pg.inner_text('#consentBox'))[:30])
        print('form nurse chips:', await pg.locator('#newForm .nchips:not(.mchips) .nchip').count())
        await pg.locator('#newForm .nchips:not(.mchips) .nchip').first.click(); await pg.click('#dueQuick button[data-h="1"]')
        await pg.click('#submitBtn'); await pg.wait_for_timeout(700)
        print('2nd registered:', await pg.locator('#activeList .card').count())
        # --- edit departure time, then cancel
        c=pg.locator('#activeList .card',has_text='高橋')
        await c.locator('[data-act=edit]').click(); await pg.wait_for_timeout(300)
        newdep=await pg.evaluate("toLocalInput(Date.now()-30*60000)")
        await pg.evaluate("([s,v])=>{const i=document.querySelector(s);i.value=v;i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}))}",['#dlgBody input[name=departAt]',newdep]); await pg.fill('#dlgBody input[name=reason]','入力間違い'); await pg.locator('#dlgBody .nchip').first.click()
        await pg.click('#dlgActions button.pri'); await pg.wait_for_timeout(500)
        print('edit log:', await pg.evaluate("outings[1].log.slice(-1)[0].text"))
        await c.locator('[data-act=edit]').click(); await pg.wait_for_timeout(300)
        await pg.fill('#dlgBody input[name=reason]','テスト入力'); await pg.locator('#dlgBody .nchip').first.click()
        await pg.click('#dlgActions button.bad'); await pg.wait_for_timeout(300); await pg.click('#cdlgYes'); await pg.wait_for_timeout(700)
        print('after cancel active:', await pg.locator('#activeList .card').count(), '| T-02:', await pg.evaluate("tags.find(t=>t.id==='T-02').status"), '| status:', await pg.evaluate("outings[1].status"))
        # --- withdrawn consent blocks tag
        await pg.click('nav button[data-tab=patients]'); await pg.wait_for_timeout(200)
        await pg.locator('#ptTable tbody tr').first.locator('[data-ptwd]').click(); await pg.locator('#dlgBody .nchip').first.click(); await pg.click('#dlgActions button.bad'); await pg.wait_for_timeout(400)
        print('patient table consent:', (await pg.locator('#ptTable tr').nth(1).inner_text()).split('\t')[6][:20])
        await pg.click('nav button[data-tab=new]'); await pg.click('#pChips .chip'); await pg.select_option('#tagSelect','T-03'); await pg.wait_for_timeout(100)
        print('withdrawn box:', (await pg.inner_text('#consentBox'))[:30])
        await pg.click('#dueQuick button[data-h="1"]'); await pg.locator('#newForm .nchips:not(.mchips) .nchip').first.click(); await pg.click('#submitBtn'); await pg.wait_for_timeout(300)
        print('withdrawn err:', '撤回' in await pg.inner_text('#formErr'))
        # --- history with cancelled row
        await pg.click('nav button[data-tab=history]'); await pg.wait_for_timeout(300)
        print('hist sum:', await pg.inner_text('#hSum'))
        print('cancel row:', await pg.locator('#hTable tr.r-cancelled').count(), '| rc col present:', '帰院時確認' in await pg.inner_text('#hTable thead'))
        # --- demo: escalation & mask & stats
        await pg.click('nav button[data-tab=settings]'); await pg.click('#demoIn'); await pg.wait_for_timeout(1500)
        print('urgent:', await pg.evaluate("document.getElementById('banner').classList.contains('urgent')"), '|', (await pg.inner_text('#bannerMsg'))[:30])
        await pg.click('nav button[data-tab=settings]'); await pg.check('#sMask'); await pg.click('#sSave'); await pg.wait_for_timeout(300)
        await pg.click('nav button[data-tab=active]'); await pg.wait_for_timeout(1300)
        print('masked names:', await pg.locator('#activeList .name').all_inner_texts())
        await pg.locator('#activeList .card').first.locator('[data-act=reveal]').click(); await pg.wait_for_timeout(1300)
        print('revealed first:', await pg.locator('#activeList .name').first.inner_text())
        await pg.screenshot(path=SP+'/m1.png')
        await pg.click('nav button[data-tab=stats]'); await pg.wait_for_timeout(300)
        print('stats total row:', (await pg.locator('#stTable tr.tot').inner_text()).replace('\t',' | '))
        await pg.screenshot(path=SP+'/s_stats.png')
        # --- gap detection & watch & backup bar
        await pg.evaluate("lastTickAt=Date.now()-5*60000"); await pg.wait_for_timeout(1200)
        print('gapBar:', not await pg.evaluate("document.getElementById('gapBar').hidden"), (await pg.inner_text('#gapMsg'))[:40])
        await pg.evaluate("settings.backupHour=0;settings.lastBackupDay='';settings.bkDismissDay=''"); await pg.wait_for_timeout(1200)
        print('bkBar:', not await pg.evaluate("document.getElementById('bkBar').hidden"))
        # watch: needs no alerts -> ack demo alarms by returning overdue patients
        await pg.evaluate("outings.forEach(o=>{if(isActive(o)&&o.dueAt<Date.now()){o.dueAt=Date.now()+3600000;}})"); 
        await pg.evaluate("settings.idleMin=1;lastInteract=Date.now()-2*60000"); await pg.wait_for_timeout(1300)
        print('watchOv:', not await pg.evaluate("document.getElementById('watchOv').hidden"), (await pg.inner_text('#watchMsg'))[:30])
        await pg.screenshot(path=SP+'/w1.png')
        await pg.click('#watchOv'); await pg.wait_for_timeout(300)
        print('watch hidden after tap:', await pg.evaluate("document.getElementById('watchOv').hidden"))
        # reload: closed gap
        await pg.evaluate("settings.lastAlive=Date.now()-10*60000;saveSettings()"); await pg.wait_for_timeout(300)
        await pg.reload(); await pg.wait_for_timeout(800)
        print('closed gap:', (await pg.inner_text('#gapMsg'))[:45])
        print('errors',errs); await b.close()
asyncio.run(main())
