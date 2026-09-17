#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
birlestir.py
------------
Tek dosyalık HTML panellerini sekmeli TEK bir HTML dosyasında toplar.

Kullanım:
    1) Bu script'i panel HTML dosyalarıyla aynı klasöre koy.
    2) Aşağıdaki PANELS listesindeki dosya adlarını kendi dosya adlarınla değiştir.
    3) python birlestir.py
    4) Çıktı: birlesik_panel.html  (çift tıkla, tarayıcıda açılır)

Panellerden birini güncellediğinde script'i tekrar çalıştırman yeterli.
"""

import base64
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- AYARLAR --
# (kısa_ad, sekme_etiketi, dosya_adı)
PANELS = [
    ("diib",     "DİİB Analiz",                "diib_takip.html"),
    ("maliyet",  "Satınalma",                  "satinalma_maliyet.html"),
    ("ihracat",  "İhracat ve Navlun Analiz",   "ihracat_navlun.html"),
    ("tev",      "TEV Tablosu Oluşturma",      "tev_tablosu.html"),
    ("diibtool", "Mal Tanımı Düzenleyici",     "diib_tool.html"),
    ("stok",     "Hammadde Stok Takip",        "hammadde_stok.html"),
]

# Sekmelerin üzerine gelindiğinde görünecek arka plan renkleri (sırayla).
TAB_RENK = ["#2E9E57", "#C9832B", "#3F7FD1", "#9B59B6", "#D2603C", "#1F8A8A"]

# Panel içinde yapılacak küçük düzeltmeler. Kaynak dosyalara dokunulmaz;
# birleşik panelde çalışırken uygulanır.
#   baslik : (CSS seçici, yeni metin)  -> panelin kendi başlığı
#   gizle  : CSS seçiciler             -> birleşik panelde gereksiz düğmeler
#   gizleUst: seçicisi verilen öğenin ÜST kutusu gizlenir (etiket + açılır liste)
# Ortak tipografi. Beş panel farklı yazı tipi ve farklı taban punto
# kullanıyordu (Segoe UI 12,5 / Source Sans 14,5 / Plex Sans 13,5 ve 15).
# Hepsi IBM Plex Sans + IBM Plex Mono'ya ve aynı algılanan boyuta çekilir.
TIPO_ORTAK = """
  :root{
    --sans:'IBM Plex Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
    --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  }
  html,body{font-family:var(--sans)}
  body{-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
       text-rendering:optimizeLegibility}
  button,input,select,textarea,th,td,table{font-family:inherit}
  .mono,code,pre,kbd,samp,[class*="mono"]{font-family:var(--mono)}
  table{font-variant-numeric:tabular-nums}

  /* --- kolon genişlikleri ---
     Başlıklar tek satırda kalır; sığmazsa üç nokta ile kısalır, yan hücreye
     taşmaz. Yatay kayabilen kapsayıcılardaki tablolar içeriğinin altına
     sıkıştırılmaz: kolon daralacağına tablo kayar.                        */
  th{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  td{overflow-wrap:break-word}
  [class*="scroll"]>table,[class*="Sar"]>table,.tscroll table{min-width:min-content}
"""

PANEL_AYAR = {
    "diib": {
        # taban 12,5px — büyütülür; yükseklikleri ekrana göre verilmiş
        # kutular aynı oranda küçültülür ki taşma olmasın
        "tipo": """
  body{zoom:1.08;font-family:'IBM Plex Sans',system-ui,sans-serif}
  .ithSar{max-height:calc((100vh - 210px)/1.08) !important}
  .senKart{max-height:85vh !important}
  .ithEklePanel{max-height:64vh !important}
  [style*="max-height:70vh"]{max-height:64vh !important}
  [style*="max-height:52vh"]{max-height:48vh !important}
""",
        "baslik": (".markaYazi h1", "DİİB Analiz"),
        "gizle": "#indirBtn,#yukleBtn,#metinBtn,#klasorBtn",
        "gizleUst": "#temaSec",
    },
    "maliyet": {
        # kendi ölçek değişkeni var; zoom yerine onu kullanmak güvenli
        "tipo": ":root{--fs:0.93}",
        "baslik": (".brand h1", "Satınalma"),
    },
    "tev":      { "tipo": "body{zoom:0.90}" },      # taban 15px
    "diibtool": { "tipo": "body{zoom:0.96}" },      # taban 14px
    "stok": {
        # taban 14px, kendi yazı tipi Barlow — ortak ölçüye çekilir
        "tipo": "body{zoom:0.96}",
        "baslik": ("header h1", "Hammadde Stok Takip"),
    },
    "ihracat": {
        # taban 13,5px — ortak ölçü bu, dokunulmuyor
        "tipo": "",
        "baslik": (".brand b", "İhracat ve Navlun Analiz"),
    },
}

OUTPUT = "birlesik_panel.html"
BASLIK = "Dış Ticaret Operasyon Paneli"

# Her panelin localStorage anahtarlarını kendi önekine hapseder.
# Paneller aynı anahtar adını kullanıyorsa (ör. "data", "rows") bunu True bırak.
PREFIX_STORAGE = True
# ---------------------------------------------------------------------------


LOGO = """<svg class="logo" role="img" aria-label="Filidea" viewBox="0 0 48 50" aria-hidden="true" fill="none" stroke="currentColor" stroke-linecap="round"><path d="M6.60 9.64A18.20 5.46 0 1 0 42.20 9.64" stroke-width="2.15"/><path d="M9.78 17.65A15.60 4.68 0 1 0 39.39 15.44" stroke-width="2.15"/><path d="M13.32 24.69A12.90 3.87 0 1 0 35.60 21.13" stroke-width="2.0"/><path d="M16.60 30.78A10.20 3.06 0 1 0 31.43 26.77" stroke-width="2.0"/><path d="M19.19 35.89A7.50 2.25 0 1 0 27.40 32.24" stroke-width="1.85"/><path d="M20.82 40.16A4.90 1.47 0 1 0 24.10 37.45" stroke-width="1.85"/><path d="M21.3 41.2C20.6 44.6 19.3 46.6 17.2 47.6" stroke-width="1.8"/></svg>"""


STORAGE_SHIM = """<script>
/* birlestir.py: panel deposu
   Panelin localStorage'ı üst çerçevedeki ortak depoya bağlanır.
   Kazancı iki tane:
     1) Anahtarlar panel önekiyle ayrılır, paneller birbirinin verisini ezmez.
     2) Tarayıcının ~5 MB localStorage sınırı ortadan kalkar; depo üst
        çerçevenin IndexedDB'sinde tutulur, oradan tek dosyaya yazılır.
   Panellerin kendi klasör kaydı kapatılır: kayıt tek yerden yapılır. */
(function () {
  var P = "__PREFIX__:";
  var api = null;
  try { api = window.parent && window.parent.__panelDepo ? window.parent.__panelDepo : null; } catch (e) {}
  var bellek = api ? api.oku(P) : {};
  var sahip = function (k) { return Object.prototype.hasOwnProperty.call(bellek, k); };
  function ilet(k, v) { if (api) api.yaz(P + k, v); }

  var yontem = {
    getItem: function (k) { return sahip(String(k)) ? bellek[String(k)] : null; },
    setItem: function (k, v) { bellek[String(k)] = String(v); ilet(String(k), String(v)); },
    removeItem: function (k) { delete bellek[String(k)]; ilet(String(k), null); },
    key: function (i) { var ks = Object.keys(bellek); return i < ks.length ? ks[i] : null; },
    clear: function () { Object.keys(bellek).forEach(function (k) { delete bellek[k]; ilet(k, null); }); }
  };

  try {
    var shim = new Proxy({}, {
      get: function (t, prop) {
        if (prop === "length") return Object.keys(bellek).length;
        if (yontem[prop]) return yontem[prop];
        if (typeof prop !== "string") return undefined;
        return sahip(prop) ? bellek[prop] : undefined;
      },
      set: function (t, prop, val) { yontem.setItem(prop, val); return true; },
      deleteProperty: function (t, prop) { yontem.removeItem(prop); return true; },
      has: function (t, prop) { return sahip(String(prop)); },
      ownKeys: function () { return Object.keys(bellek); },
      getOwnPropertyDescriptor: function () { return { enumerable: true, configurable: true }; }
    });
    Object.defineProperty(window, "localStorage", { value: shim, configurable: true });
  } catch (e) { /* depo kurulamadı, panel kendi localStorage'ı ile devam eder */ }

  /* Panellerin kendi klasör kaydı ve kendi IndexedDB'leri devre dışı.
     Böylece bütün yazmalar ortak depodan geçer; tek bir hücre değişse bile
     üst çerçeve haberdar olur ve anında kaydeder. */
  try { Object.defineProperty(window, "showDirectoryPicker", { value: undefined, configurable: true }); } catch (e) {}
  try { Object.defineProperty(window, "indexedDB", { value: undefined, configurable: true }); } catch (e) {}
  function stilEkle() {
    try {
      var st = document.createElement("style");
      /* kaldırılanlar: klasör rozetleri ve panellerin kendi "kayıt bekliyor"
         göstergeleri — kayıt artık üst çubuktan tek yerden bildiriliyor */
      st.textContent = "#fsBtn,.klsPill,#kayitDurum{display:none !important}"
        + "#statBar > span:nth-child(2){display:none !important}"
        /* logo üst çubukta tek sefer görünür, panellerde tekrarlanmaz */
        + ".brand .logo,.markaLogo,.markaCizgi{display:none !important}"
        + "__GIZLE__";
      (document.head || document.documentElement || document.body).appendChild(st);
    } catch (e) {}
  }
  if (document.head || document.documentElement) stilEkle();
  else document.addEventListener("DOMContentLoaded", stilEkle);

  /* Ortak tipografi: yazı tipi dosyaları yüklenir, kurallar panelin kendi
     stillerinden SONRA eklenir ki onları ezebilsin. */
  function tipoEkle() {
    try {
      var h = document.head || document.documentElement;
      if (!h || h.querySelector("style[data-tipo]")) return;
      var l1 = document.createElement("link");
      l1.rel = "stylesheet";
      l1.href = "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700"
              + "&family=IBM+Plex+Mono:wght@400;500;600&display=swap";
      h.appendChild(l1);
      var st = document.createElement("style");
      st.setAttribute("data-tipo", "1");
      st.textContent = __TIPO__;
      h.appendChild(st);
    } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", tipoEkle);
  else tipoEkle();
  setTimeout(tipoEkle, 600);

  /* "Değişiklikleriniz kaybolabilir" uyarısı engellenir.
     Paneller bu uyarıyı kendi klasör kayıtları için koymuştu; kayıt artık
     üst çubuktan otomatik yapıldığı için uyarının bir karşılığı yok. */
  try {
    var ekle = window.addEventListener.bind(window);
    window.addEventListener = function (tur, fn, ops) {
      if (String(tur).toLowerCase() === "beforeunload") return;
      return ekle(tur, fn, ops);
    };
    Object.defineProperty(window, "onbeforeunload", {
      get: function () { return null; }, set: function () {}, configurable: true
    });
  } catch (e) {}

  /* panele özel düzeltmeler (başlık, gereksiz düğmeler) */
  function ayarla() {
    try {
      var A = __AYAR__;
      if (A.baslik) {
        var h = document.querySelector(A.baslik[0]);
        if (h) h.textContent = A.baslik[1];
      }
      if (A.gizleUst) {
        var e = document.querySelector(A.gizleUst);
        if (e && e.parentElement) e.parentElement.style.display = "none";
      }
    } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ayarla);
  else ayarla();
  setTimeout(ayarla, 1200);   // panel başlığını sonradan çiziyorsa
})();
</script>
"""


DEPO_JS = """<script>
/* ==========================================================================
   Ortak panel deposu.
   Bütün panellerin localStorage yazmaları buraya düşer. Bellekte tek bir
   nesne tutulur, değişiklikler gecikmeli olarak IndexedDB'ye yazılır.
   Böylece 5 MB sınırı yok ve bütün veri tek yerden okunabiliyor.
   ========================================================================== */
(function () {
  var DEPO = {}, zaman = null, kirli = false;

  function db() {
    return new Promise(function (res, rej) {
      var q = indexedDB.open("panelDepo", 1);
      q.onupgradeneeded = function () {
        if (!q.result.objectStoreNames.contains("kv")) q.result.createObjectStore("kv");
      };
      q.onsuccess = function () { res(q.result); };
      q.onerror = function () { rej(q.error); };
    });
  }
  function diskeYaz() {
    kirli = false;
    return db().then(function (d) {
      return new Promise(function (res) {
        var t = d.transaction("kv", "readwrite");
        t.objectStore("kv").put(DEPO, "veri");
        t.oncomplete = function () { d.close(); res(true); };
        t.onerror = function () { d.close(); res(false); };
      });
    }).catch(function () { return false; });
  }
  function planla() {
    kirli = true;
    clearTimeout(zaman);
    zaman = setTimeout(diskeYaz, 1200);
    /* en ufak değişiklikte merkezi kayıt tetiklenir */
    try {
      window.__depoBekleyen = true;
      if (window.__panelDegisti) window.__panelDegisti();
    } catch (e) {}
  }
  function diskten() {
    return db().then(function (d) {
      return new Promise(function (res) {
        var r = d.transaction("kv", "readonly").objectStore("kv").get("veri");
        r.onsuccess = function () { d.close(); res(r.result || {}); };
        r.onerror = function () { d.close(); res({}); };
      });
    }).catch(function () { return {}; });
  }

  window.__panelDepo = {
    oku: function (P) {
      var o = {};
      Object.keys(DEPO).forEach(function (k) { if (k.indexOf(P) === 0) o[k.slice(P.length)] = DEPO[k]; });
      return o;
    },
    yaz: function (k, v) { if (v === null) delete DEPO[k]; else DEPO[k] = String(v); planla(); },
    tumu: function () { return DEPO; },
    yukle: function (o) { DEPO = o || {}; return diskeYaz(); },
    bekle: function () { return kirli ? diskeYaz() : Promise.resolve(true); }
  };

  /* açılış: depoyu yükle, eski sürümde gerçek localStorage'a yazılmış
     önekli veriler varsa bir kereye mahsus içeri al */
  window.__depoHazir = diskten().then(function (o) {
    DEPO = o;
    if (!Object.keys(DEPO).length) {
      try {
        for (var i = 0; i < localStorage.length; i++) {
          var k = localStorage.key(i);
          if (k && k !== "__panel_aktif" && k.indexOf(":") > 0) DEPO[k] = localStorage.getItem(k);
        }
        if (Object.keys(DEPO).length) diskeYaz();
      } catch (e) {}
    }
    return tasi();
  });

  /* Satınalma Maliyet paneli eskiden kendi IndexedDB'sine yazıyordu.
     Artık ortak depoyu kullanıyor; eski kayıtlar bir kereye mahsus taşınır. */
  function tasi() {
    var varMi = Object.keys(DEPO).some(function (k) { return k.indexOf("maliyet:") === 0; });
    if (varMi || !window.indexedDB) return Promise.resolve(true);
    return new Promise(function (res) {
      var q;
      try { q = indexedDB.open("alimPanel"); } catch (e) { res(true); return; }
      q.onerror = function () { res(true); };
      q.onsuccess = function () {
        var d = q.result;
        if (!d.objectStoreNames.contains("kv")) { d.close(); res(true); return; }
        var s = d.transaction("kv", "readonly").objectStore("kv");
        var rv = s.getAll(), rk = s.getAllKeys(), biten = 0;
        var tamam = function () {
          if (++biten < 2) return;
          rk.result.forEach(function (k, i) {
            var v = rv.result[i];
            if (typeof v === "string") DEPO["maliyet:" + k] = v;
          });
          d.close();
          (Object.keys(DEPO).length ? diskeYaz() : Promise.resolve()).then(function () { res(true); });
        };
        rv.onsuccess = tamam; rk.onsuccess = tamam;
        rv.onerror = function () { d.close(); res(true); };
      };
    });
  }

  window.addEventListener("beforeunload", function () { if (kirli) diskeYaz(); });
})();
</script>
"""


KAYIT_UI = """  <button class="icon-btn" id="kayitKlasor" title="Verilerin yazılacağı klasörü seç">Klasör</button>
  <button class="icon-btn" id="kayitDegis" title="Başka bir klasör seç" style="display:none">değiştir</button>
  <button class="icon-btn" id="kayitTum" title="Bütün panellerin verisini tek dosyaya yaz">Kaydet</button>
  <button class="icon-btn" id="kayitGeri" title="Kayıt dosyasından bütün panelleri geri yükle">Geri yükle</button>
  <span id="kayitDurum" style="font-size:11px;color:#9fb3c8;margin-left:10px;white-space:nowrap"></span>
  <input type="file" id="kayitDosya" accept=".json,application/json" style="display:none">"""


KAYIT_JS = """<script>
/* ==========================================================================
   Merkezi kayıt: bütün panellerin verisi TEK dosyada toplanır.
   Panellerin kendi klasör kaydına gerek kalmaz.

   Nerede duruyor:
     - localStorage  -> panel önekleriyle (maliyet:, diib:, tev: ...)
     - IndexedDB     -> maliyet panelinin "alimPanel" veritabanı gibi
   İkisi de aynı kökene ait olduğu için üst çerçeveden okunabiliyor.
   Klasör tutamacı taşınamaz (makineye özeldir), dosyaya yazılmaz.
   ========================================================================== */
(function () {
  var DOSYA = "dis-ticaret-panel-verileri.json";
  var FSA = (typeof window.showDirectoryPicker === "function");
  var kok = null, sonImza = "", calisiyor = false;
  var durum = document.getElementById("kayitDurum");

  function yaz(t, renk) { durum.textContent = t; durum.style.color = renk || "#9fb3c8"; }
  function saat() { return new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }); }

  /* ---------- klasör tutamacı (üst çerçevenin kendi IndexedDB'si) ---------- */
  function kokDB() {
    return new Promise(function (res, rej) {
      var q = indexedDB.open("panelKok", 1);
      q.onupgradeneeded = function () {
        if (!q.result.objectStoreNames.contains("h")) q.result.createObjectStore("h");
      };
      q.onsuccess = function () { res(q.result); };
      q.onerror = function () { rej(q.error); };
    });
  }
  function kokYaz(h) {
    return kokDB().then(function (db) {
      return new Promise(function (res) {
        var t = db.transaction("h", "readwrite");
        t.objectStore("h").put(h, "kok");
        t.oncomplete = function () { db.close(); res(); };
        t.onerror = function () { db.close(); res(); };
      });
    }).catch(function () {});
  }
  function kokOku() {
    return kokDB().then(function (db) {
      return new Promise(function (res) {
        var r = db.transaction("h", "readonly").objectStore("h").get("kok");
        r.onsuccess = function () { db.close(); res(r.result || null); };
        r.onerror = function () { db.close(); res(null); };
      });
    }).catch(function () { return null; });
  }
  function izin(h, istekle) {
    if (!h) return Promise.resolve(false);
    var o = { mode: "readwrite" };
    return h.queryPermission(o).then(function (d) {
      if (d === "granted") return true;
      if (!istekle) return false;
      return h.requestPermission(o).then(function (d2) { return d2 === "granted"; });
    }).catch(function () { return false; });
  }

  /* ---------- veri toplama ---------- */
  function lsTopla() {
    var o = {};
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      if (k && k !== "__panel_aktif") o[k] = localStorage.getItem(k);
    }
    return o;
  }
  function tasinabilir(v) {
    if (v === null || typeof v !== "object") return true;
    if (typeof v.queryPermission === "function") return false;   // klasör/dosya tutamacı
    if (typeof Blob !== "undefined" && v instanceof Blob) return false;
    try { JSON.stringify(v); return true; } catch (e) { return false; }
  }
  function dbAc(ad, surum) {
    return new Promise(function (res, rej) {
      var q = surum ? indexedDB.open(ad, surum) : indexedDB.open(ad);
      q.onsuccess = function () { res(q.result); };
      q.onerror = function () { rej(q.error); };
      q.onblocked = function () { rej(new Error("kilitli")); };
    });
  }
  function idbTopla() {
    if (!window.indexedDB || !indexedDB.databases) return Promise.resolve({});
    return indexedDB.databases().then(function (liste) {
      var cikti = {}, zincir = Promise.resolve();
      liste.forEach(function (d) {
        if (!d.name || d.name === "panelKok") return;
        zincir = zincir.then(function () {
          return dbAc(d.name).then(function (db) {
            var adlar = [].slice.call(db.objectStoreNames);
            if (!adlar.length) { db.close(); return; }
            return new Promise(function (res) {
              var st = {}, kalan = adlar.length;
              var tx = db.transaction(adlar, "readonly");
              adlar.forEach(function (ad) {
                var s = tx.objectStore(ad), kp = s.keyPath;
                /* iki istek de hemen açılır; dinleyiciler sonradan bağlanırsa
                   erken biten isteğin olayı kaçar ve kayıt hiç bitmez. */
                var rv = s.getAll(), rk = s.getAllKeys(), bitenler = 0;
                var tamam = function () {
                  if (++bitenler < 2) return;
                  var kayit = [];
                  rv.result.forEach(function (v, i) {
                    if (tasinabilir(v)) kayit.push({ k: rk.result[i], v: v });
                  });
                  st[ad] = { keyPath: kp || null, kayit: kayit };
                  if (--kalan === 0) {
                    cikti[d.name] = { surum: db.version, store: st };
                    db.close(); res();
                  }
                };
                rv.onsuccess = tamam; rk.onsuccess = tamam;
              });
              tx.onerror = function () { db.close(); res(); };
            });
          }).catch(function () {});
        });
      });
      return zincir.then(function () { return cikti; });
    }).catch(function () { return {}; });
  }
  function depoTumu() { return window.__panelDepo ? window.__panelDepo.tumu() : {}; }
  function anlikGoruntu() {
    return idbTopla().then(function (idb) {
      return { surum: 2, tarih: new Date().toISOString(),
               depo: depoTumu(), ls: lsTopla(), idb: idb };
    });
  }

  /* ---------- veri geri yazma ---------- */
  function lsGeri(o) {
    Object.keys(lsTopla()).forEach(function (k) { localStorage.removeItem(k); });
    Object.keys(o || {}).forEach(function (k) { try { localStorage.setItem(k, o[k]); } catch (e) {} });
  }
  function idbGeri(veri) {
    var zincir = Promise.resolve();
    Object.keys(veri || {}).forEach(function (ad) {
      zincir = zincir.then(function () {
        var bilgi = veri[ad], stAdlar = Object.keys(bilgi.store || {});
        return dbAc(ad).then(function (db) {
          var eksik = stAdlar.filter(function (s) { return !db.objectStoreNames.contains(s); });
          if (!eksik.length) return db;
          var v = db.version + 1; db.close();
          return dbAc2(ad, v, bilgi, eksik);
        }).then(function (db) {
          var hedef = stAdlar.filter(function (s) { return db.objectStoreNames.contains(s); });
          if (!hedef.length) { db.close(); return; }
          return new Promise(function (res) {
            var tx = db.transaction(hedef, "readwrite");
            hedef.forEach(function (s) {
              var o = tx.objectStore(s);
              (bilgi.store[s].kayit || []).forEach(function (r) {
                try { o.keyPath ? o.put(r.v) : o.put(r.v, r.k); } catch (e) {}
              });
            });
            tx.oncomplete = function () { db.close(); res(); };
            tx.onerror = function () { db.close(); res(); };
          });
        }).catch(function () {});
      });
    });
    return zincir;
  }
  function dbAc2(ad, surum, bilgi, eksik) {
    return new Promise(function (res, rej) {
      var q = indexedDB.open(ad, surum);
      q.onupgradeneeded = function () {
        var db = q.result;
        eksik.forEach(function (s) {
          var kp = bilgi.store[s].keyPath;
          if (!db.objectStoreNames.contains(s)) db.createObjectStore(s, kp ? { keyPath: kp } : undefined);
        });
      };
      q.onsuccess = function () { res(q.result); };
      q.onerror = function () { rej(q.error); };
    });
  }

  /* ---------- dosyaya yaz / dosyadan oku ---------- */
  function dosyayaYaz(metin, elle) {
    return izin(kok, !!elle).then(function (ok) {
      if (!ok) return false;
      return kok.getFileHandle(DOSYA, { create: true })
        .then(function (fh) { return fh.createWritable(); })
        .then(function (w) { return w.write(metin).then(function () { return w.close(); }); })
        .then(function () { return true; });
    }).catch(function () { return false; });
  }
  function indir(metin) {
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([metin], { type: "application/json" }));
    a.download = DOSYA;
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
  }

  function kaydet(elle) {
    if (calisiyor) return Promise.resolve();
    calisiyor = true;
    var hazirla = window.__panelDepo ? window.__panelDepo.bekle() : Promise.resolve();
    return hazirla.then(anlikGoruntu).then(function (g) {
      var metin = JSON.stringify(g);
      if (!elle && metin.length === sonImza.length && metin === sonImza) {
        calisiyor = false;
        if (kok) yaz("kaydedildi " + saat(), "#9ad29a");
        return;
      }
      return dosyayaYaz(metin, elle).then(function (oldu) {
        if (oldu) { sonImza = metin; yaz("kaydedildi " + saat(), "#9ad29a"); }
        else if (elle) { indir(metin); sonImza = metin; yaz("dosya indirildi " + saat(), "#9ad29a"); }
        else { yaz("kayıt klasörü seçilmedi", "#ffb547"); }
        calisiyor = false;
      });
    }).catch(function (e) {
      calisiyor = false; yaz("kayıt başarısız", "#ff9b9b");
    });
  }

  function geriYukle(metin) {
    var g;
    try { g = JSON.parse(metin); } catch (e) { yaz("dosya okunamadı", "#ff9b9b"); return; }
    if (!g || (!g.ls && !g.depo)) { yaz("dosya tanınmadı", "#ff9b9b"); return; }
    if (!confirm("Kayıt dosyasındaki veriler bütün panellere yazılacak ve sayfa yenilenecek.\\n" +
                 "Şu anki veriler değiştirilecek. Devam edilsin mi?")) return;
    lsGeri(g.ls);
    var depoIs = window.__panelDepo ? window.__panelDepo.yukle(g.depo || {}) : Promise.resolve();
    depoIs.then(function () { return idbGeri(g.idb); }).then(function () { location.reload(); });
  }

  /* ---------- düğmeler ---------- */
  /* Klasör tutamacı tarayıcıda saklanır ve kapatıp açınca da durur; sıfırlanan
     şey yalnızca yazma iznidir. Bu yüzden düğme önce izni tazelemeyi dener,
     klasör seçtirmez. Klasörü değiştirmek isteyen "değiştir"e basar. */
  var btnKlasor = document.getElementById("kayitKlasor");
  var btnDegis = document.getElementById("kayitDegis");
  function klasorGoster() {
    if (kok) { btnKlasor.textContent = "📁 " + (kok.name || "seçili");
               btnKlasor.title = "Tıklayın: yazma iznini tazele";
               btnDegis.style.display = ""; }
    else { btnKlasor.textContent = "Klasör";
           btnKlasor.title = "Verilerin yazılacağı klasörü seç";
           btnDegis.style.display = "none"; }
  }
  function klasorSec() {
    if (!FSA) { yaz("tarayıcı klasör yazmayı desteklemiyor", "#ffb547"); return; }
    window.showDirectoryPicker({ id: "operasyonPaneli", mode: "readwrite", startIn: "documents" })
      .then(function (h) { kok = h; klasorGoster(); return kokYaz(h); })
      .then(function () { yaz("klasör seçildi", "#9ad29a"); return kaydet(true); })
      .catch(function () {});
  }
  btnKlasor.addEventListener("click", function () {
    if (!kok) { klasorSec(); return; }
    izin(kok, true).then(function (ok) {
      if (ok) { yaz("kayıt klasörü hazır", "#9ad29a"); kaydet(true); }
      else klasorSec();                       // izin verilmediyse yeniden seçtir
    });
  });
  btnDegis.addEventListener("click", klasorSec);
  document.getElementById("kayitTum").addEventListener("click", function () {
    if (FSA && !kok) {
      yaz("önce kayıt klasörünü seçin", "#ffb547");
      return;
    }
    yaz("kaydediliyor…");
    kaydet(true);
  });
  document.getElementById("kayitGeri").addEventListener("click", function () {
    if (kok) {
      izin(kok, true).then(function (ok) {
        if (!ok) { document.getElementById("kayitDosya").click(); return; }
        kok.getFileHandle(DOSYA).then(function (fh) { return fh.getFile(); })
          .then(function (f) { return f.text(); })
          .then(geriYukle)
          .catch(function () { document.getElementById("kayitDosya").click(); });
      });
    } else {
      document.getElementById("kayitDosya").click();
    }
  });
  document.getElementById("kayitDosya").addEventListener("change", function (e) {
    var f = e.target.files[0];
    if (f) f.text().then(geriYukle);
    e.target.value = "";
  });

  /* ---------- açılış ve otomatik kayıt ---------- */
  kokOku().then(function (h) {
    klasorGoster();
    if (!h) { yaz(FSA ? "kayıt klasörü seçilmedi" : "kayıt: dosya indirme", "#ffb547"); return; }
    kok = h; klasorGoster();
    return izin(h, false).then(function (ok) {
      if (ok) { yaz("kayıt klasörü hazır", "#9ad29a"); return; }
      yaz("klasör izni bekleniyor — sayfaya bir kez tıklayın", "#ffb547");
      /* Tarayıcı yazma iznini ancak kullanıcı bir şeye tıkladıktan sonra
         sorabiliyor. İlk tıklamada izin bir kez istenir, sonra kendiliğinden
         yürür; klasörü yeniden seçmeye gerek kalmaz. */
      var birKez = function () {
        document.removeEventListener("click", birKez, true);
        izin(kok, true).then(function (ok2) {
          yaz(ok2 ? "kayıt klasörü hazır" : "klasör izni verilmedi", ok2 ? "#9ad29a" : "#ffb547");
          if (ok2) kaydet(false);
        });
      };
      document.addEventListener("click", birKez, true);
    });
  });

  /* Paneller veriyi kendi içinde yazıyor; değişiklik olup olmadığı anlık
     görüntü karşılaştırılarak anlaşılır. Değişmediyse dosyaya dokunulmaz. */
  /* Panellerden gelen her değişiklik burada toplanır. Art arda yazmalarda
     dosya her tuşta açılmasın diye 1,5 saniye beklenir. */
  var degisTimer = null;
  window.__panelDegisti = function () {
    if (!kok) { yaz(FSA ? "kaydedilmedi — klasör seçilmedi" : "değişiklik var — Tümünü kaydet", "#ffb547"); return; }
    yaz("değişiklik var…", "#ffd27a");
    clearTimeout(degisTimer);
    degisTimer = setTimeout(function () {
      yaz("kaydediliyor…", "#ffd27a");
      kaydet(false);
    }, 1500);
  };
  /* kayıt katmanı yüklenmeden önce yapılmış değişiklik varsa yakalanır */
  if (window.__depoBekleyen) setTimeout(function () { window.__panelDegisti(); }, 2000);
  setInterval(function () { if (kok) kaydet(false); }, 300000);
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden" && kok) kaydet(false);
  });
  window.kayitKaydet = kaydet;
})();
</script>"""


def oku(path: Path) -> str:
    """Paneli metin olarak oku (utf-8, olmazsa windows-1254)."""
    ham = path.read_bytes()
    for enc in ("utf-8", "windows-1254", "latin-1"):
        try:
            return ham.decode(enc)
        except UnicodeDecodeError:
            continue
    return ham.decode("utf-8", errors="replace")


def shim_ekle(html: str, kisa_ad: str) -> str:
    """localStorage önek shim'ini panelin en başına, kendi script'lerinden önce koy."""
    if not PREFIX_STORAGE:
        return html
    import json
    ayar = PANEL_AYAR.get(kisa_ad, {})
    gizle = ayar.get("gizle", "")
    shim = (STORAGE_SHIM
            .replace("__PREFIX__", kisa_ad)
            .replace("__AYAR__", json.dumps(ayar, ensure_ascii=False))
            .replace("__GIZLE__", (gizle + "{display:none !important}") if gizle else "")
            .replace("__TIPO__", json.dumps(TIPO_ORTAK + ayar.get("tipo", ""), ensure_ascii=False)))
    # Gerçek <head> etiketi aranır. Düz metin araması yapılırsa JavaScript
    # içindeki "j<head.length" gibi ifadeler head sanılıp shim betiğin
    # ortasına girer ve panel bozulur.
    m = re.search(r"<head(?:\s[^>]*)?>", html, re.I)
    if m:
        return html[: m.end()] + "\n" + shim + html[m.end() :]
    # head yoksa (parça hâlindeki paneller) en başa konur; panelin kendi
    # betiklerinden önce çalışması yeterlidir.
    return shim + html


def main() -> int:
    klasor = Path(__file__).resolve().parent
    bulunan, eksik = [], []

    for kisa_ad, etiket, dosya in PANELS:
        p = klasor / dosya
        if not p.is_file():
            eksik.append(dosya)
            continue
        html = shim_ekle(oku(p), kisa_ad)
        b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")
        bulunan.append((kisa_ad, etiket, dosya, b64, p.stat().st_size))
        print(f"  + {etiket:<20} {dosya}  ({p.stat().st_size/1024:.0f} KB)")

    if eksik:
        print("\n  ! Bulunamayan dosyalar:")
        for d in eksik:
            print(f"      {d}")
        mevcut = sorted(x.name for x in klasor.glob("*.html") if x.name != OUTPUT)
        if mevcut:
            print("    Klasördeki HTML dosyaları:")
            for m in mevcut:
                print(f"      {m}")
        print("    -> PANELS listesindeki dosya adlarını bunlara göre düzelt.")

    if not bulunan:
        print("\nHiç panel bulunamadı, çıktı üretilmedi.")
        return 1

    sekmeler = "\n".join(
        f'    <button class="tab" data-panel="{k}">{e}</button>'
        for k, e, _, _, _ in bulunan
    )
    kaynaklar = "\n".join(
        f'<script type="text/plain" id="src-{k}">{b}</script>'
        for k, _, _, b, _ in bulunan
    )

    renkler = "\n".join(
        f'  .tab[data-panel="{k}"]:hover {{ background: {TAB_RENK[i % len(TAB_RENK)]}; }}'
        for i, (k, _, _, _, _) in enumerate(bulunan)
    )

    cikti = SABLON.format(
        baslik=BASLIK,
        sekmeler=sekmeler,
        kaynaklar=kaynaklar,
        depo_js=DEPO_JS,
        logo=LOGO,
        tab_renk=renkler,
        kayit_ui=KAYIT_UI,
        kayit_js=KAYIT_JS,
        ilk=bulunan[0][0],
    )

    hedef = klasor / OUTPUT
    hedef.write_text(cikti, encoding="utf-8")
    print(f"\n  ✓ {OUTPUT} oluşturuldu ({hedef.stat().st_size/1024:.0f} KB, "
          f"{len(bulunan)} panel)")
    return 0


SABLON = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{baslik}</title>
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ height: 100%; margin: 0; }}
  body {{
    display: flex; flex-direction: column;
    font: 14px/1.4 "Segoe UI", system-ui, sans-serif;
    background: #f1f3f6; color: #1b1f24;
  }}
  header {{
    flex: 0 0 auto; background: #1f3b57; color: #fff;
    padding: 0 14px; display: flex; align-items: center; gap: 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,.25); z-index: 2;
  }}
  header h1 {{ font-size: 14.5px; font-weight: 600; margin: 0; padding: 12px 0;
               white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .marka {{ display: flex; align-items: center; gap: 9px; flex: 0 1 auto; min-width: 0; }}
  .marka .logo {{ width: 24px; height: 25px; color: #4fc27e; flex: 0 0 auto; }}
  /* Sekmeler daralarak sığar; başlık çubuğunda kaydırma çubuğu çıkmaz. */
  nav {{ display: flex; gap: 1px; flex: 1 1 auto; min-width: 0; overflow: hidden; }}
  .tab {{
    background: transparent; border: 0; border-bottom: 3px solid transparent;
    color: #c7d6e4; font: inherit; font-size: 13px; padding: 13px 12px 10px;
    cursor: pointer; white-space: nowrap; flex: 0 1 auto;
    min-width: 0; overflow: hidden; text-overflow: ellipsis;
  }}
  /* Pencere daraldıkça önce başlık, sonra durum yazısı, sonra logo çekilir;
     sekmeler en son ve en az kısılır.                                     */
  @media (max-width: 1500px) {{
    .tab {{ padding: 13px 9px 10px; font-size: 12.5px; }}
    .icon-btn {{ padding: 4px 8px; margin-left: 6px; }}
  }}
  @media (max-width: 1320px) {{ header h1 {{ display: none; }} }}
  @media (max-width: 1150px) {{ #kayitDurum {{ display: none; }} }}
  @media (max-width: 1000px) {{
    .marka .logo {{ display: none; }}
    .tab {{ padding: 13px 7px 10px; font-size: 12px; }}
  }}
  .tab:hover {{ color: #fff; }}
{tab_renk}
  .tab.active {{ color: #fff; border-bottom-color: #ffb547; font-weight: 600; }}
  .spacer {{ margin-left: auto; }}
  .icon-btn {{
    background: transparent; border: 1px solid rgba(255,255,255,.3); color: #c7d6e4;
    border-radius: 4px; font: inherit; font-size: 12px; padding: 4px 10px;
    cursor: pointer; margin-left: 8px;
  }}
  .icon-btn:hover {{ color: #fff; border-color: #fff; }}
  main {{ flex: 1 1 auto; position: relative; }}
  iframe {{
    position: absolute; inset: 0; width: 100%; height: 100%;
    border: 0; background: #fff; display: none;
  }}
  iframe.active {{ display: block; }}
  #bos {{
    position: absolute; inset: 0; display: grid; place-items: center; color: #7a8796;
  }}
</style>
</head>
<body>

<header>
  <span class="marka">{logo}<h1>{baslik}</h1></span>
  <nav id="nav">
{sekmeler}
  </nav>
  <span class="spacer"></span>
{kayit_ui}
  <button class="icon-btn" id="reload" title="Aktif paneli sıfırdan yükle">Yenile</button>
</header>

<main id="main"><div id="bos">Panel yükleniyor…</div></main>

{kaynaklar}

{depo_js}

<script>
(function () {{
  var main = document.getElementById("main");
  var bos = document.getElementById("bos");
  var yuklenen = {{}};
  var aktif = null;

  function coz(id) {{
    var b64 = document.getElementById("src-" + id).textContent.trim();
    var bytes = Uint8Array.from(atob(b64), function (c) {{ return c.charCodeAt(0); }});
    return new TextDecoder("utf-8").decode(bytes);
  }}

  function yukle(id) {{
    var f = document.createElement("iframe");
    f.id = "frame-" + id;
    main.appendChild(f);
    var d = f.contentDocument || f.contentWindow.document;
    d.open();
    d.write(coz(id));
    d.close();
    yuklenen[id] = f;
    return f;
  }}

  function goster(id) {{
    if (bos) {{ bos.style.display = "none"; }}
    Object.keys(yuklenen).forEach(function (k) {{
      yuklenen[k].classList.toggle("active", k === id);
    }});
    if (!yuklenen[id]) yukle(id).classList.add("active");
    [].forEach.call(document.querySelectorAll(".tab"), function (t) {{
      t.classList.toggle("active", t.dataset.panel === id);
    }});
    aktif = id;
    try {{ window.localStorage.setItem("__panel_aktif", id); }} catch (e) {{}}
  }}

  document.getElementById("nav").addEventListener("click", function (e) {{
    var t = e.target.closest(".tab");
    if (t) goster(t.dataset.panel);
  }});

  document.getElementById("reload").addEventListener("click", function () {{
    if (!aktif) return;
    if (yuklenen[aktif]) {{ yuklenen[aktif].remove(); delete yuklenen[aktif]; }}
    goster(aktif);
  }});

  var son = null;
  try {{ son = window.localStorage.getItem("__panel_aktif"); }} catch (e) {{}}
  var ilkId = son && document.getElementById("src-" + son) ? son : "{ilk}";
  /* paneller ancak depo belleğe alındıktan sonra açılır, yoksa boş okurlar */
  (window.__depoHazir || Promise.resolve()).then(function () {{ goster(ilkId); }});
}})();
</script>

{kayit_js}

</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
