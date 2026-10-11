"""
Unsur(lar)ı bir eksen etrafında dairesel olarak çoğaltır (circular pattern).

Ne yapar:
    - (DEMO) Merkezden belirli mesafede küçük bir silindirik unsur oluşturur,
    - bu unsuru Z ekseni etrafında istenen sayıda ve toplam açıda tekrarlar.

Parametreler (mm cinsinden; kod içinde /10 ile cm'ye çevrilir):
    POST_RADIUS_MM  : desenlenecek unsurun (silindir) yarıçapı
    POST_HEIGHT_MM  : unsur yüksekliği
    BOLT_RADIUS_MM  : desenin merkez eksene uzaklığı (bolt-circle yarıçapı)
    PATTERN_COUNT   : tekrar sayısı
    TOTAL_ANGLE_DEG : desenin toplam açısı (derece)

Ne zaman kullanılır:
    - Cıvata deliği dağılımı, pervane/kanat dizilimi, kollu hub gibi
      "etrafına X tane ekle" isteklerinde.
"""

import math

import adsk.core
import adsk.fusion

# ---- Parametreler (mm) ----
POST_RADIUS_MM = 5.0
POST_HEIGHT_MM = 15.0
BOLT_RADIUS_MM = 30.0
PATTERN_COUNT = 6
TOTAL_ANGLE_DEG = 360.0

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
rootComp = design.rootComponent
extrudes = rootComp.features.extrudeFeatures

# --- DEMO UNSUR: merkezden BOLT_RADIUS_MM ötede küçük silindir ---
post_sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
post_sketch.sketchCurves.sketchCircles.addByCenterRadius(
    adsk.core.Point3D.create(BOLT_RADIUS_MM / 10.0, 0, 0),
    POST_RADIUS_MM / 10.0)
post_input = extrudes.createInput(post_sketch.profiles.item(0),
                                  adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
post_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(POST_HEIGHT_MM / 10.0))
post_feature = extrudes.add(post_input)

# --- Desenlenecek unsur(lar)ı koleksiyona koy ---
pattern_entities = adsk.core.ObjectCollection.create()
pattern_entities.add(post_feature)

# --- Dairesel desen: Z ekseni etrafında ---
circ_patterns = rootComp.features.circularPatternFeatures
pattern_input = circ_patterns.createInput(pattern_entities, rootComp.zConstructionAxis)
pattern_input.quantity = adsk.core.ValueInput.createByReal(PATTERN_COUNT)
# TODO: totalAngle için createByReal ile verilen değerin radyan olarak yorumlandığı
# varsayılmıştır (360 derece = 2*pi). Derece/radyan yorumu doğrulanmalı.
pattern_input.totalAngle = adsk.core.ValueInput.createByReal(math.radians(TOTAL_ANGLE_DEG))
circ_patterns.add(pattern_input)
