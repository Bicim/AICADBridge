"""
Dikdörtgen eskizi çizer ve kesiti yeni bir katı gövde olarak uzatır (extrude).

Ne yapar:
    - XY düzleminde iki köşe noktası ile kapalı dikdörtgen çizer,
    - profili verilen yüksekliğe kadar uzatarak yeni bir kutu/prizma
      gövdesi (NewBodyFeatureOperation) oluşturur.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    X_MIN_MM, Y_MIN_MM : dikdörtgenin sol alt köşesi
    X_MAX_MM, Y_MAX_MM : dikdörtgenin sağ üst köşesi
    HEIGHT_MM          : uzatma (extrude) yüksekliği

Ne zaman kullanılır:
    - Plaka, tabla, kutu, pano, taban, ayak gibi prizmatik parçalar için
      temel şablondur.
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
X_MIN_MM = -50.0
Y_MIN_MM = -30.0
X_MAX_MM = 50.0
Y_MAX_MM = 30.0
HEIGHT_MM = 10.0

# mm -> cm dönüşümü (Fusion 360 API dahili uzunluk birimi cm'dir)
p1 = adsk.core.Point3D.create(X_MIN_MM / 10.0, Y_MIN_MM / 10.0, 0)
p2 = adsk.core.Point3D.create(X_MAX_MM / 10.0, Y_MAX_MM / 10.0, 0)
height_cm = HEIGHT_MM / 10.0

# ---- Kök bileşene erişim ----
app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent

# 1) XY düzleminde yeni eskiz oluştur
sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
sketch.name = 'RectProfile'

# 2) İki köşe noktası ile kapalı dikdörtgen çiz
sketch.sketchCurves.sketchLines.addTwoPointRectangle(p1, p2)

# 3) Kapalı profili yeni gövde olarak uzat
extrudes = rootComp.features.extrudeFeatures
prof = sketch.profiles.item(0)
ext_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(height_cm))
extrudes.add(ext_input)
