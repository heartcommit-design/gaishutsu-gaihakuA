import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        for w,h,mob in [(1024,1366,False),(390,844,True)]:
            pg=await b.new_page(viewport={'width':w,'height':h},is_mobile=mob,has_touch=True); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            await pg.goto('file://'+APP+'/index.html'); await pg.wait_for_timeout(500); await pg.tap('#startOv')
            await pg.click('nav button[data-tab=settings]'); await pg.click('#demoIn'); await pg.wait_for_timeout(1200)
            await pg.evaluate("(async()=>{const now=Date.now();for(let i=0;i<5;i++){const o={id:uid(),name:'見本 外出'+i,pid:'X'+i,ward:'東1',room:'',adm:'任意入院',kind:'外出',departAt:now-3600000,dueAt:now+(i+1)*3600000,dueAtOriginal:now+(i+1)*3600000,dest:'近くのコンビニ',alone:true,selfTel:'090-1111-000'+i,famName:'',famRel:'',famTel:'',clothes:'黒い上着',tagId:'',consent:false,departNurse:'看護 A',status:'out',createdAt:now,hasPhoto:false,log:[]};await saveOuting(o);outings.push(o);}lastSig='';await tick();})()")
            await pg.click('nav button[data-tab=active]'); await pg.wait_for_timeout(1200)
            txt=await pg.inner_text('#activeList')
            print(w,'rows',await pg.locator('#activeList .crow').count(),'| phone numbers visible?', '090-' in txt, '| clothes visible?', '黒い上着' in txt)
            await pg.screenshot(path=f'v18_{w}.png')
            r=pg.locator('#activeList .crow').first
            print('  first row buttons:', await r.locator('button').all_inner_texts())
            await r.locator('[data-act=open]').click(); await pg.wait_for_timeout(1200)
            print('  after open: full cards', await pg.locator('#activeList .card:not(.crow)').count(), '| close btn', await pg.locator('#activeList [data-act=close]').count())
            if w==1024: await pg.screenshot(path='v18_open.png')
            await pg.evaluate("Object.keys(openUntil).forEach(k=>openUntil[k]=Date.now()-1)"); await pg.wait_for_timeout(1300)
            print('  auto closed:', await pg.locator('#activeList .card:not(.crow)').count()==0)
            # return from compact row
            c=pg.locator('#activeList .crow',has_text='見本 外出4'); await c.locator('[data-act=return]').click(); await pg.wait_for_timeout(300)
            print('  return dlg:', await pg.inner_text('#dlgTitle'))
            await pg.click('#dlgActions button >> nth=0')
            # print rendering full
            full=await pg.evaluate("(async()=>{printFull=true;await renderActive();const n=document.querySelectorAll('#activeList .card:not(.crow)').length;const c=document.querySelectorAll('#activeList [data-act=close]').length;printFull=false;lastSig='';await tick();return [n,c]})()")
            print('  print mode full cards/close btns:', full, '| back to compact', await pg.locator('#activeList .crow').count())
            print('  scrollW', await pg.evaluate("document.documentElement.scrollWidth"), 'errors', errs)
            await pg.close()
        await b.close()
asyncio.run(main())
