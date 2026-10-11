"""
Kesit profilini bir yol (path) boyunca tarayarak katı gövde üretir (sweep).

Ne yapar:
    - YZ düzleminde bir çember kesiti ve XY düzleminde +X doğrultusunda
      düz bir yol çizgisi oluşturur,
    - kesiti yol boyunca tarayarak yeni bir boru/silindir gövdesi üretir.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    PROFILE_DIA_MM : kesit çemberinin çapı
    PATH_LENGTH_MM  : yol uzunluğu

Ne zaman kullanılır:
    - Boru, kablo kanalı, eğri kol, ray gibi "yol boyunca uzat" istekleri.
      (Yol, düz çizgi yerine yay veya birleşik eğri de olabilir.)
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
PROFILE_DIA_MM = 10.0
PATH_LENGTH_MM = 80.0

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent

# 1) YOL: XY düzleminde orijinden +X yönüne düz çizgi
path_sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
path_sketch.name = 'SweepPath'
path_line = path_sketch.sketchCurves.sketchLines.addByTwoPoints(
    adsk.core.Point3D.create(0, 0, 0),
    adsk.core.Point3D.create(PATH_LENGTH_MM / 10.0, 0, 0))

# 2) KESİT: YZ düzleminde orijin merkezli çember (yolun başlangıcına dik)
prof_sketch = rootComp.sketches.add(rootComp.yZConstructionPlane)
prof_sketch.name = 'SweepProfile'
prof_sketch.sketchCurves.sketchCircles.addByCenterRadius(
    adsk.core.Point3D.create(0, 0, 0), PROFILE_DIA_MM / 2.0 / 10.0)

# 3) Yol (Path) nesnesini oluştur
# TODO: ChainedCurveOptions enum değerinin tam adı (noChainCurveOptions)
# doğrulanmalı; API sürümlerine göre farklılık gösterebilir.
path = adsk.fusion.Path.create(path_line, adsk.fusion.ChainedCurveOptions.noChainCurveOptions)

# 4) Sweep özelliği: kesiti yol boyunca tarayıp yeni gövde oluştur
sweeps = rootComp.features.sweepFeatures
sweep_input = sweeps.createInput(
    prof_sketch.profiles.item(0),
    path,
    adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
sweep_input.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
sweeps.add(sweep_input)
