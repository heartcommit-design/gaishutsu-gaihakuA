import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
SP=OUT
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':820,'height':1180},has_touch=True)
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('file://'+APP+'/index.html#detail'); await pg.wait_for_timeout(600)
        # simulate old-version bad record: out with future depart + tag
        await pg.evaluate("""async()=>{const t=Date.now()+10*86400000;const tg=tags.find(x=>x.id==='T-03');const o={id:uid(),name:'浦島 太郎',pid:'B1111',ward:'東1',room:'',adm:'任意入院',kind:'外泊',departAt:t,dueAt:t+2*86400000,dueAtOriginal:t+2*86400000,dest:'自宅',alone:false,compName:'浦島 姫',compRel:'妻',compTel:'',selfTel:'09088888888',famName:'',famRel:'',famTel:'',clothes:'黒ロンT',tagId:'T-03',consent:true,departNurse:'田中 花子',note:'',status:'out',createdAt:Date.now(),hasPhoto:false,log:[]};
          tg.status='inuse';tg.outingId=o.id;await saveTag(tg);await saveOuting(o);}""")
        await pg.reload(); await pg.wait_for_timeout(700); await pg.click('#startOv')
        print('active cards:', await pg.locator('#activeList .card').count(), '| plan count:', await pg.inner_text('#cntPlan'), '| T-03:', await pg.evaluate("tags.find(t=>t.id==='T-03').status"))
        # new future 外泊 registration -> plan
        await pg.click('nav button[data-tab=new]')
        await pg.fill('input[name=name]','乙姫 花'); await pg.fill('input[name=pid]','P'+str(abs(hash('乙姫 花'))%1000)); await pg.click('#wardRadios label:has-text("西2")'); await pg.click('#kindRadios label:has-text("外泊")')
        fut=await pg.evaluate("toLocalInput(Date.now()+3*86400000)")
        await pg.evaluate("([s,v])=>{const i=document.querySelector(s);i.value=v;i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}))}",['input[name=departAt]',fut]); await pg.click('#dueQuick button[data-d="2"]')
        print('plan mode:', await pg.inner_text('#submitBtn'), '| tag hidden:', await pg.evaluate("document.getElementById('fsTag').hidden"))
        await pg.fill('input[name=departNurse]','看護師A'); await pg.click('#submitBtn'); await pg.wait_for_timeout(800)
        print('plan list:', await pg.locator('#planList .card').count(), '| active:', await pg.locator('#activeList .card').count())
        await pg.screenshot(path=SP+'/p1.png')
        # departure procedure for 乙姫
        await pg.locator('#planList .card',has_text='乙姫').locator('[data-pact=edit]').click(); await pg.wait_for_timeout(400)
        print('departure btn:', await pg.inner_text('#submitBtn'), '| kind:', await pg.evaluate("nf.elements.kind.value"), '| tag visible:', not await pg.evaluate("document.getElementById('fsTag').hidden"))
        await pg.select_option('#tagSelect','T-01'); await pg.click('#submitBtn'); await pg.wait_for_timeout(500)
        print('err:', (await pg.inner_text('#formErr')).replace('\n',' | '))
        await pg.check('input[name=consent]'); await pg.fill('input[name=departNurse]','看護師B'); await pg.click('#submitBtn'); await pg.wait_for_timeout(900)
        c=pg.locator('#activeList .card',has_text='乙姫')
        print('active label:', await c.locator('.lbl').inner_text(), '|', await c.locator('.count').inner_text(), '| plans left:', await pg.inner_text('#cntPlan'))
        print('log:', await pg.evaluate("outings.find(o=>o.name==='乙姫 花'&&o.status==='out').log.map(l=>l.text).join(' / ')"))
        await pg.screenshot(path=SP+'/p2.png')
        await pg.click('nav button[data-tab=calendar]'); await pg.wait_for_timeout(400); await pg.screenshot(path=SP+'/p3.png')
        print('errors',errs); await b.close()
asyncio.run(main())
