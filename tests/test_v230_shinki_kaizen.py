"""2.3.0 新規登録の改善 1〜5 を assert で確かめる
1 細かく選ぶ（選択欄はふだん隠す・押すと出る・エラーで開く）
2 出発前の札（30分以内に出発で登録→外出・外泊中に「出発前（あと○分）」、出発時刻を過ぎると消える）
3 外出なのに帰院が翌日以降→確認（戻る／外出のまま／外泊に変えて）
4 文字の入力欄にフォーカスがある間は下の登録バーを隠す
5 タグをボタンで選ぶ（select の値・change が今までどおり）
"""
import os
from playwright.sync_api import sync_playwright
HERE=os.path.dirname(os.path.abspath(__file__)); APP=os.path.dirname(HERE)
def main():
    errs=[]
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={'width':1180,'height':820}); pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.clock.install(); pg.goto('file://'+APP+'/index.html#detail'); pg.wait_for_timeout(400); pg.clock.run_for(1000); pg.click('#startOv')
        def wait(js,tries=60):
            for _ in range(tries):
                v=pg.evaluate(js)
                if v: return v
                pg.clock.run_for(100); pg.wait_for_timeout(40)
            return pg.evaluate(js)
        vis=lambda sel: pg.locator(sel).is_visible()
        pg.click('nav button[data-tab=new]'); pg.clock.run_for(300)
        # 1
        assert not vis('#depMan') and not vis('#dueMan')
        pg.click('.tfine[data-man="dueMan"]'); assert vis('#dueMan') and not vis('#depMan')
        pg.click('.tfine[data-man="dueMan"]'); assert not vis('#dueMan')
        pg.fill('input[name=name]','テスト 太郎'); pg.fill('input[name=pid]','P0101'); pg.click('#wardRadios label:has-text("東1")')
        pg.fill('input[name=departNurse]','(デモ) 看護師A'); pg.click('#submitBtn'); pg.clock.run_for(300)
        assert vis('#dueMan'), '帰院予定のエラーで選択欄が開いていない'
        # 4
        pg.focus('input[name=departNurse]'); pg.clock.run_for(50)
        assert pg.evaluate("getComputedStyle(document.getElementById('regBar')).display")=='none'
        pg.click('#dueQuick [data-h="2"]'); pg.clock.run_for(400)
        assert pg.evaluate("getComputedStyle(document.getElementById('regBar')).display")!='none'
        # 5
        n=pg.locator('#tagBtns .tb').count(); assert n==pg.locator('#tagSelect option').count()
        assert pg.locator('#tagBtns .tb.on').inner_text()=='タグなし'
        pg.click('#tagBtns [data-tag="T-05"]'); pg.clock.run_for(50)
        assert pg.input_value('#tagSelect')=='T-05' and pg.locator('#consentBox input[name=consent]').count()==1, '選んでも select／同意書の欄に反映されない'
        assert pg.locator('#tagBtns .tb.on').get_attribute('data-tag')=='T-05'
        pg.select_option('#tagSelect',''); pg.clock.run_for(1100)
        assert pg.locator('#tagBtns .tb.on').get_attribute('data-tag')==''
        # 3：外出で帰院が翌日 → 確認。戻る→登録されない／外泊に変えて→外泊で登録
        setdue="d=>{const i=nf.elements.dueAt;const x=new Date(Date.now()+d*86400000);x.setHours(10,0,0,0);i.value=toLocalInput(x.getTime());i.dispatchEvent(new Event('input',{bubbles:true}))}"
        pg.evaluate(setdue,1); pg.click('#submitBtn'); pg.clock.run_for(200)
        assert pg.locator('#dlg[open]').count()==1 and '翌日以降' in pg.inner_text('#dlgBody')
        pg.click('#dlgActions button:has-text("戻る")'); pg.clock.run_for(300)
        assert pg.evaluate("!outings.some(o=>o.pid==='P0101')")
        pg.click('#submitBtn'); pg.clock.run_for(200); pg.click('#dlgActions button:has-text("外泊に変えて登録")')
        assert wait("(outings.find(o=>o.pid==='P0101')||{}).kind")=='外泊'
        # 外出のまま
        pg.click('nav button[data-tab=new]'); pg.clock.run_for(300)
        pg.fill('input[name=name]','テスト 次郎'); pg.fill('input[name=pid]','P0102'); pg.click('#wardRadios label:has-text("東1")')
        pg.evaluate(setdue,1); pg.fill('input[name=departNurse]','(デモ) 看護師A'); pg.click('#submitBtn'); pg.clock.run_for(200)
        pg.click('#dlgActions button:has-text("外出のまま登録")')
        assert wait("(outings.find(o=>o.pid==='P0102')||{}).kind")=='外出'
        # 同じ日なら確認は出ない
        pg.click('nav button[data-tab=new]'); pg.clock.run_for(300)
        pg.fill('input[name=name]','テスト 三郎'); pg.fill('input[name=pid]','P0103'); pg.click('#wardRadios label:has-text("東1")')
        pg.click('#depQuick [data-m="30"]'); pg.click('#dueQuick [data-h="2"]'); pg.fill('input[name=departNurse]','(デモ) 看護師A'); pg.click('#submitBtn')
        assert wait("(outings.find(o=>o.pid==='P0103')||{}).status")=='out'
        assert pg.locator('#dlg[open]').count()==0
        # 2：出発前の札（時間軸）→一覧でも→出発時刻を過ぎると消える。件数は変わらない
        pg.click('nav button[data-tab=active]'); pg.clock.run_for(1200)
        oid=pg.evaluate("outings.find(o=>o.pid==='P0103').id")
        badge=pg.locator(f'[data-pre="{oid}"]')
        assert badge.count()==1 and '出発前（あと30分）' in badge.first.inner_text(), badge.count()
        pg.clock.run_for(5*60000); pg.wait_for_timeout(100); pg.clock.run_for(1100)
        assert 'あと25分' in badge.first.inner_text(), badge.first.inner_text()
        cnt=pg.inner_text('#cntActive')
        pg.click('#viewSeg [data-view=list]'); pg.clock.run_for(1200)
        assert pg.locator(f'[data-pre="{oid}"]').count()==1
        pg.clock.run_for(26*60000); pg.wait_for_timeout(100); pg.clock.run_for(1200)
        assert pg.locator(f'[data-pre="{oid}"]').count()==0, '出発時刻を過ぎても札が残っている'
        assert pg.inner_text('#cntActive')==cnt
        b.close()
    print('errors',errs); assert not errs
if __name__=='__main__': main()
