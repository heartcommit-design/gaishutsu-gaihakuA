"""2.3.0：予定に切り替わる境目は「出発が今から30分を超える時」。30分後のボタンは出発の登録のまま（時間がたっても予定に倒れない）"""
import os, datetime
from playwright.sync_api import sync_playwright
HERE=os.path.dirname(os.path.abspath(__file__)); APP=os.path.dirname(HERE)
def main():
    errs=[]
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={'width':1180,'height':820}); pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.clock.install(time=datetime.datetime(2026,11,13,10,0))   # 時計を昼に固定（夜だと「外出で帰院が翌日」の確認が出て登録が止まる）
        pg.goto('file://'+APP+'/index.html'); pg.wait_for_timeout(500); pg.clock.run_for(1000); pg.click('#startOv')
        pg.click('nav button[data-tab=new]'); pg.clock.run_for(500)
        plan=lambda: pg.evaluate('isPlanForm()')
        def wait_st(pid):   # 時計を止めているので、保存（IndexedDB）が終わるまで少しずつ進めて待つ
            for _ in range(60):
                st=pg.evaluate(f"(outings.find(o=>o.pid==='{pid}')||{{}}).status||null")
                if st: return st
                pg.clock.run_for(100); pg.wait_for_timeout(50)
            return None
        for m in ['0','10','20','30']:
            pg.click(f'#depQuick [data-m="{m}"]'); assert not plan(), m
            assert pg.inner_text('#submitBtn')=='この内容で出発を登録', m
        for m in ['60','120','180']:
            pg.click(f'#depQuick [data-m="{m}"]'); assert plan(), m
        pg.click('#depQuick [data-tmr="1"]'); assert plan()
        # 境目：30分ちょうどは出発、31分は予定
        set_=lambda mins: pg.evaluate("m=>{const i=nf.elements.departAt;i.value=toLocalInput(Date.now()+m*60000);i.dispatchEvent(new Event('input',{bubbles:true}))}",mins)
        set_(30); assert not plan(); set_(31); assert plan()
        # 30分後を押してから2分たっても出発のまま。登録すると外出中に入る
        pg.click('#depQuick [data-m="30"]'); pg.clock.run_for(120000); assert not plan()
        pg.fill('input[name=name]','テスト 太郎'); pg.fill('input[name=pid]','P0030'); pg.click('#wardRadios label:has-text("東1")')
        pg.click('#dueQuick [data-h="2"]'); pg.fill('input[name=departNurse]','(デモ) 看護師A'); pg.click('#submitBtn')
        assert wait_st('P0030')=='out'
        # 1時間後は予定
        pg.click('nav button[data-tab=new]'); pg.clock.run_for(300)
        pg.fill('input[name=name]','テスト 花子'); pg.fill('input[name=pid]','P0060'); pg.click('#wardRadios label:has-text("東1")')
        pg.click('#depQuick [data-m="60"]'); pg.click('#dueQuick [data-h="2"]'); pg.fill('input[name=departNurse]','(デモ) 看護師A')
        assert pg.inner_text('#submitBtn')=='予定として登録'
        pg.click('#submitBtn')
        assert wait_st('P0060')=='planned'
        # 再読み込み（起動時の見直し）でも、30分以内の出発は外出中のまま
        pg.reload(); pg.wait_for_timeout(500); pg.clock.run_for(1000); pg.click('#startOv')
        assert wait_st('P0030')=='out'
        b.close()
    print('errors',errs); assert not errs
if __name__=='__main__': main()
