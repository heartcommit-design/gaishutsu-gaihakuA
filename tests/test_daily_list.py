import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
SP=OUT
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1180,'height':820},has_touch=True)
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('file://'+APP+'/index.html#detail'); await pg.wait_for_timeout(600); await pg.click('#startOv')
        await pg.click('nav button[data-tab=settings]'); await pg.click('#demoIn'); await pg.wait_for_timeout(1000)
        # a returned record yesterday
        await pg.evaluate("""async()=>{const d=new Date();d.setDate(d.getDate()-1);d.setHours(13,0,0,0);const t=d.getTime();
          const o={id:uid(),name:'高橋 三郎',pid:'1234',ward:'西1',room:'105',adm:'任意入院',kind:'外出',departAt:t,dueAt:t+2*3600000,dueAtOriginal:t+2*3600000,returnedAt:t+2.5*3600000,returnNurse:'看護師D',dest:'明石駅のコンビニ',alone:true,selfTel:'080-1111-2222',famName:'高橋 花',famRel:'妻',famTel:'080-3333-4444',clothes:'',tagId:'T-05',tagReturned:true,consent:true,departNurse:'看護師C',note:'',status:'returned',hasPhoto:false,photoDeletedAt:t+2.5*3600000,log:[{at:t,text:'外出に出発',by:'看護師C'},{at:t+2.5*3600000,text:'帰院',by:'看護師D'}]};
          await saveOuting(o);outings.push(o);}""")
        await pg.click('nav button[data-tab=history]'); await pg.wait_for_timeout(400)
        print(await pg.inner_text('#hTitle'), '|', await pg.inner_text('#hSum'))
        print('cols:', await pg.locator('#hTable thead th').count(), 'rows today:', await pg.locator('#hTable tbody tr[data-id]').count())
        await pg.screenshot(path=SP+'/x1.png')
        await pg.click('#hYest'); await pg.wait_for_timeout(300)
        print(await pg.inner_text('#hTitle'), '| rows:', await pg.locator('#hTable tbody tr[data-id]').count())
        print('row:', (await pg.locator('#hTable tbody tr').first.inner_text()).replace('\t',' | ')[:300])
        await pg.locator('#hTable tbody tr').first.click(); await pg.wait_for_timeout(300)
        print('detail:', await pg.inner_text('#dlgTitle')); await pg.click('#dlgActions button')
        await pg.click('#hNext'); print('next ->', await pg.inner_text('#hTitle'))
        await pg.click('nav button[data-tab=calendar]'); await pg.wait_for_timeout(300); await pg.click('#calToTable'); await pg.wait_for_timeout(300)
        print('from calendar ->', await pg.inner_text('#hTitle'))
        print('errors',errs); await b.close()
asyncio.run(main())
