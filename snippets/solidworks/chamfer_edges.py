# SolidWorks (Adam-CAD) — Kenar Pah Kırma (Chamfer)
pah_mm = sw.define_parameter('pah_mm', 2.0)

sw.chamfer_edges(distance_mm=pah_mm, angle_deg=45.0)
sw.rebuild()
