# SolidWorks (Adam-CAD) — Daire Eskiz ve Silindir Katılama (Extrude Boss)
cap_mm = sw.define_parameter('cap_mm', 50.0)
yukseklik_mm = sw.define_parameter('yukseklik_mm', 80.0)

sw.extrude_cylinder(
    diameter_mm=cap_mm,
    height_mm=yukseklik_mm,
    x_mm=0.0,
    y_mm=0.0,
    plane='top'
)
sw.rebuild()
