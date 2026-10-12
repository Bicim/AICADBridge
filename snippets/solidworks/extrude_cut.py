# SolidWorks (Adam-CAD) — Dikdörtgen Yuva / Cep Kesme (Extruded Cut)
cep_genislik_mm = sw.define_parameter('cep_genislik_mm', 30.0)
cep_uzunluk_mm = sw.define_parameter('cep_uzunluk_mm', 20.0)
cep_derinlik_mm = sw.define_parameter('cep_derinlik_mm', 10.0)

sw.cut_box(
    width_mm=cep_genislik_mm,
    length_mm=cep_uzunluk_mm,
    depth_mm=cep_derinlik_mm,
    x_mm=0.0,
    y_mm=0.0,
    plane='top',
    centered=True
)
sw.rebuild()
