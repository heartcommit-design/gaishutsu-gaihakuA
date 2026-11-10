import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
D=OUT+'/'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1024,'height':1366},has_touch=True)
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('file://'+APP+'/index.html'); await pg.wait_for_timeout(500); await pg.click('#startOv')
        await pg.click('nav button[data-tab=settings]'); await pg.click('#demoIn'); await pg.wait_for_timeout(1500)
        # bulk patients
        await pg.evaluate("""(async()=>{const K=['あ','い','う','え','お','か','き','く','け','こ'];for(let i=0;i<40;i++){const p={id:uid(),pid:'Z'+(1000+i),name:'見本 患者'+i,kana:'みほん かんじゃ'+K[i%10],sex:i%2?'女':'男',age:String(30+i),famName:'見本 家族'+i,famRel:'母',famTel:'090-1234-'+(1000+i),ward:'東1',room:String(100+i),adm:'任意入院',count:i%3,dests:[],lastOutAt:i<15?Date.now()-i*3600000:0,createdAt:Date.now()};patients.push(p);await dbPut('patients',p);}})()""")
        await pg.click('nav button[data-tab=new]'); await pg.wait_for_timeout(300)
        h=await pg.evaluate("document.getElementById('pChips').getBoundingClientRect().height"); print('chips height', round(h), '| count', await pg.locator('#pChips .chip').count(), '|', await pg.inner_text('#pChipsMore'))
        await pg.screenshot(path=D+'v17_new.png',clip={'x':0,'y':200,'width':1024,'height':450})
        await pg.fill('#pSearch','かんじゃ'); await pg.wait_for_timeout(200); print('search count', await pg.locator('#pChips .chip').count(), '|', await pg.inner_text('#pChipsMore'))
        await pg.click('nav button[data-tab=patients]'); await pg.wait_for_timeout(300)
        print('ptCount', await pg.inner_text('#ptCount'))
        await pg.screenshot(path=D+'v17_pt.png')
        # scroll inside wrap
        await pg.evaluate("(()=>{const w=document.querySelector('#ptTable').parentElement;w.scrollLeft=600;w.scrollTop=400;})()"); await pg.wait_for_timeout(200)
        await pg.screenshot(path=D+'v17_pt_scrolled.png')
        nm=await pg.evaluate("(()=>{const w=document.querySelector('#ptTable').parentElement;const th=document.querySelector('#ptTable th.nm0').getBoundingClientRect();const wr=w.getBoundingClientRect();const td=document.querySelector('#ptTable tbody td.nm0').getBoundingClientRect();return {thTop:Math.round(th.top-wr.top),thLeft:Math.round(th.left-wr.left),tdLeft:Math.round(td.left-wr.left)}})()")
        print('sticky after scroll:', nm)
        await pg.locator('#ptTable [data-ptgo]').first.click(); await pg.wait_for_timeout(300); print('ptgo -> name', await pg.input_value('input[name=name]'))
        print('errors',errs); await b.close()
asyncio.run(main())
