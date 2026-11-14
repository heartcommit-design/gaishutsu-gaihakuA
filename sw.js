// 外出・外泊管理（新版：ガラス調・時間軸）：オフライン起動用（画面のファイルだけを保存。患者データは扱わない）
// 新版は現行（gaishutsu-v…）と同じドメインに置かれても混ざらないよう、別の名前のキャッシュを使う。
// 古いキャッシュを消すときも、新版自身のもの（gaishutsu-shisaku- で始まる）だけを消す。
const PREFIX = 'gaishutsu-shisaku-';
const CACHE = 'gaishutsu-shisaku-v2.2.2';
const FILES = ['./', './index.html', './manifest.webmanifest', './icon-180.png', './icon-192.png', './icon-512.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES))); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith(PREFIX) && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  // 保存済みの画面をすぐ返し（オフラインでも起動）、裏で新しい版を取りに行く
  e.respondWith(caches.open(CACHE).then(async c => {
    const key = req.mode === 'navigate' ? './index.html' : req;
    const hit = await c.match(key, { ignoreSearch: true });
    const net = fetch(req).then(r => { if (r && r.ok) c.put(key, r.clone()); return r; }).catch(() => null);
    return hit || (await net) || new Response('オフラインです', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }));
});
