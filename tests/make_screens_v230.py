"""2.3.0 の画面写真を docs/screens_v2.3.0/ に撮る（suite には入れない）。
新規登録の ①開いた直後 ②患者を選んだ直後 ③登録できる状態 ④外泊の時刻 ⑤予定に切り替わった状態 ⑥「細かく選ぶ」を開いた状態 ⑦タグのボタン、
外出・外泊中の「出発前」の札（時間軸・一覧）、外出で帰院が翌日以降の時の確認。
両配色（明るい／暗い）× iPad 横 1180×820・iPad 縦 1024×1366、1倍。①は画面全体（full_page。固定の下のバーは隠す）も撮る。
時計を 2026/11/13(金) 10:00（日本時間）に固定し、架空の患者・看護師で撮る。各画面で横にはみ出していないことも確かめる。
"""
import os
from playwright.sync_api import sync_playwright
from v200_util import jst
try:
    from PIL import Image
except ImportError:
    Image = None

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
DST = os.path.join(APP, 'docs', 'screens_v2.3.0'); os.makedirs(DST, exist_ok=True)
SIZES = [(1180, 820, 'ipad_yoko'), (1024, 1366, 'ipad_tate')]
NURSE = '(デモ) 看護師A'
PATIENTS = """async()=>{const L=[
  {pid:'P0001',name:'(デモ) 見本 太郎',kana:'みほん たろう',sex:'男',age:'45',ward:'東2',adm:'医療保護入院',selfTel:'090-0000-0001',famName:'(デモ) 見本 花子',famRel:'母',famTel:'090-0000-0002',lastDest:'見本の公園'},
  {pid:'P0002',name:'(デモ) 見本 次郎',kana:'みほん じろう',sex:'男',age:'62',ward:'西1',adm:'任意入院'},
  {pid:'P0003',name:'(デモ) 見本 和子',kana:'みほん かずこ',sex:'女',age:'71',ward:'東1',adm:'任意入院'}];
  let i=0;for(const x of L){const p={id:'pt'+(++i),count:1,dests:[],lastOutAt:Date.now()-i*86400000,createdAt:Date.now(),...x};patients.push(p);await dbPut('patients',p);}
  renderPatientChips();}"""


def small(fp):
    if Image:  # 公開リポジトリを重くしないよう、256色に減らして保存（2.0.0 と同じ）
        Image.open(fp).convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(fp, optimize=True)


