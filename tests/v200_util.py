"""2.0.0（試作版）のテストで共通に使う小道具。
- contrast(pg, selector)：画面上の実際の色からコントラスト比を計算する。
  文字の色は計算済みスタイルから取り、背景は「文字を一時的に透明にして撮った画面写真」の画素から取る
  （半透明のガラス・ぼかし・背景の色の面を含めた、実際に見えている色）。背景の画素のうち最も条件の悪いものとの比を返す。
- jst(...)：日本時間の日時（Playwright の時計を固定するときに渡す）／ms(...)：同じ日時をミリ秒で
"""
import base64, datetime

JST = datetime.timezone(datetime.timedelta(hours=9))


def jst(y, mo, d, h=0, mi=0, s=0):
    return datetime.datetime(y, mo, d, h, mi, s, tzinfo=JST)


def ms(y, mo, d, h=0, mi=0, s=0):
    return int(jst(y, mo, d, h, mi, s).timestamp() * 1000)


def _lum(r, g, b):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def ratio(c1, c2):
    a, b = _lum(*c1), _lum(*c2)
    if a < b:
        a, b = b, a
    return (a + 0.05) / (b + 0.05)


_DECODE = """async (b64)=>{const img=new Image();img.src='data:image/png;base64,'+b64;await img.decode();
  const c=document.createElement('canvas');c.width=img.width;c.height=img.height;const x=c.getContext('2d');x.drawImage(img,0,0);
  const d=x.getImageData(0,0,c.width,c.height).data;const seen={};
  for(let i=0;i<d.length;i+=4){const k=d[i]+','+d[i+1]+','+d[i+2];seen[k]=(seen[k]||0)+1;}
  return Object.entries(seen).map(([k,n])=>[k.split(',').map(Number),n]);}"""


def contrast(pg, el, decoder):
    """el: Locator（1要素）。decoder: 画像を読むための別ページ（about:blank）。最小のコントラスト比を返す。"""
    # 上に固定した帯（ヘッダー・アラーム帯）に隠れないよう、画面の中ほどへ動かしてから撮る
    el.evaluate("e=>e.scrollIntoView({block:'center',inline:'nearest'})")
    info = el.evaluate("""e=>{const cs=getComputedStyle(e);const m=cs.color.match(/[\\d.]+/g).map(Number);
      const st=document.createElement('style');st.id='__ct';
      e.setAttribute('data-ct','1');st.textContent='[data-ct],[data-ct] *{color:transparent!important;text-shadow:none!important;caret-color:transparent!important;-webkit-text-fill-color:transparent!important}[data-ct]::placeholder{color:transparent!important}';
      document.head.appendChild(st);
      // 子要素が自分の背景を持つとき（件数バッジなど）は、その子を隠して親の文字の背景だけを見る（子は別に確かめる）
      e.querySelectorAll('*').forEach(c=>{const b=getComputedStyle(c).backgroundColor;if(b&&b!=='rgba(0, 0, 0, 0)'&&b!=='transparent'){c.setAttribute('data-ct-h','1');c.style.setProperty('visibility','hidden','important');}});
      const r=e.getBoundingClientRect();
      return {c:m.slice(0,3),a:m.length>3?m[3]:1,x:r.x,y:r.y,w:r.width,h:r.height};}""")
    pg.wait_for_timeout(60)
    pad = 2
    clip = {'x': info['x'] + pad, 'y': info['y'] + pad, 'width': max(2, info['w'] - 2 * pad), 'height': max(2, info['h'] - 2 * pad)}
    png = pg.screenshot(clip=clip, animations='disabled')
    el.evaluate("e=>{e.removeAttribute('data-ct');const s=document.getElementById('__ct');if(s)s.remove();e.querySelectorAll('[data-ct-h]').forEach(c=>{c.removeAttribute('data-ct-h');c.style.removeProperty('visibility');});}")
    px = decoder.evaluate(_DECODE, base64.b64encode(png).decode())
    total = sum(n for _, n in px)
    # ごく少ない画素（角の縁・影のにじみ）は除き、面の9割以上を占める色だけで判定する
    px.sort(key=lambda t: -t[1])
    keep, acc = [], 0
    for c, n in px:
        keep.append(c); acc += n
        if acc >= total * 0.9:
            break
    tc, a = info['c'], info['a']
    worst = 99
    for bg in keep:
        fg = [round(tc[i] * a + bg[i] * (1 - a)) for i in range(3)]
        worst = min(worst, ratio(fg, bg))
    return worst
