import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        for vp,mob in [({'width':1024,'height':768},False),({'width':768,'height':1024},False),({'width':390,'height':844},True)]:
            ctx=await b.new_context(viewport=vp,has_touch=True,is_mobile=mob); pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
            await pg.goto('file://'+APP+'/index.html'); await pg.wait_for_timeout(500); await pg.tap('#startOv')
            await pg.click('nav button[data-tab=new]'); await pg.wait_for_timeout(200)
            await pg.fill('input[name=name]','予定 太郎'); await pg.fill('input[name=pid]','Y1'); await pg.click('#wardRadios label:has-text("東1")')
            await pg.evaluate("(()=>{const i=nf.elements.departAt;i.value=toLocalInput(Date.now()+86400000);i.dispatchEvent(new Event('input',{bubbles:true}));})()")
            await pg.click('#dueQuick button[data-d="1"]'); await pg.fill('input[name=departNurse]','看護 A'); await pg.click('#submitBtn'); await pg.wait_for_timeout(600)
            await pg.click('nav button[data-tab=plan]'); await pg.wait_for_timeout(300)
            await pg.locator('#planList [data-pact=go]').first.tap(); await pg.wait_for_timeout(300)
            dl=await pg.evaluate("(()=>{const d=document.getElementById('dlg');const r=d.getBoundingClientRect();const b=[...document.querySelectorAll('#dlgActions button')].map(x=>{const q=x.getBoundingClientRect();return x.textContent+':'+Math.round(q.top)+'-'+Math.round(q.bottom)});return {open:d.open,top:Math.round(r.top),bottom:Math.round(r.bottom),vh:innerHeight,btns:b}})()")
            print(vp, dl)
            await pg.screenshot(path=f"cg_{vp['width']}.png")
            await pg.locator('#dlgActions button',has_text='やめる').tap(); await pg.wait_for_timeout(300)
            print('  after やめる open?', await pg.evaluate("document.getElementById('dlg').open"), '| status', await pg.evaluate("outings[0].status"), errs)
            await ctx.close()
        await b.close()
asyncio.run(main())
