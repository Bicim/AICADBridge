"""
Katı gövdeye baştan sona delik (simple drill hole) açar.

Ne yapar:
    - (DEMO) Önce üzerine delik açılacak bir blok oluşturur,
    - bloğun üst yüzeyinde verilen noktaya konumlandırılmış, gövdeyi
      tamamen delen bir simple-drill delik özelliği ekler.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    PLATE_W_MM, PLATE_L_MM, PLATE_T_MM : demo bloğun en/boy/kalınlığı
    HOLE_X_MM, HOLE_Y_MM               : deliğin üst yüzeydeki merkezi
    HOLE_DIA_MM                        : delik çapı

Ne zaman kullanılır:
    - Cıvata deliği, geçme deliği, montaj deliği gibi eksenel delikler.
    - NOT: Delik ekseni referans yüzeyin normali doğrultusundadır;
      konum noktası hedef gövdeye ait bir yüz üzerinde olmalıdır.
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
PLATE_W_MM = 50.0
PLATE_L_MM = 50.0
PLATE_T_MM = 30.0
HOLE_X_MM = 0.0
HOLE_Y_MM = 0.0
HOLE_DIA_MM = 8.0

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent
extrudes = rootComp.features.extrudeFeatures

# --- DEMO GÖVDE: blok, XY düzleminden +Z yönünde ---
plate_sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
plate_sketch.sketchCurves.sketchLines.addTwoPointRectangle(
    adsk.core.Point3D.create(-PLATE_W_MM / 2.0 / 10.0, -PLATE_L_MM / 2.0 / 10.0, 0),
    adsk.core.Point3D.create(PLATE_W_MM / 2.0 / 10.0, PLATE_L_MM / 2.0 / 10.0, 0))
plate_input = extrudes.createInput(plate_sketch.profiles.item(0),
                                   adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
plate_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(PLATE_T_MM / 10.0))
extrudes.add(plate_input)
plate_body = rootComp.bRepBodies.item(rootComp.bRepBodies.count - 1)

# --- Deliğin konumlanacağı ÜST YÜZEYİ bul: normali +Z olan düzlemsel yüz ---
top_face = None
for i in range(plate_body.faces.count):
    face = plate_body.faces.item(i)
    if face.geometry.objectType == adsk.core.Plane.classType():
        normal = face.geometry.normal
        if normal.z > 0.999:
            top_face = face
            break

# --- Delik özelliği ---
holes = rootComp.features.holeFeatures
hole_input = holes.createInput()
# TODO: positionByPoint imzası (yüz + global koordinatlı nokta) ve deliğin matkap
# yönü (yüzey normalinin tersi varsayılmıştır) Fusion API dokümanından doğrulanmalı.
hole_input.positionByPoint(
    top_face,
    adsk.core.Point3D.create(HOLE_X_MM / 10.0, HOLE_Y_MM / 10.0, PLATE_T_MM / 10.0))
# TODO: setSimpleDrillByDiameter imzası ve HoleExtentThroughAllDefinition.create()
# kullanımı doğrulanmalı; API sürümüne göre createInput2 ve farklı setSimpleDrill*
# varyantları bulunabilir.
hole_input.setSimpleDrillByDiameter(
    True,
    adsk.core.ValueInput.createByReal(HOLE_DIA_MM / 10.0),
    adsk.fusion.HoleExtentThroughAllDefinition.create())
holes.add(hole_input)
