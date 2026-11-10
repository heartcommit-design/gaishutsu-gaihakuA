import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__));APP=_os.path.dirname(HERE);OUT=_os.path.join(HERE,'out');_os.makedirs(OUT,exist_ok=True)
import http.server,threading,functools,os
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def __init__(s,*a,**k):super().__init__(*a,directory=APP,**k)
    def log_message(self,*a):pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8791),Q);threading.Thread(target=srv.serve_forever,daemon=True).start()
errs=[]
with sync_playwright() as p:
    b=p.chromium.launch();pg=b.new_page(viewport={'width':1180,'height':820})
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8791/index.html');pg.wait_for_timeout(800);pg.get_by_text('タップして開始').click();pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('#demoIn').click()");pg.wait_for_timeout(1500)
    r=pg.evaluate("""({pts:patients.length,demo:patients.filter(x=>x.demo).length,e1:patients.filter(x=>x.ward==='東1').length,
      out:outings.filter(x=>x.status==='out').length,plan:outings.filter(x=>x.status==='planned').length,
      uniqPid:new Set(patients.map(x=>x.pid)).size,
      sample:patients.slice(0,12).map(x=>[x.name,x.kana,x.sex,x.age,x.room,x.adm,x.famName,x.famRel,x.famTel,x.consentDate,x.count]),
      outs:outings.map(o=>[o.name,o.ward,o.status,o.tagId,o.patientId===(patients.find(p=>p.pid===o.pid)||{}).id]),
      toast:document.querySelector('#toast').textContent,
      nocons:patients.filter(x=>!x.consentDate).length,
      sexes:[patients.filter(x=>x.sex==='男').length,patients.filter(x=>x.sex==='女').length],
      ages:[Math.min(...patients.map(x=>+x.age)),Math.max(...patients.map(x=>+x.age))]})""")
    for k,v in r.items():print(k,v)
    # second press guarded
    pg.evaluate("document.querySelector('#demoIn').click()");pg.wait_for_timeout(600)
    print('again',pg.evaluate("[patients.length,document.querySelector('#toast').textContent]"))
    # register tab
    pg.evaluate("showTab('patients')");pg.wait_for_timeout(500)
    print('rows',pg.evaluate("document.querySelectorAll('#patientList tbody tr, .xl tbody tr').length"),pg.evaluate("(document.querySelector('#ptCount')||{}).textContent"))
    pg.screenshot(path='demo50_pts.png')
    pg.evaluate("showTab('active')");pg.wait_for_timeout(400);pg.screenshot(path='demo50_active.png')
    # reload persistence
    pg.reload();pg.wait_for_timeout(1000);print('after reload',pg.evaluate("[patients.length,outings.length]"))
    pg.evaluate("document.querySelector('#demoOut').click()");pg.wait_for_timeout(1000)
    print('after demoOut',pg.evaluate("[patients.length,outings.length,tags.filter(t=>t.status!=='available').length]"))
    pg.reload();pg.wait_for_timeout(1000);print('after reload2',pg.evaluate("[patients.length,outings.length]"))
    b.close()
print('errors',errs)
