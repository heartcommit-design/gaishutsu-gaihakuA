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
        await pg.click('nav button[data-tab=settings]'); await pg.click('#demoIn'); await pg.wait_for_timeout(1000)
        # register with photo then return
        await pg.click('nav button[data-tab=new]')
        await pg.fill('input[name=name]','高橋 三郎'); await pg.fill('input[name=pid]','P'+str(abs(hash('高橋 三郎'))%1000)); await pg.click('#wardRadios label:has-text("西1")')
        await pg.click('#dueQuick button[data-h="1"]'); await pg.fill('input[name=departNurse]','看護師B'); await pg.fill('input[name=dest]','明石駅')
        await pg.set_input_files('#photoInput',SP+'/p.png'); await pg.wait_for_timeout(500)
        await pg.click('#submitBtn'); await pg.wait_for_timeout(800)
        c=pg.locator('.card',has_text='高橋 三郎'); await c.locator('[data-act=return]').click()
        await pg.fill('#dlgForm input[name=nurse]','看護師C'); await pg.click('#dlgActions button.ok'); await pg.wait_for_timeout(800)
        # inject a past record last month (returned, late, searched)
        await pg.evaluate("""async()=>{const now=Date.now();const d=new Date();d.setMonth(d.getMonth()-1);d.setDate(15);d.setHours(10,0,0,0);const t=d.getTime();
          const o={id:uid(),name:'高橋 三郎',pid:'',ward:'西1',room:'105',adm:'任意入院',kind:'外出',departAt:t,dueAt:t+2*3600000,dueAtOriginal:t+2*3600000,returnedAt:t+3.5*3600000,returnNurse:'看護師D',dest:'公園',alone:true,selfTel:'',famName:'',famRel:'',famTel:'',clothes:'',tagId:'T-02',tagReturned:true,departNurse:'看護師D',status:'returned',hasPhoto:false,photoDeletedAt:t+3.5*3600000,log:[{at:t,text:'外出に出発',by:'看護師D'},{at:t+2.2*3600000,text:'捜索開始（連絡：同行の家族・関係者）',by:'看護師D'},{at:t+3.5*3600000,text:'帰院',by:'看護師D'}]};
          await saveOuting(o);outings.push(o);}""")
        await pg.click('nav button[data-tab=calendar]'); await pg.wait_for_timeout(500)
        await pg.screenshot(path=SP+'/c1.png',full_page=True)
        await pg.locator('#calDay .dayrow',has_text='高橋 三郎').click(); await pg.wait_for_timeout(400)
        print('detail photo line:', await pg.locator('#dlgBody dd',has_text='削除済み').inner_text())
        await pg.screenshot(path=SP+'/c2.png')
        await pg.click('#dlgActions button'); 
        await pg.click('#calPrev'); await pg.wait_for_timeout(300)
        await pg.click('#calGrid [data-d$="-15"]'); await pg.wait_for_timeout(300)
        print('last month day15:', (await pg.inner_text('#calDay')).replace('\n',' | ')[:200])
        await pg.click('nav button[data-tab=patients]'); await pg.wait_for_timeout(300)
        await pg.locator('#ptTable tr',has_text='高橋 三郎').locator('[data-pthist]').click(); await pg.wait_for_timeout(300)
        print('patient hist:', (await pg.inner_text('#dlgTitle')))
        await pg.set_viewport_size({'width':390,'height':900}); await pg.click('#dlgActions button'); await pg.click('nav button[data-tab=calendar]'); await pg.wait_for_timeout(400)
        await pg.screenshot(path=SP+'/c3.png')
        print('errors',errs); await b.close()
asyncio.run(main())
