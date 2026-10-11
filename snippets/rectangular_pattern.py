"""
Unsur(lar)ı bir doğrultuda ızgara biçiminde çoğaltır (rectangular pattern).

Ne yapar:
    - (DEMO) Orijinde küçük bir dikdörtgen kolon unsuru oluşturur,
    - bu unsuru +X doğrultusunda istenen sayıda ve aralıkta tekrarlar.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    POST_W_MM, POST_L_MM, POST_H_MM : demo kolonun ölçüleri
    COUNT_X                          : 1. yöndeki tekrar sayısı
    SPACING_X_MM                     : 1. yöndeki adım aralığı (merkezden merkeze)

Ne zaman kullanılır:
    - Izgara delik/diş/kanatçık dizileri, paneller gibi
      "sırayla X tane ekle" isteklerinde.
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
POST_W_MM = 10.0
POST_L_MM = 10.0
POST_H_MM = 15.0
COUNT_X = 4
SPACING_X_MM = 20.0

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent
extrudes = rootComp.features.extrudeFeatures

# --- DEMO UNSUR: orijinde küçük kolon ---
post_sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
post_sketch.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create(-POST_W_MM / 2.0 / 10.0, -POST_L_MM / 2.0 / 10.0, 0),
    adsk.core.Point3D.create(POST_W_MM / 2.0 / 10.0, POST_L_MM / 2.0 / 10.0, 0))
post_input = extrudes.createInput(post_sketch.profiles.item(0),
                                  adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
post_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(POST_H_MM / 10.0))
post_feature = extrudes.add(post_input)

# --- Desenlenecek unsur(lar) ---
pattern_entities = adsk.core.ObjectCollection.create()
pattern_entities.add(post_feature)

# --- 1. yön doğrultusu: XY düzleminde +X yönlü eskiz doğrusu ---
dir_sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
dir_line = dir_sketch.sketchCurves.sketchLines.addByTwoPoints(
    adsk.core.Point3D.create(0, 0, 0),
    adsk.core.Point3D.create(1.0, 0, 0))

# --- Düzgün (ızgara) desen özelliği ---
rect_patterns = rootComp.features.rectangularPatternFeatures
# TODO: createInput yön parametresi olarak eskiz doğrusu kullanıldı; API sürümüne
# göre BRepEdge veya eksen de kabul edebilir, imza doğrulanmalı.
pattern_input = rect_patterns.createInput(pattern_entities, dir_line)
# TODO: distanceOne'ın adım aralığı (spacing) mi toplam mesafe mi olduğu ve
# patternDistanceType ayarı doğrulanmalı.
pattern_input.quantityOne = adsk.core.ValueInput.createByReal(COUNT_X)
pattern_input.distanceOne = adsk.core.ValueInput.createByReal(SPACING_X_MM / 10.0)
# İkinci yön (isteğe bağlı):
# pattern_input.quantityTwo = adsk.core.ValueInput.createByReal(COUNT_Y)
# pattern_input.distanceTwo = adsk.core.ValueInput.createByReal(SPACING_Y_MM / 10.0)
rect_patterns.add(pattern_input)
