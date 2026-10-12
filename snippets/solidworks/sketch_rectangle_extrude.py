# SolidWorks (Adam-CAD) — Dikdörtgen Kutu / Plaka Katılama (Extrude Boss)
genislik_mm = sw.define_parameter('genislik_mm', 80.0)
uzunluk_mm = sw.define_parameter('uzunluk_mm', 50.0)
yukseklik_mm = sw.define_parameter('yukseklik_mm', 20.0)

sw.extrude_box(
    width_mm=genislik_mm,
    length_mm=uzunluk_mm,
    height_mm=yukseklik_mm,
    x_mm=0.0,
    y_mm=0.0,
    plane='top',
    centered=True
)
sw.rebuild()
