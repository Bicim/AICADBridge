"""
Referans (yapı) düzlemi oluşturur ve üzerine eskiz çizer.

Ne yapar:
    - XY düzleminden verilen mesafede ofsetli bir yapı düzlemi
      (construction plane) oluşturur,
    - (DEMO) bu düzlem üzerine çember eskizi çizip yeni gövde olarak uzatır.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    OFFSET_MM     : XY düzleminden ofset mesafesi (+Z yönünde)
    CIRCLE_DIA_MM : örnek eskiz çemberinin çapı
    HEIGHT_MM     : örnek uzatma yüksekliği

Ne zaman kullanılır:
    - Gövdenin belirli bir yüksekliğinde yeni bir çalışma düzlemi gerekince:
      üst kat delikleri, montaj düzlemleri, loft kesitleri.
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
OFFSET_MM = 25.0
CIRCLE_DIA_MM = 20.0
HEIGHT_MM = 5.0

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent

# 1) Ofsetli yapı düzlemi oluştur
planes = rootComp.constructionPlanes
plane_input = planes.createInput()
plane_input.setByOffset(rootComp.xYConstructionPlane,
                        adsk.core.ValueInput.createByReal(OFFSET_MM / 10.0))
offset_plane = planes.add(plane_input)

# 2) (DEMO) Yeni düzlem üzerinde eskiz çiz ve uzat
sketch = rootComp.sketches.add(offset_plane)
sketch.name = 'OffsetPlaneSketch'
sketch.sketchCurves.sketchCircles.addByCenterRadius(
    adsk.core.Point3D.create(0, 0, 0), CIRCLE_DIA_MM / 2.0 / 10.0)

extrudes = rootComp.features.extrudeFeatures
ext_input = extrudes.createInput(sketch.profiles.item(0),
                                 adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(HEIGHT_MM / 10.0))
extrudes.add(ext_input)
