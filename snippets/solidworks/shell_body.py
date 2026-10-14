# SolidWorks (Adam-CAD) — Kabuk / İçi Boş Gövde (Shell)
cidar_mm = sw.define_parameter('cidar_mm', 2.5)

sw.shell_body(wall_thickness_mm=cidar_mm)
sw.rebuild()
