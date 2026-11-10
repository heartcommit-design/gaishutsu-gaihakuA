import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
D=HERE+'/data/'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1024,'height':1366})
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto('file://'+APP+'/index.html#detail'); await pg.wait_for_timeout(500); await pg.click('#startOv')
        await pg.click('nav button[data-tab=patients]'); await pg.wait_for_timeout(200)
        await pg.set_input_files('#ptCsvFile',D+'sjis.csv'); await pg.wait_for_timeout(500)
        print('dlg:', (await pg.inner_text('#dlgBody'))[:600].replace('\n',' | '))
        await pg.screenshot(path=OUT+'/imp1.png')
        await pg.click('#dlgActions button.pri'); await pg.wait_for_timeout(600)
        ps=await pg.evaluate("patients.map(p=>[p.pid,p.name,p.kana,p.sex,ageOf(p),p.birth||'',p.famName,p.famRel,p.famTel,p.ward,p.room].join('|'))")
        for x in ps: print(' ',x)
        await pg.set_input_files('#ptCsvFile',D+'utf8.csv'); await pg.wait_for_timeout(400)
        print('utf8 dlg head:', (await pg.inner_text('#dlgBody'))[:80].replace('\n',' '))
        await pg.click('#dlgActions button.pri'); await pg.wait_for_timeout(400)
        print('A1005:', await pg.evaluate("(p=>[p.name,p.kana,p.sex,ageOf(p)].join('|'))(patients.find(p=>p.pid==='A1005'))"))
        # re-import sjis with keep -> A1003 empty kana stays; second time should be 'unchanged'
        await pg.set_input_files('#ptCsvFile',D+'sjis.csv'); await pg.wait_for_timeout(400)
        print('reimport:', (await pg.inner_text('#dlgBody'))[:60].replace('\n',' ')); await pg.click('#dlgActions button:not(.pri)')
        await pg.set_input_files('#ptCsvFile',D+'bad.csv'); await pg.wait_for_timeout(400)
        print('bad:', (await pg.inner_text('#dlgBody'))[:80].replace('\n',' ')); await pg.click('#dlgActions button')
        # search by kana (katakana input)
        await pg.fill('#ptQ','ミホンハナ'); await pg.wait_for_timeout(200); print('search kata->', await pg.locator('#ptTable tr').count()-1)
        await pg.fill('#ptQ',''); await pg.screenshot(path=OUT+'/imp2.png')
        # register outing from chip
        await pg.click('nav button[data-tab=new]'); await pg.fill('#pSearch','さぶろう'); await pg.wait_for_timeout(200)
        await pg.locator('#pChips .chip').first.click(); await pg.wait_for_timeout(200)
        print('form:', [await pg.input_value(f'input[name={n}]') for n in ['name','pid','kana','age','famName','famTel']], await pg.input_value('select[name=sex]'))
        await pg.click('#dueQuick button[data-h="2"]'); await pg.fill('input[name=departNurse]','看護 A'); await pg.click('#submitBtn'); await pg.wait_for_timeout(700)
        print('card sub:', await pg.locator('#activeList .card .sub').first.inner_text())
        p2=await pg.evaluate("(p=>[p.kana,p.sex,ageOf(p),p.birth,p.count].join('|'))(patients.find(p=>p.pid==='A1004'))"); print('patient after outing:', p2)
        await pg.click('nav button[data-tab=history]'); await pg.wait_for_timeout(300)
        print('history head:', (await pg.locator('#hTable tr').first.inner_text())[:80].replace('\n',' ').replace('\t',' '))
        print('errors',errs); await b.close()
asyncio.run(main())
