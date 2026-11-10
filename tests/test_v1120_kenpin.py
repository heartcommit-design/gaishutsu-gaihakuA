"""1.12.0 検品の直し。assert で確かめる。データはすべて架空。
1. GO で写真を撮った時、外出の保存（outings）が先、写真の保存（photos）が後。写真の保存に失敗しても、タグと外出の状態は食い違わない。
2. GO で服装の欄が空なら、経過に「服装を記入」を残さない。
3. 古いバックアップ（1.10.0 以前）から復元したら、行き先の3つを足す処理がもう一度だけ動く（重ねない）。新しいバックアップでは動かない。
4. CSV取り込みの確認画面で、退院中の患者が含まれる時は「退院中の◯人は情報だけ更新します（退院のまま）」と出す。
"""
import os, json, struct, zlib
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); APP = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
URL = 'file://' + APP + '/index.html#detail'
NURSE = '(デモ) 看護師A'


def png(path, w=60, h=80):
    raw = b''.join(b'\x00' + b'\x70\x30\x30' * w for _ in range(h))
    ch = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))


PHOTO = os.path.join(OUT, 'kenpin_p.png'); png(PHOTO)
errs = []


def open_app(ctx):
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(200)
    return pg


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1024, 'height': 1366}, has_touch=True)
        pg = open_app(ctx)
        # 架空の患者3人と予定3件（P0003 の予定は写真あり・服装あり）
        pg.evaluate("""async()=>{const now=Date.now();
          for(const [pid,name] of [['P0001','テスト 太郎'],['P0002','テスト 花子'],['P0003','テスト 次郎'],['P0004','テスト 四郎']]){
            const x={id:'pt'+pid,pid,name,ward:'東1',adm:'任意入院',consentDate:'2026-10-01',consentLog:[],count:0,dests:[],createdAt:now};patients.push(x);await dbPut('patients',x);}
          const mk=(pid,name,clothes,hasPhoto)=>({id:'pl'+pid,patientId:'pt'+pid,name,pid,ward:'東1',adm:'任意入院',kind:'外出',departAt:now+3*3600000,dueAt:now+6*3600000,dueAtOriginal:now+6*3600000,
            dest:'見本の公園',alone:true,clothes,tagId:'',consent:false,departNurse:NURSE,status:'planned',createdAt:now,hasPhoto,log:[{at:now,text:'外出の予定を登録',by:NURSE}]});
          const NURSE='(デモ) 看護師A';
          for(const o of [mk('P0001','テスト 太郎','',false),mk('P0002','テスト 花子','',false),mk('P0003','テスト 次郎','服P 紺の上着',true),mk('P0004','テスト 四郎','服Q 白い帽子',false)]){outings.push(o);await saveOuting(o);}
          await dbPut('photos',new Blob(['old'],{type:'image/jpeg'}),'plP0003');
          // 保存の順番を記録し、必要なら写真の保存だけ失敗させる
          window.__puts=[];window.__failPhoto=false;const orig=IDBObjectStore.prototype.put;
          IDBObjectStore.prototype.put=function(v,k){window.__puts.push(this.name);if(this.name==='photos'&&window.__failPhoto)throw new Error('テスト：写真の保存に失敗');return orig.call(this,v,k);};}""")

        def go(name, photo=False, clothes=None, tag=''):
            pg.click('nav button[data-tab=plan]'); pg.wait_for_timeout(250)
            pg.locator('#planList .card', has_text=name).locator('[data-pact=go]').click(); pg.wait_for_timeout(300)
            if photo:
                pg.set_input_files('#goPhotoInput', PHOTO); pg.wait_for_timeout(500)
            if clothes is not None:
                pg.fill('#dlgBody textarea[name=goClothes]', clothes)
            pg.select_option('#goTag', tag); pg.wait_for_timeout(100)
            pg.fill('#dlgForm input[name=nurse]', NURSE)
            pg.evaluate("window.__puts=[]")
            pg.click('#dlgActions button.ok'); pg.wait_for_timeout(900)

        O = lambda pid: pg.evaluate("pid=>outings.find(o=>o.pid===pid)", pid)
        DBO = lambda pid: pg.evaluate("pid=>dbGet('outings','pl'+pid)", pid)
        logs = lambda o: [l['text'] for l in o['log']]

        # ---- 1a 写真あり：外出の保存が先、写真の保存が後
        go('テスト 太郎', photo=True, tag='T-01')
        puts = pg.evaluate('window.__puts')
        assert 'outings' in puts and 'photos' in puts and puts.index('outings') < puts.index('photos'), puts
        o = O('P0001')
        assert o['status'] == 'out' and o['hasPhoto'] and o['tagId'] == 'T-01', o
        assert DBO('P0001')['hasPhoto'] and DBO('P0001')['status'] == 'out', '写真のあとの外出の保存ができていない'
        assert pg.evaluate("dbKeys('photos').then(k=>k.includes('plP0001'))")

        # ---- 1b 写真の保存に失敗：出発・タグは登録され、食い違わない
        pg.evaluate("window.__failPhoto=true")
        go('テスト 花子', photo=True, tag='T-02')
        o = O('P0002'); d = DBO('P0002')
        assert o['status'] == 'out' and d['status'] == 'out' and d['tagId'] == 'T-02', (o['status'], d)
        assert not o['hasPhoto'] and not d['hasPhoto'], '写真がないのに「写真あり」になっている'
        t = pg.evaluate("dbGet('tags','T-02')")
        assert t['status'] == 'inuse' and t['outingId'] == 'plP0002', t
        assert pg.evaluate("tags.find(x=>x.id==='T-02').status") == 'inuse'
        assert not pg.evaluate("dbKeys('photos').then(k=>k.includes('plP0002'))")
        assert any('保存できなかった' in x for x in logs(d)), logs(d)
        assert '服装写真を保存できませんでした' in pg.inner_text('#toast')
        assert pg.locator('#activeList .card[data-id="plP0002"]').count() == 1, '外出中の一覧に出ていない'
        # 予定で撮った写真がある人：撮り直しに失敗しても、前の写真と「写真あり」のまま
        go('テスト 次郎', photo=True)
        o = O('P0003')
        assert o['status'] == 'out' and o['hasPhoto'] and DBO('P0003')['hasPhoto'], o
        assert pg.evaluate("dbGet('photos','plP0003').then(b=>b&&b.size)") == 3, '前の写真が残っていない'
        assert not any('撮り直し' in x for x in logs(o))
        pg.evaluate("window.__failPhoto=false")

        # ---- 2 服装の欄が空なら「服装を記入」を残さない
        assert not any('服装を記入' in x for x in logs(O('P0001'))), '服装が空なのに記録が残った'
        assert not any('服装を記入' in x for x in logs(O('P0002')))
        # 予定で入れた服装を、GOで空にしても記録は残さず、予定の服装のまま
        go('テスト 四郎', clothes='   ')
        o = O('P0004')
        assert not any('服装を記入' in x for x in logs(o)) and o['clothes'] == '服Q 白い帽子', (o['clothes'], logs(o))
        # （比べるため）記入した時は記録が残る：GOの取消で予定に戻して、もう一度
        pg.evaluate("undoDeparture(outings.find(o=>o.pid==='P0004'),'テスト','(デモ) 看護師A')"); pg.wait_for_timeout(400)
        go('テスト 四郎', clothes='服R 赤いマフラー')
        o = O('P0004')
        assert o['clothes'] == '服R 赤いマフラー' and sum('服装を記入' in x for x in logs(o)) == 1, logs(o)

        # ---- 4 CSV取り込み：退院中の患者
        pg.evaluate("""async()=>{const p=patients.find(x=>x.pid==='P0001');p.status='discharged';p.dischargedAt='2026-11-01';await dbPut('patients',p);}""")
        csvp = os.path.join(OUT, 'kenpin_dis.csv')
        open(csvp, 'w', encoding='utf-8-sig').write('氏名,患者ID,家族連絡先\r\nテスト 太郎,P0001,090-0000-0111\r\nテスト 花子,P0002,090-0000-0222\r\nテスト 九郎,P0009,090-0000-0999\r\n')
        pg.click('nav button[data-tab=patients]'); pg.wait_for_timeout(200)
        pg.set_input_files('#ptCsvFile', csvp); pg.wait_for_timeout(500)
        assert '退院中の1人は情報だけ更新します（退院のまま）' in pg.inner_text('#dlgBody'), pg.inner_text('#dlgBody')[:300]
        assert '更新（退院中）' in pg.inner_text('#dlgBody')
        pg.click('#dlgActions button.pri'); pg.wait_for_timeout(500)
        t = pg.evaluate("patients.find(x=>x.pid==='P0001')")
        assert t['status'] == 'discharged' and t['famTel'] == '090-0000-0111', t
        assert pg.evaluate("patients.find(x=>x.pid==='P0009').status") is None
        # 退院中の人がいなければ出さない
        csvq = os.path.join(OUT, 'kenpin_in.csv')
        open(csvq, 'w', encoding='utf-8-sig').write('氏名,患者ID\r\nテスト 花子,P0002\r\n')
        pg.set_input_files('#ptCsvFile', csvq); pg.wait_for_timeout(500)
        assert '退院中' not in pg.inner_text('#dlgBody') and pg.locator('#csvDis').count() == 0
        pg.click('#dlgActions button:has-text("やめる")')
        ctx.close()

        # ---- 3 バックアップからの復元
        ctx2 = b.new_context(viewport={'width': 1024, 'height': 1366})
        pg = open_app(ctx2)

        def restore(settings, name):
            fp = os.path.join(OUT, name)
            json.dump({'app': 'gaishutsu_kanri', 'version': 1, 'exportedAt': 0, 'settings': settings, 'tags': [], 'patients': [], 'outings': []},
                      open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
            pg.click('nav button[data-tab=settings]'); pg.wait_for_timeout(200)
            pg.set_input_files('#bkIn', fp); pg.wait_for_timeout(300)
            pg.click('#cdlgYes'); pg.wait_for_timeout(800)
            assert '復元しました' in pg.inner_text('#toast'), pg.inner_text('#toast')
            return pg.evaluate('settings.destPresets')

        # 古いバックアップ（印なし）：3つを足す。すでにある「喫煙」は重ねない
        dp = restore({'destPresets': ['自宅', '喫煙'], 'nurses': []}, 'kenpin_old.json')
        assert dp == ['自宅', '喫煙', '図書館', '加古川のイオン'], dp
        assert pg.evaluate('settings.destAdded1110') is True
        assert pg.evaluate("dbGet('settings','main').then(s=>[s.destPresets.length,s.destAdded1110])") == [4, True]
        # そのあと利用者が消したものは、開き直しても足さない（一度だけ）
        pg.fill('#sDest', '自宅'); pg.click('#sPresetSave'); pg.wait_for_timeout(300)
        pg.reload(); pg.wait_for_timeout(700); pg.click('#startOv'); pg.wait_for_timeout(200)
        assert pg.evaluate('settings.destPresets') == ['自宅']
        # 新しいバックアップ（1.11.0 以降・印あり）：足さない
        dp = restore({'destPresets': ['自宅', '見本の公園'], 'destAdded1110': True, 'nurses': []}, 'kenpin_new.json')
        assert dp == ['自宅', '見本の公園'], dp
        ctx2.close(); b.close()
    print('errors', errs)
    assert not errs


if __name__ == '__main__':
    main()
