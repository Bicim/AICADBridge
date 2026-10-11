"""
Kapalı bir eskiz profilini bir eksen etrafında döndürerek katı gövde üretir (revolve).

Ne yapar:
    - XZ düzleminde halka kesitli (içi boş) kapalı bir profil çizer,
    - bu profili Z ekseni etrafında verilen açıda döndürerek yeni bir
      eksenel simetrik gövde (halka/boru) oluşturur.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    INNER_RADIUS_MM : iç yarıçap (0 yapılırsa dolu gövde elde edilir)
    OUTER_RADIUS_MM : dış yarıçap
    HEIGHT_MM       : döndürme ekseni yönündeki yükseklik
    ANGLE_DEG       : döndürme açısı (derece)

Ne zaman kullanılır:
    - Eksenel simetrik parçalar: halka, kapak, huni, koni, şişe, mil
      başlığı gibi "döndürerek oluştur" isteklerinde.
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
INNER_RADIUS_MM = 20.0
OUTER_RADIUS_MM = 30.0
HEIGHT_MM = 40.0
ANGLE_DEG = 360.0

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent

# XZ düzleminde eskiz: eskiz x -> global X (yarıçap yönü),
# eskiz y -> global Z (yükseklik yönü). Kesit +X bölgesinde yer alır.
sketch = rootComp.sketches.add(rootComp.xZConstructionPlane)
sketch.name = 'RevolveProfile'

# Kapalı halka kesiti: dikdörtgen (iç yarıçap .. dış yarıçap, 0 .. yükseklik)
sketch.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create(INNER_RADIUS_MM / 10.0, 0, 0),
    adsk.core.Point3D.create(OUTER_RADIUS_MM / 10.0, HEIGHT_MM / 10.0, 0))

# Profili Z ekseni etrafında döndür
revolves = rootComp.features.revolveFeatures
rev_input = revolves.createInput(
    sketch.profiles.item(0),
    rootComp.zConstructionAxis,
    adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
# Açı gerçek değeri RADYAN cinsindendir (360 derece = 2*pi)
rev_input.setAngleExtent(False, adsk.core.ValueInput.createByReal(math.radians(ANGLE_DEG)))
revolves.add(rev_input)
