"""
Tasarıma kullanıcı parametreleri ekler ve değerlerini güvenle günceller.

Ne yapar:
    - 'genislik_mm' ve 'yukseklik_mm' adlarında iki kullanıcı parametresi
      oluşturur (mm cinsinden),
    - mevcut bir parametrenin değerini expression üzerinden günceller.

Parametreler (mm cinsinden):
    WIDTH_MM, HEIGHT_MM : oluşturulacak parametrelerin başlangıç değerleri

Ne zaman kullanılır:
    - Ölçüleri kod içinde sabit yazmak yerine parametrik yönetmek,
      sonradan "genişliği 60 yap" gibi istekleri güvenle uygulamak.
    - NOT: Tek başına katı gövde üretmez; modelleme snippet'leriyle birlikte
      kullanılır (parametre değerleri ValueInput olarak extrude/revolve vb.
      girdilerine verilebilir).

ÖNEMLİ: Fusion API dahili uzunluk birimi cm'dir; ValueInput.createByString
kullanmak birim dönüşümünü Fusion'a bıraktığı için en güvenli yoldur.
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
WIDTH_MM = 50.0
HEIGHT_MM = 20.0

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent

params = design.userParameters

# 1) Yeni parametre ekle: add(isim, değer, birim, açıklama)
# NOT: Aynı isimli parametre zaten varsa add hata verir; eklemeden önce
# itemByName ile kontrol etmek güvenlidir.
width_param = params.add(
    'genislik_mm',
    adsk.core.ValueInput.createByString('{:g} mm'.format(WIDTH_MM)),
    'mm',
    'Tabla genişliği')
height_param = params.add(
    'yukseklik_mm',
    adsk.core.ValueInput.createByString('{:g} mm'.format(HEIGHT_MM)),
    'mm',
    'Tabla yüksekliği')

# 2) Mevcut parametrenin değerini güncelle (birim güvenli yol: expression)
existing = params.itemByName('genislik_mm')
if existing:
    existing.expression = '60 mm'
