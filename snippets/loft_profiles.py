"""
Paralel kesitler arasında geçiş yüzeyi oluşturarak katı gövde üretir (loft).

Ne yapar:
    - XY düzleminde alt kesit çemberini çizer,
    - XY'den belirli yükseklikte ofsetli bir yapı düzlemi oluşturup
      üst kesit çemberini çizer,
    - iki kesit arasında loft yaparak yeni bir gövde üretir.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    BOTTOM_RADIUS_MM : alt kesit çemberinin yarıçapı
    TOP_RADIUS_MM    : üst kesit çemberinin yarıçapı
    HEIGHT_MM        : kesitler arasındaki mesafe (Z yönünde)

Ne zaman kullanılır:
    - Farklı kesitler arasında yumuşak geçiş gereken parçalar: koni benzeri
      organik formlar, hortum başlığı, eğimli kolon ("kesitler arası geçiş").
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
BOTTOM_RADIUS_MM = 15.0
TOP_RADIUS_MM = 8.0
HEIGHT_MM = 40.0

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent

# 1) ALT KESİT: XY düzleminde çember
bottom_sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
bottom_sketch.name = 'LoftBottom'
bottom_sketch.sketchCurves.sketchCircles.addByCenterRadius(
    adsk.core.Point3D.create(0, 0, 0), BOTTOM_RADIUS_MM / 10.0)

# 2) ÜST KESİT: XY'den HEIGHT_MM yukarıda ofsetli yapı düzleminde çember
planes = rootComp.constructionPlanes
plane_input = planes.createInput()
plane_input.setByOffset(rootComp.xYConstructionPlane,
                        adsk.core.ValueInput.createByReal(HEIGHT_MM / 10.0))
top_plane = planes.add(plane_input)

top_sketch = rootComp.sketches.add(top_plane)
top_sketch.name = 'LoftTop'
top_sketch.sketchCurves.sketchCircles.addByCenterRadius(
    adsk.core.Point3D.create(0, 0, 0), TOP_RADIUS_MM / 10.0)

# 3) LOFT: kesitleri sırayla ekle ve yeni gövde olarak oluştur
lofts = rootComp.features.loftFeatures
loft_input = lofts.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
loft_input.loftSections.add(bottom_sketch.profiles.item(0))
loft_input.loftSections.add(top_sketch.profiles.item(0))
lofts.add(loft_input)
