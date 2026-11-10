import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio, os
from playwright.async_api import async_playwright
SP=OUT
URL='file://'+APP+'/index.html#detail'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={'width':820,'height':1180},has_touch=True)
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m: m.type=='error' and errs.append(m.text))
        await pg.goto(URL); await pg.wait_for_timeout(800); await pg.screenshot(path=SP+'/s0.png'); await pg.click('#startOv'); await pg.wait_for_timeout(300)
        # demo data
        await pg.click('nav button[data-tab=settings]'); await pg.click('#demoIn'); await pg.wait_for_timeout(1500)
        print('cards', await pg.locator('.card').count(), 'overdue', await pg.locator('.card.st-overdue').count(), 'soon', await pg.locator('.card.st-soon').count())
        print('banner on', await pg.locator('#banner.on').count(), await pg.inner_text('#bannerMsg'))
        await pg.screenshot(path=SP+'/s1.png',full_page=True)
        # new registration with photo
        await pg.click('nav button[data-tab=new]')
        await pg.fill('input[name=name]','テスト 太郎'); await pg.fill('input[name=pid]','P'+str(abs(hash('テスト 太郎'))%1000)); await pg.click('#wardRadios label:has-text("東1")')
        await pg.click('#dueQuick button[data-h="2"]')
        await pg.select_option('#tagSelect','T-05')
        await pg.check('input[name=consent]')
        await pg.fill('input[name=departNurse]','看護師B')
        # create a png photo
        await pg.evaluate("""()=>{}""")
        png=SP+'/p.png'
        import struct,zlib
        def mk(w,h):
            raw=b''.join(b'\x00'+b'\x80\x20\x20'*w for _ in range(h))
            def ch(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
            return b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw))+ch(b'IEND',b'')
        open(png,'wb').write(mk(60,80))
        await pg.set_input_files('#photoInput',png); await pg.wait_for_timeout(600)
        await pg.click('#submitBtn'); await pg.wait_for_timeout(1200)
        print('cards after new', await pg.locator('.card').count())
        print('photos in db', await pg.evaluate("dbKeys('photos').then(k=>k.length)"))
        # lost flow on test card
        card=pg.locator('.card',has_text='テスト 太郎')
        await card.locator('[data-act=lost]').click()
        await pg.fill('#dlgForm input[name=staff]','看護師B'); await pg.click('#dlgActions button.srch'); await pg.wait_for_timeout(1200)
        print('search cards', await pg.locator('.card.st-search').count())
        await pg.screenshot(path=SP+'/s2.png',full_page=True)
        # return flow
        await card.locator('[data-act=return]').click()
        await pg.fill('#dlgForm input[name=nurse]','看護師C'); await pg.click('#dlgActions button.ok'); await pg.wait_for_timeout(1200)
        print('photos in db after return', await pg.evaluate("dbKeys('photos').then(k=>k.length)"))
        print('T-04 status', await pg.evaluate("tags.find(t=>t.id==='T-04').status"))
        # ack
        await pg.click('#bannerAck'); await pg.wait_for_timeout(1200)
        print('ack button visible', await pg.is_visible('#bannerAck'))
        # history
        await pg.click('nav button[data-tab=history]'); await pg.wait_for_timeout(500)
        print('history rows', await pg.locator('#hTable tr[data-id]').count())
        await pg.screenshot(path=SP+'/s3.png',full_page=True)
        await pg.click('nav button[data-tab=tags]'); await pg.wait_for_timeout(300)
        await pg.screenshot(path=SP+'/s4.png')
        # reload persistence
        await pg.reload(); await pg.wait_for_timeout(800); await pg.click('#startOv'); await pg.wait_for_timeout(800)
        print('after reload cards', await pg.locator('.card').count())
        await pg.set_viewport_size({'width':390,'height':900}); await pg.click('nav button[data-tab=active]'); await pg.wait_for_timeout(1200)
        await pg.screenshot(path=SP+'/s5.png')
        print('errors', errs)
        await b.close()
asyncio.run(main())
