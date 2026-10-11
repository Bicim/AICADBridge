"""
Gövdeyi seçilen yüzü açık bırakarak ince cidarlı kabuğa dönüştürür (shell).

Ne yapar:
    - (DEMO) Üst yüzeyi +Z yönünde bir kutu oluşturur,
    - üst yüzeyi "kaldırılacak yüz" olarak işaretleyip gövdeyi verilen
      cidar kalınlığında içi boş bir kabuğa dönüştürür.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    BOX_W_MM, BOX_L_MM, BOX_H_MM : demo kutunun ölçüleri
    WALL_MM                      : cidar kalınlığı

Ne zaman kullanılır:
    - İçi boş kap, kutu, muhafaza, kapak üretimi
      ("içini oy", "ince cidarlı yap" istekleri).
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
BOX_W_MM = 60.0
BOX_L_MM = 40.0
BOX_H_MM = 30.0
WALL_MM = 2.0

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent
extrudes = rootComp.features.extrudeFeatures

# --- DEMO GÖVDE: kutu (gerçek kullanımda mevcut gövde hedeflenir) ---
sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
sketch.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create(-BOX_W_MM / 2.0 / 10.0, -BOX_L_MM / 2.0 / 10.0, 0),
    adsk.core.Point3D.create(BOX_W_MM / 2.0 / 10.0, BOX_L_MM / 2.0 / 10.0, 0))
ext_input = extrudes.createInput(sketch.profiles.item(0),
                                 adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(BOX_H_MM / 10.0))
extrudes.add(ext_input)
body = rootComp.bRepBodies.item(rootComp.bRepBodies.count - 1)

# --- Açılacak ÜST YÜZEYİ bul: normali +Z olan düzlemsel yüz ---
top_face = None
for i in range(body.faces.count):
    face = body.faces.item(i)
    if face.geometry.objectType == adsk.core.Plane.classType():
        normal = face.geometry.normal
        if normal.z > 0.999:
            top_face = face
            break

# --- Kabuk (shell) özelliği ---
faces_to_remove = adsk.core.ObjectCollection.create()
faces_to_remove.add(top_face)

shells = rootComp.features.shellFeatures
# TODO: createInput(faces, isTangentChain) imzası ve insideThickness özellik adı
# doğrulanmalı (bazı sürümlerde outsideThickness gibi ek özellikler de vardır).
shell_input = shells.createInput(faces_to_remove, False)
shell_input.insideThickness = adsk.core.ValueInput.createByReal(WALL_MM / 10.0)
shells.add(shell_input)
