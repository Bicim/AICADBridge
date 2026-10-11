"""
Unsur veya gövdeyi bir düzlem boyunca aynalar (mirror).

Ne yapar:
    - (DEMO) YZ düzleminin +X tarafında bir kutu oluşturur,
    - bu kutu unsurunu YZ düzlemi boyunca aynalayarak simetrik kopyasını üretir.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    BOX_W_MM, BOX_L_MM, BOX_H_MM : demo kutunun ölçüleri
    BOX_OFFSET_MM                : kutunun YZ düzleminden uzaklığı

Ne zaman kullanılır:
    - Simetrik parçaların yalnızca yarısını modelleyip aynalamak
      ("iki tarafı simetrik yap" istekleri).
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
BOX_W_MM = 40.0
BOX_L_MM = 30.0
BOX_H_MM = 15.0
BOX_OFFSET_MM = 10.0

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent
extrudes = rootComp.features.extrudeFeatures

# --- DEMO UNSUR: YZ düzleminin +X tarafında kutu ---
sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
sketch.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create(BOX_OFFSET_MM / 10.0, -BOX_L_MM / 2.0 / 10.0, 0),
    adsk.core.Point3D.create((BOX_OFFSET_MM + BOX_W_MM) / 10.0, BOX_L_MM / 2.0 / 10.0, 0))
ext_input = extrudes.createInput(sketch.profiles.item(0),
                                 adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(BOX_H_MM / 10.0))
box_feature = extrudes.add(ext_input)

# --- Aynalanacak unsur(lar) ---
mirror_entities = adsk.core.ObjectCollection.create()
mirror_entities.add(box_feature)

# --- Aynalama özelliği: YZ düzlemi (X=0) boyunca ---
mirrors = rootComp.features.mirrorFeatures
mirror_input = mirrors.createInput(mirror_entities)
# TODO: MirrorFeatureInput üzerinde düzlemi ayarlayan özelliğin adı ('plane')
# ve createInput imzası (düzlem parametresi ayrıca alınabilir) doğrulanmalı.
mirror_input.plane = rootComp.yZConstructionPlane
mirrors.add(mirror_input)
