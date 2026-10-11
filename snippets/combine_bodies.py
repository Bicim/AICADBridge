"""
İki katı gövdeyi birleştirir (join) veya birinden diğerini keser (cut).

Ne yapar:
    - (DEMO) Üst üste binen iki kutu gövdesi oluşturur,
    - araç (tool) gövdeyi hedef (target) gövdeyle Combine özelliği
      üzerinden birleştirir.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    TARGET_W_MM, TARGET_L_MM, TARGET_H_MM : hedef kutunun ölçüleri
    TOOL_W_MM, TOOL_L_MM, TOOL_H_MM       : araç kutunun ölçüleri
    TOOL_OFFSET_X_MM, TOOL_OFFSET_Y_MM    : araç kutunun kaydırması

Ne zaman kullanılır:
    - Ayrı üretilen parçaları tek gövdeye kaynatmak (JoinFeatureOperation)
      veya bir gövdeden diğerinin izini düşürmek (CutFeatureOperation).
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
TARGET_W_MM = 40.0
TARGET_L_MM = 40.0
TARGET_H_MM = 20.0
TOOL_W_MM = 20.0
TOOL_L_MM = 20.0
TOOL_H_MM = 30.0
TOOL_OFFSET_X_MM = 15.0
TOOL_OFFSET_Y_MM = 15.0

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent
extrudes = rootComp.features.extrudeFeatures

# --- HEDEF GÖVDE: merkezde kutu ---
target_sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
target_sketch.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create(-TARGET_W_MM / 2.0 / 10.0, -TARGET_L_MM / 2.0 / 10.0, 0),
    adsk.core.Point3D.create(TARGET_W_MM / 2.0 / 10.0, TARGET_L_MM / 2.0 / 10.0, 0))
target_input = extrudes.createInput(target_sketch.profiles.item(0),
                                    adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
target_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(TARGET_H_MM / 10.0))
extrudes.add(target_input)
target_body = rootComp.bRepBodies.item(rootComp.bRepBodies.count - 1)

# --- ARAÇ GÖVDE: kaydırılmış, hedefle üst üste binen kutu ---
tool_sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
tool_sketch.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create(TOOL_OFFSET_X_MM / 10.0, TOOL_OFFSET_Y_MM / 10.0, 0),
    adsk.core.Point3D.create((TOOL_OFFSET_X_MM + TOOL_W_MM) / 10.0,
                             (TOOL_OFFSET_Y_MM + TOOL_L_MM) / 10.0, 0))
tool_input = extrudes.createInput(tool_sketch.profiles.item(0),
                                  adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
tool_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(TOOL_H_MM / 10.0))
extrudes.add(tool_input)
tool_body = rootComp.bRepBodies.item(rootComp.bRepBodies.count - 1)

# --- COMBINE: araç gövdeyi hedef gövdeye birleştir ---
combines = rootComp.features.combineFeatures
tool_bodies = adsk.core.ObjectCollection.create()
tool_bodies.add(tool_body)
combine_input = combines.createInput(target_body, tool_bodies)
combine_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
# Kesme yapmak için: adsk.fusion.FeatureOperations.CutFeatureOperation
# TODO: isKeepToolBodies gibi ek özellikler gerekiyorsa API dokümanından doğrulanmalı.
combines.add(combine_input)
