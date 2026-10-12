# SolidWorks (Adam-CAD) — Kenar Yuvarlatma (Fillet)
radyus_mm = sw.define_parameter('radyus_mm', 3.0)

sw.fillet_edges(radius_mm=radyus_mm)
sw.rebuild()
