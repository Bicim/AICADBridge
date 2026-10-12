# SolidWorks (Adam-CAD) — Döndürerek Katılama (Revolve)
alt_yaricap_mm = sw.define_parameter('alt_yaricap_mm', 30.0)
ust_yaricap_mm = sw.define_parameter('ust_yaricap_mm', 18.0)
yukseklik_mm = sw.define_parameter('yukseklik_mm', 50.0)

sw.revolve_profile(
    points_mm=[
        (0.0, 0.0),
        (alt_yaricap_mm, 0.0),
        (ust_yaricap_mm, yukseklik_mm),
        (0.0, yukseklik_mm),
    ],
    angle_deg=360.0,
    plane='front'
)
sw.rebuild()
