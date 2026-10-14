# SolidWorks (Adam-CAD) — Merkez veya Cıvata Dairesi Delik Açma (Cut Hole / Bolt Circle)
delik_cap_mm = sw.define_parameter('delik_cap_mm', 15.0)
delik_derinlik_mm = sw.define_parameter('delik_derinlik_mm', 80.0)

# Tek merkez deliği:
sw.cut_hole(
    diameter_mm=delik_cap_mm,
    depth_mm=delik_derinlik_mm,
    x_mm=0.0,
    y_mm=0.0,
    plane='top',
    through_all=True
)
sw.rebuild()
