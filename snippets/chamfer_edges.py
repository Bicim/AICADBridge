"""
Gövde kenarlarına pah (chamfer / eğik kesme) uygular.

Ne yapar:
    - (DEMO) Önce bir kutu gövdesi oluşturur,
    - son oluşturulan gövdenin TÜM kenarlarını seçer,
    - her birine eşit mesafeli pah kırar.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    BOX_W_MM, BOX_L_MM, BOX_H_MM : demo kutunun ölçüleri
    CHAMFER_MM                   : pah mesafesi

Ne zaman kullanılır:
    - "Kenarları kır", "pah ver" isteklerinde.
    - Keskin kenarları güvenli hale getirme, montaj/tolerans kolaylığı.
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
BOX_W_MM = 40.0
BOX_L_MM = 40.0
BOX_H_MM = 20.0
CHAMFER_MM = 2.0

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

# --- Pah kırılacak kenarları topla: son gövdenin tüm kenarları ---
body = rootComp.bRepBodies.item(rootComp.bRepBodies.count - 1)
edges = adsk.core.ObjectCollection.create()
for i in range(body.edges.count):
    edges.add(body.edges.item(i))

# --- Pah özelliği ---
chamfers = rootComp.features.chamferFeatures
chamfer_input = chamfers.createInput2()
# TODO: chamferEdgeSets.addEdgeSet imzası doğrulanmalı. Eşit mesafeli pah için
# (edges, distance) kullanıldı; bazı sürümlerde iki mesafeli varyant
# (edges, dist1, dist2) bulunur. createInput/createInput2 farkı da doğrulanmalı.
chamfer_input.chamferEdgeSets.addEdgeSet(
    edges,
    adsk.core.ValueInput.createByReal(CHAMFER_MM / 10.0))
chamfers.add(chamfer_input)
