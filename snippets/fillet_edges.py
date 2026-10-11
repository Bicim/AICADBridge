"""
Gövde kenarlarına sabit yarıçaplı yuvarlatma (fillet) uygular.

Ne yapar:
    - (DEMO) Önce bir kutu gövdesi oluşturur,
    - son oluşturulan gövdenin TÜM kenarlarını seçer,
    - her birine aynı yarıçapta fillet uygular.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    BOX_W_MM, BOX_L_MM, BOX_H_MM : demo kutunun ölçüleri
    FILLET_RADIUS_MM             : yuvarlatma yarıçapı

Ne zaman kullanılır:
    - "Kenarları yuvarlatılmış", "köşeleri yumuşat" isteklerinde.
    - Güvenli kenar, estetik radyüs veya montaj kolaylığı için.
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
BOX_W_MM = 40.0
BOX_L_MM = 40.0
BOX_H_MM = 20.0
FILLET_RADIUS_MM = 3.0

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent
extrudes = rootComp.features.extrudeFeatures

# --- DEMO GÖVDE: kutu (gerçek kullanımda mevcut gövde hedeflenir) ---
box_sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
box_sketch.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create(-BOX_W_MM / 2.0 / 10.0, -BOX_L_MM / 2.0 / 10.0, 0),
    adsk.core.Point3D.create(BOX_W_MM / 2.0 / 10.0, BOX_L_MM / 2.0 / 10.0, 0))
box_input = extrudes.createInput(box_sketch.profiles.item(0),
                                 adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
box_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(BOX_H_MM / 10.0))
extrudes.add(box_input)

# --- Yuvarlatılacak kenarları topla: son gövdenin tüm kenarları ---
body = rootComp.bRepBodies.item(rootComp.bRepBodies.count - 1)
edges = adsk.core.ObjectCollection.create()
for i in range(body.edges.count):
    edges.add(body.edges.item(i))

# --- Sabit yarıçaplı kenar seti ile fillet oluştur ---
fillets = rootComp.features.filletFeatures
fillet_input = fillets.createInput()
fillet_input.addConstantRadiusEdgeSet(
    edges,
    adsk.core.ValueInput.createByReal(FILLET_RADIUS_MM / 10.0),
    True)  # teğet zincir boyunca yayılım
fillets.add(fillet_input)
