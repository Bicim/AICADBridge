"""
Çember eskizi çizer ve kesiti yeni bir katı gövde olarak uzatır (extrude).

Ne yapar:
    - XY düzleminde verilen merkez ve çapta bir çember eskizi çizer,
    - bu kapalı profili verilen yüksekliğe kadar uzatarak yeni bir
      silindirik katı gövde (NewBodyFeatureOperation) oluşturur.

Parametreler (mm cinsinden; Fusion API cm kullandığı için kod içinde /10 ile çevrilir):
    CENTER_X_MM, CENTER_Y_MM : çember merkezinin eskiz düzlemi koordinatları
    DIAMETER_MM              : çember çapı
    HEIGHT_MM                : uzatma (extrude) yüksekliği

Ne zaman kullanılır:
    - Silindirik parçalar: mil, boru, tekerlek, ayak, motor gövdesi,
      yuvarlak tabla gibi "daire/silindir" isteklerinde temel şablondur.
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
CENTER_X_MM = 0.0
CENTER_Y_MM = 0.0
DIAMETER_MM = 40.0
HEIGHT_MM = 20.0

# mm -> cm dönüşümü (Fusion 360 API dahili uzunluk birimi cm'dir)
radius_cm = (DIAMETER_MM / 2.0) / 10.0
center_cm = adsk.core.Point3D.create(CENTER_X_MM / 10.0, CENTER_Y_MM / 10.0, 0)
height_cm = HEIGHT_MM / 10.0

# ---- Kök bileşene erişim ----
app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent

# 1) XY düzleminde yeni eskiz oluştur
sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
sketch.name = 'CircleProfile'

# 2) Çemberi çiz (merkez ve yarıçap cm cinsinden)
sketch.sketchCurves.sketchCircles.addByCenterRadius(center_cm, radius_cm)

# 3) Kapalı profili yeni gövde olarak uzat
extrudes = rootComp.features.extrudeFeatures
prof = sketch.profiles.item(0)
ext_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(height_cm))
extrudes.add(ext_input)
