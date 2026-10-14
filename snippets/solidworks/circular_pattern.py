# SolidWorks (Adam-CAD) — Dairesel Dizilim / Bolt Circle Delikleri
delik_cap_mm = sw.define_parameter('delik_cap_mm', 6.0)
dizilim_cap_mm = sw.define_parameter('dizilim_cap_mm', 70.0)
delik_sayisi = 4

sw.cut_bolt_circle(
    hole_diameter_mm=delik_cap_mm,
    bolt_circle_diameter_mm=dizilim_cap_mm,
    count=delik_sayisi,
    plane='top'
)
sw.rebuild()
