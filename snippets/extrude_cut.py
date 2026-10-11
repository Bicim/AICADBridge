"""
Mevcut katı gövdeden malzeme kaldıran kesme (extrude-cut) örneği.

Ne yapar:
    - (DEMO) Önce üzerine kesim yapılacak bir plaka oluşturur,
    - XY düzleminde dikdörtgen bir kesme profili çizer,
    - profili CutFeatureOperation ile uzatarak plakadan malzeme kaldırır.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    PLATE_W_MM, PLATE_L_MM, PLATE_T_MM : demo plakanın en/boy/kalınlığı
    CUT_W_MM, CUT_L_MM                 : kesit penceresinin en/boyu
    CUT_D_MM                           : kesim derinliği (plakayı geçecek kadar)

Ne zaman kullanılır:
    - Yuva, pencere, oluk, kanal, cep (pocket) açma.
    - KRİTİK KURAL: Kesme profili mevcut gövdeyle fiziksel olarak
      kesişmek ZORUNDADIR; boşlukta CutFeatureOperation kullanmak
      "Kesilecek hedef gövde bulunamadı" hatasına yol açar.
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
PLATE_W_MM = 100.0
PLATE_L_MM = 60.0
PLATE_T_MM = 30.0
CUT_W_MM = 30.0
CUT_L_MM = 20.0
CUT_D_MM = 35.0  # plaka kalınlığını güvenle aşsın

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent
extrudes = rootComp.features.extrudeFeatures

# --- DEMO GÖVDE: plaka, XY düzleminden +Z yönünde uzatılmıştır ---
# (gerçek kullanımda kesim, mevcut gövdenin üzerine uygulanır)
plate_sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
plate_sketch.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create(-PLATE_W_MM / 2.0 / 10.0, -PLATE_L_MM / 2.0 / 10.0, 0),
    adsk.core.Point3D.create(PLATE_W_MM / 2.0 / 10.0, PLATE_L_MM / 2.0 / 10.0, 0))
plate_input = extrudes.createInput(plate_sketch.profiles.item(0),
                                   adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
plate_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(PLATE_T_MM / 10.0))
extrudes.add(plate_input)

# --- KESİM PROFİLİ: plakanın alt yüzeyi (XY düzlemi) üzerinde pencere ---
cut_sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
cut_sketch.name = 'CutProfile'
cut_sketch.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create(-CUT_W_MM / 2.0 / 10.0, -CUT_L_MM / 2.0 / 10.0, 0),
    adsk.core.Point3D.create(CUT_W_MM / 2.0 / 10.0, CUT_L_MM / 2.0 / 10.0, 0))

# CutFeatureOperation: profil gövdeyle kesiştiği için malzeme kaldırılır
cut_input = extrudes.createInput(cut_sketch.profiles.item(0),
                                 adsk.fusion.FeatureOperations.CutFeatureOperation)
cut_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(CUT_D_MM / 10.0))
extrudes.add(cut_input)