def main():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w, h, tag in SIZES:
            for th in ['light', 'dark']:
                ctx = b.new_context(viewport={'width': w, 'height': h}, timezone_id='Asia/Tokyo', device_scale_factor=1, has_touch=True)
                pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
                pg.clock.set_fixed_time(jst(2026, 11, 13, 10, 0))
                pg.goto('file://' + APP + '/index.html'); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(300)
                pg.evaluate("window.tone=function(){}")
                pg.click('nav button[data-tab=settings]'); pg.click(f'#thmSeg [data-thm={th}]'); pg.wait_for_timeout(200)
                pg.evaluate(PATIENTS)

                def blur():
                    pg.evaluate('document.activeElement&&document.activeElement.blur()'); pg.wait_for_timeout(450)

                def to(sel, block='start'):
                    # 上の帯の下に来るように置く（なめらかな移動は使わない）
                    pg.evaluate("([s,b])=>{const e=document.querySelector(s);const top=document.querySelector('.topbar').getBoundingClientRect().height;"
                                "const r=e.getBoundingClientRect();const y=b==='start'?r.top+scrollY-top-12:r.top+scrollY-(innerHeight-r.height)/2;window.scrollTo({top:Math.max(0,y),behavior:'instant'});}", [sel, block])
                    pg.wait_for_timeout(150)

                def shot(name, full=False):
                    pg.wait_for_timeout(1100)   # 毎秒の描き直し（下のバー）を待つ
                    sw = pg.evaluate('document.documentElement.scrollWidth')
                    assert sw <= w, f'{name} {th} {tag}: 横にはみ出し {sw}>{w}'
                    pg.evaluate("document.getElementById('toast').style.display='none'")
                    pg.wait_for_timeout(120)
                    fp = os.path.join(DST, f'{name}_{th}_{tag}.png')
                    if full:  # 画面全体の写真では、固定の下のバーが途中に写り込むので隠す（下の登録ボタンは同じもの）
                        pg.evaluate("document.getElementById('regBar').style.visibility='hidden'")
                    pg.screenshot(path=fp, full_page=full, animations='disabled'); small(fp)
                    pg.evaluate("document.getElementById('regBar').style.visibility=''")

                pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(300)
                pg.evaluate("window.scrollTo({top:0,behavior:'instant'})")
                shot('shinki1_hiraita'); shot('shinki1_hiraita_zentai', full=True)
                # ② 患者を選んだ直後
                pg.locator('#pChips [data-pt]', has_text='見本 太郎').first.click(); pg.wait_for_timeout(900)
                to('#newForm'); shot('shinki2_kanja')
                # ③ 登録できる状態（帰院 +3時間・看護師）
                pg.click('#dueQuick [data-h="3"]'); pg.fill('input[name=departNurse]', NURSE); blur()
                to('#newForm>fieldset:nth-of-type(2)'); shot('shinki3_toroku_dekiru')
                # ⑦ タグのボタン（T-02 を選ぶ → 同意書の欄）
                pg.click('#tagBtns [data-tag="T-02"]'); pg.wait_for_timeout(200)
                to('#fsTag'); shot('shinki7_tag')
                pg.click('#tagBtns [data-tag=""]'); pg.wait_for_timeout(100)
                # ④ 外泊の時刻（明後日 13:00）
                pg.click('#kindRadios label:has-text("外泊")'); pg.click('#dueQuick [data-d="2"]'); pg.click('#dueQuick [data-t="13:00"]'); blur()
                to('#newForm>fieldset:nth-of-type(2)'); shot('shinki4_gaihaku')
                # ⑤ 予定に切り替わった状態（出発 明日 10:00）
                pg.click('#depQuick [data-tmr="1"]'); pg.click('#depTimes [data-t="10:00"]'); pg.click('#dueQuick [data-d="2"]'); blur()
                to('#newForm>fieldset:nth-of-type(2)'); shot('shinki5_yotei')
                # ⑥ 細かく選ぶを開いた状態
                pg.click('.tfine[data-man="depMan"]'); pg.click('.tfine[data-man="dueMan"]'); blur()
                to('#newForm>fieldset:nth-of-type(2)'); shot('shinki6_komakaku')
                pg.click('.tfine[data-man="depMan"]'); pg.click('.tfine[data-man="dueMan"]')
                # 外出で帰院が翌日以降 → 確認
                pg.click('#pUnload'); pg.wait_for_timeout(200)
                pg.locator('#pChips [data-pt]', has_text='見本 次郎').first.click(); pg.wait_for_timeout(900)
                pg.click('#depQuick [data-m="0"]')
                pg.evaluate("(()=>{const i=nf.elements.dueAt;i.value='2026-11-14T10:00';i.dispatchEvent(new Event('input',{bubbles:true}))})()")
                pg.fill('input[name=departNurse]', NURSE); blur()
                pg.click('#rbBtn'); pg.wait_for_timeout(400)
                assert pg.locator('#dlg[open]').count() == 1
                shot('kakunin_yokujitsu')
                pg.click('#dlgActions button:has-text("戻る")'); pg.wait_for_timeout(300)
                # 出発前の札：30分後の出発で登録 → 外出・外泊中
                pg.click('#depQuick [data-m="30"]'); pg.click('#dueQuick [data-h="3"]'); blur()
                pg.click('#rbBtn'); pg.wait_for_timeout(900)
                pg.click('nav button[data-tab=new]'); pg.wait_for_timeout(300)
                pg.locator('#pChips [data-pt]', has_text='見本 和子').first.click(); pg.wait_for_timeout(600)
                pg.click('#depQuick [data-m="0"]'); pg.click('#dueQuick [data-h="2"]'); pg.fill('input[name=departNurse]', NURSE); blur()
                pg.click('#rbBtn'); pg.wait_for_timeout(900)
                pg.click('nav button[data-tab=active]'); pg.wait_for_timeout(300)
                for view, lbl in [('timeline', 'jikanjiku'), ('list', 'ichiran')]:
                    pg.click(f'#viewSeg [data-view={view}]'); pg.wait_for_timeout(500)
                    assert pg.locator('[data-pre]').count() >= 1, '出発前の札が無い'
                    pg.evaluate("window.scrollTo({top:0,behavior:'instant'})")
                    shot(f'shuppatsumae_{lbl}')
                ctx.close()
        b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
