"""SolidWorks CAD adapterı (COM / pywin32 + Adam-CAD / CADAM parametrik köprüsü).

Bu modül Windows üzerinde çalışan SolidWorks (`SldWorks.Application`) oturumuna
`win32com.client` (COM API) üzerinden bağlanır. Fusion 360 adaptörüyle (`fusion360.py`)
birebir aynı arayüzü sunar:
    - inspect_current_design()
    - execute_code(code)
    - capture_viewport_image(width, height)
    - update_parameters(params_dict)

Ayrıca LLM tarafından üretilen Python kodlarının SolidWorks COM API'sindeki
(SelectByID2 VARIANT farkları, TR/EN düzlem isimleri, metre/milimetre dönüşümü)
tuzaklara takılmaması için hem:
    1) Akıllı COM sarmalayıcıları (`swApp`, `swModel`, `featMgr`, `sketchMgr`, `selMgr`)
    2) Yüksek seviyeli Adam-CAD yardımcıları (`sw` / `cad` nesnesi)
doğrudan `exec` çalışma alanına enjekte edilir.
"""

import ast
import base64
import math
import os
import tempfile
import traceback

from aicad_bridge.runtime import aicad_log

try:
    import pythoncom
    import win32com.client
    HAS_WIN32COM = True
except ImportError:
    pythoncom = None
    win32com = None
    HAS_WIN32COM = False


# SolidWorks sabitleri
SW_DOC_NONE = 0
SW_DOC_PART = 1
SW_DOC_ASSEMBLY = 2
SW_DOC_DRAWING = 3

SW_END_COND_BLIND = 0
SW_END_COND_THROUGH_ALL = 1
SW_END_COND_MID_PLANE = 6

# Standart düzlem eşlemeleri (TR / EN / Almanca / Fransızca / Kısaltmalar)
PLANE_ALIASES = {
    'front': ('Front Plane', 'Ön Düzlem', 'Ön', 'Front', 'Ebene vorne', 'Plan de face'),
    'top': ('Top Plane', 'Üst Düzlem', 'Üst', 'Top', 'Ebene oben', 'Plan de dessus'),
    'right': ('Right Plane', 'Sağ Düzlem', 'Sağ', 'Right', 'Ebene rechts', 'Plan de droite'),
}


def _co_init():
    """Arka plan HTTP thread'lerinde COM çağrılarının çalışması için CoInitialize çağırır."""
    if HAS_WIN32COM and pythoncom is not None:
        try:
            pythoncom.CoInitialize()
        except Exception:
            pass


def _null_callout():
    """SelectByID2 için pywin32'nin beklediği VT_DISPATCH None VARIANT'ını döndürür."""
    if HAS_WIN32COM and win32com is not None and pythoncom is not None:
        try:
            return win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        except Exception:
            return None
    return None


def get_sw_app(launch_if_needed=False):
    """Açık olan SolidWorks uygulamasına bağlanır (veya istenirse başlatır)."""
    if not HAS_WIN32COM:
        return None
    _co_init()
    try:
        app = win32com.client.GetActiveObject("SldWorks.Application")
        return app
    except Exception:
        if not launch_if_needed:
            try:
                # Bazı sistemlerde GetActiveObject yerine Dispatch mevcut oturuma bağlanır
                app = win32com.client.Dispatch("SldWorks.Application")
                if getattr(app, 'Visible', False):
                    return app
            except Exception:
                return None
            return None
        try:
            app = win32com.client.Dispatch("SldWorks.Application")
            app.Visible = True
            return app
        except Exception as e:
            aicad_log(f"[SolidWorks] Uygulama başlatılamadı: {e}")
            return None


def is_available():
    """SolidWorks COM bağlantısının aktif olup olmadığını döndürür."""
    app = get_sw_app(launch_if_needed=False)
    return app is not None


def _get_doc_title(doc):
    try:
        t = doc.GetTitle
        return t() if callable(t) else str(t)
    except Exception:
        return "Parca1.SLDPRT"


def _get_doc_type(doc):
    try:
        t = doc.GetType
        return int(t() if callable(t) else t)
    except Exception:
        return SW_DOC_PART


def ensure_active_part(sw_app):
    """Aktif bir Part dokümanı döndürür; açık doküman yoksa yeni bir Part açar."""
    if not sw_app:
        return None
    doc = getattr(sw_app, 'ActiveDoc', None)
    if callable(doc):
        doc = doc()
    if doc is not None:
        return doc

    aicad_log("[SolidWorks] Açık doküman bulunamadı, yeni Parça (Part) oluşturuluyor...")
    # 1. Yöntem: NewPart()
    try:
        new_doc = sw_app.NewPart()
        if new_doc is not None:
            return new_doc
    except Exception:
        pass

    # 2. Yöntem: Varsayılan şablon üzerinden NewDocument
    try:
        # 8 = swDefaultTemplatePart
        tmpl = sw_app.GetUserPreferenceStringValue(8)
        if tmpl:
            new_doc = sw_app.NewDocument(tmpl, 0, 0, 0)
            if new_doc is not None:
                return new_doc
    except Exception:
        pass

    return getattr(sw_app, 'ActiveDoc', None)


def select_standard_plane(model, plane_key='top', append=False):
    """Dil bağımsız (TR/EN) standart düzlem seçici.

    plane_key: 'top' | 'xy' | 'front' | 'xz' | 'right' | 'yz' veya doğrudan düzlem adı.
    """
    if model is None:
        return False
    key = str(plane_key or 'top').strip().lower()
    if key in ('xy', 'top', 'üst', 'ust', 'üst düzlem', 'top plane', 'z'):
        norm = 'top'
    elif key in ('xz', 'front', 'ön', 'on', 'ön düzlem', 'front plane', 'y'):
        norm = 'front'
    elif key in ('yz', 'right', 'sağ', 'sag', 'sağ düzlem', 'right plane', 'x'):
        norm = 'right'
    else:
        norm = None

    ext = getattr(model, 'Extension', None)
    callout = _null_callout()

    candidates = list(PLANE_ALIASES.get(norm, ())) if norm else [ str(plane_key) ]
    for name in candidates:
        try:
            if ext is not None:
                ok = ext.SelectByID2(name, "PLANE", 0.0, 0.0, 0.0, bool(append), 0, callout, 0)
                if ok:
                    return True
        except Exception:
            try:
                if ext is not None:
                    ok = ext.SelectByID2(name, "PLANE", 0.0, 0.0, 0.0, bool(append), 0, None, 0)
                    if ok:
                        return True
            except Exception:
                pass

    # İsimle bulunamadıysa Feature ağacındaki ilk RefPlane unsurlarını tara (dil bağımsız kesin çözüm)
    plane_order = {'front': 0, 'top': 1, 'right': 2}.get(norm, 0)
    try:
        feat = model.FirstFeature
        if callable(feat):
            feat = feat()
        ref_planes = []
        guard = 0
        while feat is not None and guard < 40:
            guard += 1
            try:
                tn = feat.GetTypeName2
                tname = tn() if callable(tn) else str(tn)
                if tname == 'RefPlane':
                    ref_planes.append(feat)
                    if len(ref_planes) >= 3:
                        break
            except Exception:
                pass
            nxt = getattr(feat, 'GetNextFeature', None)
            feat = nxt() if callable(nxt) else nxt

        if ref_planes:
            target = ref_planes[min(plane_order, len(ref_planes) - 1)]
            sel_fn = getattr(target, 'Select2', None)
            if callable(sel_fn):
                return bool(sel_fn(bool(append), 0))
    except Exception as e:
        aicad_log(f"[SolidWorks] RefPlane tarama hatası: {e}")

    return False


class SafeExtensionWrapper:
    """ModelDocExtension.SelectByID2 çağrılarında Callout=None ve TR/EN düzlem adlarını otomatik düzeltir."""

    def __init__(self, real_ext, model):
        self._real_ext = real_ext
        self._model = model

    def SelectByID2(self, name, sel_type, x=0.0, y=0.0, z=0.0, append=False, mark=0, callout=None, select_option=0):
        st = str(sel_type or '').upper()
        if st == 'PLANE':
            if select_standard_plane(self._model, name, append=append):
                return True
        if self._real_ext is None:
            return False
        co = _null_callout() if callout is None else callout
        try:
            return self._real_ext.SelectByID2(
                str(name), str(sel_type), float(x), float(y), float(z),
                bool(append), int(mark), co, int(select_option)
            )
        except Exception:
            return self._real_ext.SelectByID2(
                str(name), str(sel_type), float(x), float(y), float(z),
                bool(append), int(mark), None, int(select_option)
            )

    def __getattr__(self, item):
        return getattr(self._real_ext, item) if self._real_ext is not None else None


class SafeModelWrapper:
    """IModelDoc2 sarmalayıcısı: güvenli Extension.SelectByID2 ve yardımcı metotlar sağlar."""

    def __init__(self, real_model):
        self._real_model = real_model
        self._ext = SafeExtensionWrapper(getattr(real_model, 'Extension', None), real_model) if real_model else None

    @property
    def Extension(self):
        return self._ext

    def ClearSelection2(self, all_flag=True):
        if self._real_model is None:
            return
        try:
            self._real_model.ClearSelection2(bool(all_flag))
        except Exception:
            pass

    def EditRebuild3(self):
        if self._real_model is None:
            return False
        try:
            res = self._real_model.EditRebuild3
            return res() if callable(res) else bool(res)
        except Exception:
            return False

    def __getattr__(self, item):
        return getattr(self._real_model, item) if self._real_model is not None else None


class SolidWorksCADHelper:
    """Adam-CAD (CADAM) tarzı yüksek seviyeli, milimetre (mm) tabanlı SolidWorks modelleme yardımcısı.

    LLM hem doğrudan SolidWorks COM API'sini (`swModel`, `sketchMgr`, `featMgr`)
    hem de bu `sw` / `cad` yardımcı sınıfını kullanabilir. Tüm ölçüler **mm** cinsindendir
    ve dahili olarak SolidWorks birimi olan **metreye (/1000.0)** otomatik çevrilir.
    """

    def __init__(self, sw_app, raw_model):
        self.app = sw_app
        self.raw_model = raw_model
        self.model = SafeModelWrapper(raw_model)
        self.sketch_mgr = getattr(raw_model, 'SketchManager', None) if raw_model else None
        self.feat_mgr = getattr(raw_model, 'FeatureManager', None) if raw_model else None
        self.operations_log = []
        self.parameters = {}

    @staticmethod
    def mm(val_mm):
        """Milimetreyi SolidWorks dahili birimi olan metreye çevirir (1 mm = 0.001 m)."""
        return float(val_mm) / 1000.0

    def define_parameter(self, name, value_mm, unit='mm'):
        """Parametrik değeri kaydeder ve varsa SolidWorks global değişkenini günceller."""
        val = float(value_mm)
        self.parameters[str(name)] = {'value': val, 'unit': unit}
        return val

    def select_plane(self, plane='top', append=False):
        """'top' (XY), 'front' (XZ) veya 'right' (YZ) düzlemini seçer."""
        self.model.ClearSelection2(True)
        return select_standard_plane(self.raw_model, plane, append=append)

    def _begin_sketch(self, plane='top'):
        self.select_plane(plane, append=False)
        if self.sketch_mgr is not None:
            try:
                self.sketch_mgr.InsertSketch(True)
            except Exception:
                pass

    def _end_sketch(self):
        if self.sketch_mgr is not None:
            try:
                self.sketch_mgr.InsertSketch(True)
            except Exception:
                pass

    def _extrude_boss(self, depth_m, merge=True, midplane=False):
        if self.feat_mgr is None:
            return None
        end_cond = SW_END_COND_MID_PLANE if midplane else SW_END_COND_BLIND
        # FeatureExtrusion3 veya FeatureExtrusion2
        for method_name in ('FeatureExtrusion3', 'FeatureExtrusion2'):
            fn = getattr(self.feat_mgr, method_name, None)
            if callable(fn):
                try:
                    if method_name == 'FeatureExtrusion3':
                        feat = fn(
                            True, False, False, end_cond, 0, float(depth_m), 0.0,
                            False, False, False, False, 0.0, 0.0,
                            False, False, False, False, bool(merge), True, True,
                            0, 0.0, False
                        )
                    else:
                        feat = fn(
                            True, False, False, end_cond, 0, float(depth_m), 0.0,
                            False, False, False, False, 0.0, 0.0,
                            False, False, False, False, bool(merge), True, True,
                            0, 0.0, False
                        )
                    if feat is not None:
                        return feat
                except Exception as e:
                    aicad_log(f"[SolidWorks] {method_name} hatası: {e}")
        return None

    def _extrude_cut(self, depth_m=None, through_all=False, flip_dir=False):
        if self.feat_mgr is None:
            return None
        end_cond = SW_END_COND_THROUGH_ALL if (through_all or depth_m is None) else SW_END_COND_BLIND
        d_m = float(depth_m) if depth_m is not None else 1.0
        for method_name in ('FeatureCut4', 'FeatureCut3'):
            fn = getattr(self.feat_mgr, method_name, None)
            if callable(fn):
                try:
                    if method_name == 'FeatureCut4':
                        feat = fn(
                            True, False, bool(flip_dir), end_cond, 0, d_m, 0.0,
                            False, False, False, False, 0.0, 0.0,
                            False, False, False, False, False, True, True,
                            True, True, False, 0, 0.0, False, False
                        )
                    else:
                        feat = fn(
                            True, False, bool(flip_dir), end_cond, 0, d_m, 0.0,
                            False, False, False, False, 0.0, 0.0,
                            False, False, False, False, False, True, True,
                            False, False, False, 0, 0.0, False
                        )
                    if feat is not None:
                        return feat
                except Exception as e:
                    aicad_log(f"[SolidWorks] {method_name} hatası: {e}")
        return None

    def extrude_cylinder(self, diameter_mm, height_mm, x_mm=0.0, y_mm=0.0, plane='top', merge=True, midplane=False, cx_mm=None, cy_mm=None):
        """Belirtilen düzlemde (varsayılan Top/Üst) silindir katılar."""
        if cx_mm is not None:
            x_mm = cx_mm
        if cy_mm is not None:
            y_mm = cy_mm
        r_m = self.mm(diameter_mm) / 2.0
        h_m = self.mm(height_mm)
        cx_m = self.mm(x_mm)
        cy_m = self.mm(y_mm)

        self._begin_sketch(plane)
        if self.sketch_mgr is not None:
            self.sketch_mgr.CreateCircleByRadius(cx_m, cy_m, 0.0, r_m)
        feat = self._extrude_boss(h_m, merge=merge, midplane=midplane)
        self.model.ClearSelection2(True)
        self.operations_log.append(f"extrude_cylinder(d={diameter_mm}mm, h={height_mm}mm)")
        return feat

    def extrude_box(self, width_mm, length_mm, height_mm, x_mm=0.0, y_mm=0.0, plane='top', centered=True, merge=True, midplane=False, cx_mm=None, cy_mm=None):
        """Belirtilen düzlemde dikdörtgen prizma (kutu/plaka) katılar."""
        if cx_mm is not None:
            x_mm = cx_mm
        if cy_mm is not None:
            y_mm = cy_mm
        w_m = self.mm(width_mm)
        l_m = self.mm(length_mm)
        h_m = self.mm(height_mm)
        cx_m = self.mm(x_mm)
        cy_m = self.mm(y_mm)

        self._begin_sketch(plane)
        if self.sketch_mgr is not None:
            if centered:
                self.sketch_mgr.CreateCenterRectangle(cx_m, cy_m, 0.0, cx_m + w_m / 2.0, cy_m + l_m / 2.0, 0.0)
            else:
                self.sketch_mgr.CreateCornerRectangle(cx_m, cy_m, 0.0, cx_m + w_m, cy_m + l_m, 0.0)
        feat = self._extrude_boss(h_m, merge=merge, midplane=midplane)
        self.model.ClearSelection2(True)
        self.operations_log.append(f"extrude_box({width_mm}x{length_mm}x{height_mm}mm)")
        return feat

    def extrude_polygon(self, sides, diameter_mm, height_mm, x_mm=0.0, y_mm=0.0, plane='top', merge=True, cx_mm=None, cy_mm=None):
        """Çokgen (altıgen somun vb.) profil çizip katılar."""
        if cx_mm is not None:
            x_mm = cx_mm
        if cy_mm is not None:
            y_mm = cy_mm
        r_m = self.mm(diameter_mm) / 2.0
        h_m = self.mm(height_mm)
        cx_m = self.mm(x_mm)
        cy_m = self.mm(y_mm)

        self._begin_sketch(plane)
        if self.sketch_mgr is not None:
            try:
                self.sketch_mgr.CreatePolygon(cx_m, cy_m, 0.0, cx_m + r_m, cy_m, 0.0, int(sides), True)
            except Exception:
                # Fallback: çizgilerle çokgen
                n = max(3, int(sides))
                for i in range(n):
                    a1 = 2.0 * math.pi * i / n
                    a2 = 2.0 * math.pi * (i + 1) / n
                    self.sketch_mgr.CreateLine(
                        cx_m + r_m * math.cos(a1), cy_m + r_m * math.sin(a1), 0.0,
                        cx_m + r_m * math.cos(a2), cy_m + r_m * math.sin(a2), 0.0
                    )
        feat = self._extrude_boss(h_m, merge=merge)
        self.model.ClearSelection2(True)
        self.operations_log.append(f"extrude_polygon(sides={sides}, d={diameter_mm}mm, h={height_mm}mm)")
        return feat

    def cut_hole(self, diameter_mm, depth_mm=None, x_mm=0.0, y_mm=0.0, plane='top', through_all=False, cx_mm=None, cy_mm=None):
        """Mevcut katı gövde üzerinde dairesel delik (Extruded Cut) açar."""
        if cx_mm is not None:
            x_mm = cx_mm
        if cy_mm is not None:
            y_mm = cy_mm
        r_m = self.mm(diameter_mm) / 2.0
        d_m = self.mm(depth_mm) if depth_mm is not None else None
        cx_m = self.mm(x_mm)
        cy_m = self.mm(y_mm)

        self._begin_sketch(plane)
        if self.sketch_mgr is not None:
            self.sketch_mgr.CreateCircleByRadius(cx_m, cy_m, 0.0, r_m)
        feat = self._extrude_cut(depth_m=d_m, through_all=(through_all or depth_mm is None), flip_dir=False)
        if feat is None:
            # Kesme yönü ters kalmış olabilir; ters yönde tekrar dene
            feat = self._extrude_cut(depth_m=d_m, through_all=True, flip_dir=True)
        self.model.ClearSelection2(True)
        self.operations_log.append(f"cut_hole(d={diameter_mm}mm, x={x_mm}, y={y_mm})")
        return feat

    def reset_part(self):
        """Parametrik (Adam-CAD) modda slider değiştiğinde mevcut unsurları temizler veya yeni parça açar."""
        if self.raw_model is None:
            return
        try:
            feats, sketches = _count_features_and_sketches(self.raw_model)
            ext = getattr(self.raw_model, 'Extension', None)
            callout = _null_callout()
            for item in reversed(feats + sketches):
                name = item.get('name', '')
                if not name:
                    continue
                try:
                    self.model.ClearSelection2(True)
                    if ext is not None:
                        ext.SelectByID2(name, "BODYFEATURE", 0.0, 0.0, 0.0, False, 0, callout, 0)
                        ext.SelectByID2(name, "SKETCH", 0.0, 0.0, 0.0, True, 0, callout, 0)
                    del_fn = getattr(self.raw_model, 'EditDelete', None)
                    if callable(del_fn):
                        del_fn()
                except Exception:
                    pass
            self.model.ClearSelection2(True)
        except Exception as e:
            aicad_log(f"[SolidWorks] reset_part uyarısı: {e}")

    def cut_bolt_circle(self, hole_diameter_mm, bolt_circle_diameter_mm, count, depth_mm=None, x_mm=0.0, y_mm=0.0, plane='top', cx_mm=None, cy_mm=None):
        """Flanş vb. parçalar üzerinde dairesel dizilimli (bolt circle) cıvata delikleri açar.
        İlk iki argüman hangi sırayla verilirse verilsin (küçük olan delik çapı, büyük olan PCD) otomatik algılanır.
        """
        if cx_mm is not None:
            x_mm = cx_mm
        if cy_mm is not None:
            y_mm = cy_mm
        d1 = float(hole_diameter_mm)
        d2 = float(bolt_circle_diameter_mm)
        actual_hole_mm = min(d1, d2)
        actual_pcd_mm = max(d1, d2)
        r_hole_m = self.mm(actual_hole_mm) / 2.0
        r_pitch_m = self.mm(actual_pcd_mm) / 2.0
        cx_m = self.mm(x_mm)
        cy_m = self.mm(y_mm)
        d_m = self.mm(depth_mm) if depth_mm is not None else None
        n = max(1, int(count))

        self._begin_sketch(plane)
        if self.sketch_mgr is not None:
            for i in range(n):
                angle = 2.0 * math.pi * i / n
                hx = cx_m + r_pitch_m * math.cos(angle)
                hy = cy_m + r_pitch_m * math.sin(angle)
                self.sketch_mgr.CreateCircleByRadius(hx, hy, 0.0, r_hole_m)
        feat = self._extrude_cut(depth_m=d_m, through_all=(depth_mm is None), flip_dir=False)
        if feat is None:
            feat = self._extrude_cut(depth_m=d_m, through_all=True, flip_dir=True)
        self.model.ClearSelection2(True)
        self.operations_log.append(f"cut_bolt_circle(count={n}, d={actual_hole_mm}mm, pcd={actual_pcd_mm}mm)")
        return feat

    def cut_box(self, width_mm, length_mm, depth_mm=None, x_mm=0.0, y_mm=0.0, plane='top', centered=True, cx_mm=None, cy_mm=None):
        """Dikdörtgen cep / kanal / yuva kesmesi yapar."""
        if cx_mm is not None:
            x_mm = cx_mm
        if cy_mm is not None:
            y_mm = cy_mm
        w_m = self.mm(width_mm)
        l_m = self.mm(length_mm)
        d_m = self.mm(depth_mm) if depth_mm is not None else None
        cx_m = self.mm(x_mm)
        cy_m = self.mm(y_mm)

        self._begin_sketch(plane)
        if self.sketch_mgr is not None:
            if centered:
                self.sketch_mgr.CreateCenterRectangle(cx_m, cy_m, 0.0, cx_m + w_m / 2.0, cy_m + l_m / 2.0, 0.0)
            else:
                self.sketch_mgr.CreateCornerRectangle(cx_m, cy_m, 0.0, cx_m + w_m, cy_m + l_m, 0.0)
        feat = self._extrude_cut(depth_m=d_m, through_all=(depth_mm is None), flip_dir=False)
        if feat is None:
            feat = self._extrude_cut(depth_m=d_m, through_all=True, flip_dir=True)
        self.model.ClearSelection2(True)
        self.operations_log.append(f"cut_box({width_mm}x{length_mm}mm)")
        return feat

    def _select_body_edges(self, max_edges=24):
        """Aktif katı gövdenin kenarlarını seçer (Fillet / Chamfer için)."""
        self.model.ClearSelection2(True)
        selected = 0
        bodies = _get_solid_bodies(self.raw_model)
        for body in bodies:
            try:
                edges = body.GetEdges
                edges = edges() if callable(edges) else edges
                if not edges:
                    continue
                for edge in edges[:max_edges]:
                    try:
                        ent = edge
                        sel_fn = getattr(ent, 'Select4', None) or getattr(ent, 'Select2', None)
                        if callable(sel_fn):
                            sel_fn(True, None)
                            selected += 1
                    except Exception:
                        pass
            except Exception:
                pass
        return selected

    def fillet_edges(self, radius_mm, max_edges=16):
        """Katı gövdenin kenarlarına radyus (Fillet) uygular."""
        r_m = self.mm(radius_mm)
        self._select_body_edges(max_edges=max_edges)
        feat = None
        if self.feat_mgr is not None:
            try:
                # SimpleFillet / FeatureFillet3
                fn = getattr(self.feat_mgr, 'FeatureFillet3', None)
                if callable(fn):
                    feat = fn(195, r_m, 0.0, 0, 0, 0, 0, None, None, None, None, None, None, None)
            except Exception as e:
                aicad_log(f"[SolidWorks] FeatureFillet3 hatası: {e}")
        self.model.ClearSelection2(True)
        self.operations_log.append(f"fillet_edges(r={radius_mm}mm)")
        return feat

    def chamfer_edges(self, distance_mm, angle_deg=45.0, max_edges=16):
        """Katı gövdenin kenarlarına pah (Chamfer) kırar."""
        d_m = self.mm(distance_mm)
        ang_rad = math.radians(float(angle_deg))
        self._select_body_edges(max_edges=max_edges)
        feat = None
        if self.feat_mgr is not None:
            try:
                fn = getattr(self.feat_mgr, 'InsertFeatureChamfer', None)
                if callable(fn):
                    feat = fn(4, 1, d_m, ang_rad, 0.0, 0.0, 0.0, 0.0)
            except Exception as e:
                aicad_log(f"[SolidWorks] InsertFeatureChamfer hatası: {e}")
        self.model.ClearSelection2(True)
        self.operations_log.append(f"chamfer_edges(d={distance_mm}mm)")
        return feat

    def shell_body(self, wall_thickness_mm, remove_top_face=True):
        """En üst düzlemsel yüzü seçip gövdenin içini boşaltır (Shell)."""
        t_m = self.mm(wall_thickness_mm)
        self.model.ClearSelection2(True)
        bodies = _get_solid_bodies(self.raw_model)
        if bodies and self.raw_model is not None:
            try:
                faces = bodies[0].GetFaces
                faces = faces() if callable(faces) else faces
                if faces and remove_top_face:
                    sel_fn = getattr(faces[0], 'Select4', None) or getattr(faces[0], 'Select2', None)
                    if callable(sel_fn):
                        sel_fn(False, None)
                fn = getattr(self.raw_model, 'InsertFeatureShell', None)
                if callable(fn):
                    fn(t_m, False)
            except Exception as e:
                aicad_log(f"[SolidWorks] InsertFeatureShell hatası: {e}")
        self.model.ClearSelection2(True)
        self.operations_log.append(f"shell_body(t={wall_thickness_mm}mm)")

    def revolve_profile(self, points_mm, angle_deg=360.0, plane='front', merge=True):
        """[(r1, z1), (r2, z2), ...] (mm) noktalarından kapalı kesit çizip Y ekseni etrafında döndürür (Revolve)."""
        pts = list(points_mm or [])
        if len(pts) < 3:
            raise ValueError("revolve_profile için en az 3 nokta (r_mm, z_mm) gereklidir.")
        ang_rad = math.radians(float(angle_deg))

        self._begin_sketch(plane)
        if self.sketch_mgr is not None:
            # Merkez ekseni (Y ekseni boyunca centerline)
            z_vals = [float(p[1]) for p in pts]
            min_z = self.mm(min(z_vals) - 10.0)
            max_z = self.mm(max(z_vals) + 10.0)
            centerline = self.sketch_mgr.CreateCenterLine(0.0, min_z, 0.0, 0.0, max_z, 0.0)
            for i in range(len(pts)):
                p1 = pts[i]
                p2 = pts[(i + 1) % len(pts)]
                self.sketch_mgr.CreateLine(
                    self.mm(p1[0]), self.mm(p1[1]), 0.0,
                    self.mm(p2[0]), self.mm(p2[1]), 0.0
                )
            if centerline is not None:
                try:
                    sel_fn = getattr(centerline, 'Select4', None) or getattr(centerline, 'Select2', None)
                    if callable(sel_fn):
                        sel_fn(False, None)
                except Exception:
                    pass
        feat = None
        if self.feat_mgr is not None:
            for m_name in ('FeatureRevolve2', 'FeatureRevolve'):
                fn = getattr(self.feat_mgr, m_name, None)
                if callable(fn):
                    try:
                        feat = fn(True, True, False, False, 0, 0, ang_rad, 0.0, False, False, 0.0, 0.0, bool(merge), True, True)
                        if feat is not None:
                            break
                    except Exception:
                        pass
        self.model.ClearSelection2(True)
        self.operations_log.append(f"revolve_profile(angle={angle_deg}deg)")
        return feat

    def rebuild(self):
        """Modeli yeniden oluşturur ve ekrana sığdırır."""
        self.model.EditRebuild3()
        try:
            if self.raw_model is not None:
                vf = getattr(self.raw_model, 'ViewZoomtofit2', None)
                if callable(vf):
                    vf()
        except Exception:
            pass


def _get_solid_bodies(model):
    """Aktif Part dokümanındaki katı gövdeleri (IBody2 listesi) döndürür."""
    if model is None:
        return []
    for attr in ('GetBodies2',):
        fn = getattr(model, attr, None)
        if fn is not None:
            try:
                # 0 = swSolidBody
                res = fn(0, True) if callable(fn) else fn
                if res:
                    return list(res)
            except Exception:
                try:
                    res = fn(0, False)
                    if res:
                        return list(res)
                except Exception:
                    pass
    return []


def _count_features_and_sketches(model):
    """Aktif modeldeki unsur ve eskiz sayılarını ve isimlerini döndürür."""
    features = []
    sketches = []
    if model is None:
        return features, sketches
    try:
        feat = getattr(model, 'FirstFeature', None)
        feat = feat() if callable(feat) else feat
        guard = 0
        ignore_types = {
            'OriginProfileFeature', 'RefPlane', 'SensorFolder', 'MaterialFolder',
            'HistoryFolder', 'SelectionSetFolder', 'CommentsFolder', 'FavoriteFolder',
            'SurfaceBodyFolder', 'SolidBodyFolder', 'DocsFolder', 'DetailCabinet',
            'AmbientLight', 'DirectionLight', 'SketchBitmap'
        }
        while feat is not None and guard < 300:
            guard += 1
            try:
                tn = feat.GetTypeName2
                tname = tn() if callable(tn) else str(tn)
                nm = getattr(feat, 'Name', '')
                nm = nm() if callable(nm) else str(nm)
                if tname in ('ProfileFeature', '3DProfileFeature'):
                    sketches.append({'name': nm, 'is_visible': True, 'profiles_count': 1})
                elif tname and tname not in ignore_types:
                    features.append({'name': nm, 'type': tname})
            except Exception:
                pass
            nxt = getattr(feat, 'GetNextFeature', None)
            feat = nxt() if callable(nxt) else nxt
    except Exception as e:
        aicad_log(f"[SolidWorks] Feature tarama hatası: {e}")
    return features, sketches


def _inspect_body(body, idx):
    """Tek bir SolidWorks IBody2 nesnesinin bounding box, yüz/kenar ve hacim bilgilerini okur."""
    name = f"Body{idx + 1}"
    try:
        nm = getattr(body, 'Name', None)
        name = (nm() if callable(nm) else str(nm)) or name
    except Exception:
        pass

    min_x_mm = min_y_mm = min_z_mm = 0.0
    max_x_mm = max_y_mm = max_z_mm = 0.0
    try:
        box_fn = getattr(body, 'GetBodyBox', None)
        box = box_fn() if callable(box_fn) else box_fn
        if box and len(box) >= 6:
            # SolidWorks metre döndürür -> mm için * 1000
            min_x_mm = round(float(box[0]) * 1000.0, 2)
            min_y_mm = round(float(box[1]) * 1000.0, 2)
            min_z_mm = round(float(box[2]) * 1000.0, 2)
            max_x_mm = round(float(box[3]) * 1000.0, 2)
            max_y_mm = round(float(box[4]) * 1000.0, 2)
            max_z_mm = round(float(box[5]) * 1000.0, 2)
    except Exception:
        pass

    dx_mm = round(abs(max_x_mm - min_x_mm), 2)
    dy_mm = round(abs(max_y_mm - min_y_mm), 2)
    dz_mm = round(abs(max_z_mm - min_z_mm), 2)

    # Hacim tahmini veya MassProperties: kutu hacminden cm³
    vol_cm3 = round((dx_mm * dy_mm * dz_mm) / 1000.0, 2) if (dx_mm and dy_mm and dz_mm) else 0.0

    faces_count = 0
    edges_count = 0
    cylinder_faces_count = 0
    try:
        fc = getattr(body, 'GetFaceCount', None)
        if fc is not None:
            faces_count = int(fc() if callable(fc) else fc)
        faces = getattr(body, 'GetFaces', None)
        faces_list = (faces() if callable(faces) else faces) or []
        if not faces_count and faces_list:
            faces_count = len(faces_list)
        for face in faces_list:
            try:
                surf = getattr(face, 'GetSurface', None)
                surf = surf() if callable(surf) else surf
                if surf is not None:
                    is_cyl = getattr(surf, 'IsCylinder', None)
                    if bool(is_cyl() if callable(is_cyl) else is_cyl):
                        cylinder_faces_count += 1
            except Exception:
                pass
    except Exception:
        pass

    try:
        ec = getattr(body, 'GetEdgeCount', None)
        if ec is not None:
            edges_count = int(ec() if callable(ec) else ec)
        else:
            edges = getattr(body, 'GetEdges', None)
            edges_list = (edges() if callable(edges) else edges) or []
            edges_count = len(edges_list)
    except Exception:
        pass

    return {
        'name': name,
        'is_solid': True,
        'is_visible': True,
        'faces_count': faces_count,
        'edges_count': edges_count,
        'cylinder_faces_count': cylinder_faces_count,
        'volume_cm3': vol_cm3,
        'bounds_mm': {
            'min': [min_x_mm, min_y_mm, min_z_mm],
            'max': [max_x_mm, max_y_mm, max_z_mm],
        },
        'dimensions_mm': {'width_x': dx_mm, 'length_y': dy_mm, 'height_z': dz_mm},
    }


def inspect_current_design(sw_app=None):
    """Aktif SolidWorks dokümanındaki gövdeleri, unsurları ve boyutları inceler."""
    try:
        app = sw_app or get_sw_app(launch_if_needed=False)
        if not app:
            return {
                'has_design': False,
                'cad_target': 'solidworks',
                'message': 'SolidWorks uygulamasına erişilemedi. Lütfen SolidWorks programını açın.'
            }

        doc = getattr(app, 'ActiveDoc', None)
        doc = doc() if callable(doc) else doc
        if not doc:
            return {
                'has_design': False,
                'cad_target': 'solidworks',
                'message': 'Açık bir SolidWorks parça dokümanı yok (ilk komutta otomatik oluşturulur).'
            }

        doc_name = _get_doc_title(doc)
        raw_bodies = _get_solid_bodies(doc)
        bodies = [_inspect_body(b, i) for i, b in enumerate(raw_bodies)]
        features, sketches = _count_features_and_sketches(doc)

        summary_lines = []
        if not bodies and not sketches:
            summary_lines.append("SolidWorks çalışma alanı şu anda boş (Henüz bir katı gövde veya eskiz yok).")
        else:
            summary_lines.append(f"Aktif SolidWorks Dokümanı: '{doc_name}'")
            if bodies:
                summary_lines.append(f"Mevcut Katı Gövdeler ({len(bodies)} Adet):")
                for b in bodies:
                    dims = b['dimensions_mm']
                    b_min = b['bounds_mm']['min']
                    b_max = b['bounds_mm']['max']
                    summary_lines.append(
                        f" - '{b['name']}': Boyutlar (X={dims['width_x']}mm, Y={dims['length_y']}mm, Z={dims['height_z']}mm) | "
                        f"Sınır Koordinatları: X[{b_min[0]}..{b_max[0]}], Y[{b_min[1]}..{b_max[1]}], Z[{b_min[2]}..{b_max[2]}] mm | "
                        f"Silindirik Yüz: {b['cylinder_faces_count']}"
                    )
            if features:
                summary_lines.append("FeatureManager Unsurları: " + ", ".join(f"'{f['name']}' ({f['type']})" for f in features[:12]))

        total_faces = sum(int(b.get('faces_count', 0) or 0) for b in bodies)
        total_edges = sum(int(b.get('edges_count', 0) or 0) for b in bodies)
        total_cylinder_faces = sum(int(b.get('cylinder_faces_count', 0) or 0) for b in bodies)
        total_volume_cm3 = round(sum(float(b.get('volume_cm3', 0.0) or 0.0) for b in bodies), 2)

        return {
            'has_design': True,
            'cad_target': 'solidworks',
            'doc_name': doc_name,
            'default_units': 'mm',
            'bodies_count': len(bodies),
            'bodies': bodies,
            'sketches_count': len(sketches),
            'sketches': sketches,
            'features_count': len(features),
            'features': features,
            'total_faces': total_faces,
            'total_edges': total_edges,
            'total_cylinder_faces': total_cylinder_faces,
            'total_volume_cm3': total_volume_cm3,
            'summary_text': "\n".join(summary_lines),
        }
    except Exception as e:
        tb = traceback.format_exc()
        aicad_log(f"[SolidWorks] inspect_current_design hatası: {e}\n{tb}")
        return {
            'has_design': False,
            'cad_target': 'solidworks',
            'error': str(e),
            'summary_text': 'SolidWorks tasarım durumu okunamadı.'
        }


def execute_code(code, sw_app=None):
    """Aktif SolidWorks parça dokümanında Python kodunu güvenle yürütür."""
    try:
        # 1. Sözdizimi ön kontrolü (Self-Healing için temiz hata mesajı)
        try:
            ast.parse(code)
        except SyntaxError as syn_err:
            err_msg = (
                f"Üretilen kodda SÖZDİZİMİ HATASI var (satır {syn_err.lineno}): {syn_err.msg}. "
                f"Kod SolidWorks içinde ÇALIŞTIRILMADI; lütfen Python sözdizimini düzeltin."
            )
            aicad_log(f"[SolidWorks] Sözdizimi ön kontrolü hatası: satır {syn_err.lineno}: {syn_err.msg}")
            return {
                'success': False,
                'error': err_msg,
                'traceback': f'SyntaxError: {syn_err.msg} (satır {syn_err.lineno})',
            }

        app = sw_app or get_sw_app(launch_if_needed=True)
        if not app:
            return {
                'success': False,
                'devMode': True,
                'error': (
                    "SolidWorks uygulamasına bağlanılamadı (SldWorks.Application). "
                    "Lütfen SolidWorks programını açın ve tekrar deneyin."
                ),
                'traceback': '',
            }

        raw_model = ensure_active_part(app)
        if not raw_model:
            return {
                'success': False,
                'error': (
                    "SolidWorks içinde aktif bir Parça (Part) dokümanı açılamadı. "
                    "Lütfen SolidWorks'te yeni bir Parça (Ctrl+N -> Part) açın."
                ),
                'traceback': '',
            }

        initial_bodies = len(_get_solid_bodies(raw_model))
        initial_feats, initial_sketches = _count_features_and_sketches(raw_model)
        initial_feat_count = len(initial_feats)
        initial_sketch_count = len(initial_sketches)

        helper = SolidWorksCADHelper(app, raw_model)
        safe_model = helper.model

        exec_scope = {
            'sw': helper,
            'cad': helper,
            'swApp': app,
            'app': app,
            'swModel': safe_model,
            'model': safe_model,
            'Part': safe_model,
            'part': safe_model,
            'featMgr': helper.feat_mgr,
            'sketchMgr': helper.sketch_mgr,
            'selMgr': getattr(raw_model, 'SelectionManager', None),
            'select_plane': helper.select_plane,
            'mm_to_m': SolidWorksCADHelper.mm,
            'math': math,
            'traceback': traceback,
            'win32com': win32com,
            'pythoncom': pythoncom,
            '__name__': '__main__',
        }

        aicad_log(f"[SolidWorks] Kod çalıştırılıyor. Mevcut gövdeler={initial_bodies}, unsurlar={initial_feat_count}")
        aicad_log(f"--- [SOLIDWORKS İCRA EDİLECEK KOD] ---\n{code}\n--- [KOD SONU] ---")

        exec(code, exec_scope)

        if 'run' in exec_scope and callable(exec_scope['run']):
            curr_bodies = len(_get_solid_bodies(raw_model))
            curr_feats, _ = _count_features_and_sketches(raw_model)
            if curr_bodies == initial_bodies and len(curr_feats) == initial_feat_count and not helper.operations_log:
                exec_scope['run'](None)

        helper.rebuild()

        final_bodies_list = _get_solid_bodies(raw_model)
        final_bodies = len(final_bodies_list)
        final_feats, final_sketches = _count_features_and_sketches(raw_model)
        final_feat_count = len(final_feats)
        final_sketch_count = len(final_sketches)

        aicad_log(
            f"[SolidWorks] İcra sonrası: Gövde {initial_bodies}->{final_bodies}, "
            f"Unsur {initial_feat_count}->{final_feat_count}, Eskiz {initial_sketch_count}->{final_sketch_count}"
        )

        if final_bodies <= 0 and final_feat_count <= initial_feat_count and not helper.operations_log:
            sketch_info = ""
            if final_sketch_count > initial_sketch_count:
                sketch_info = f" ({final_sketch_count - initial_sketch_count} adet 2D eskiz çizildi fakat 3D katıya dönüştürülmedi)"
            err_msg = (
                f"Kod çalıştırıldı fakat SolidWorks çalışma alanına HİÇBİR YENİ 3D KATI GÖVDE (Body) veya UNSUR (Feature) EKLENMEDİ{sketch_info}! "
                "Lütfen doğrudan `sw.extrude_cylinder(...)`, `sw.extrude_box(...)`, `sw.cut_hole(...)` yardımcılarını "
                "veya `featMgr.FeatureExtrusion2(...)` çağrısını kullanarak kapalı eskizi 3D katı gövdeye dönüştürün."
            )
            aicad_log(f"[SolidWorks] Geometri doğrulama başarısız: {err_msg}")
            return {'success': False, 'error': err_msg, 'traceback': err_msg}

        new_body_names = []
        for b in final_bodies_list[initial_bodies:]:
            try:
                nm = getattr(b, 'Name', None)
                new_body_names.append((nm() if callable(nm) else str(nm)) or 'Katı Gövde')
            except Exception:
                new_body_names.append('Katı Gövde')

        return {
            'success': True,
            'cad_target': 'solidworks',
            'new_bodies_count': max(0, final_bodies - initial_bodies),
            'new_bodies': new_body_names,
            'new_features_count': max(len(helper.operations_log), final_feat_count - initial_feat_count),
            'error': None,
            'traceback': None,
        }
    except Exception as e:
        tb = traceback.format_exc()
        aicad_log(f"[SolidWorks] Kod çalıştırma hatası: {e}\n{tb}")
        return {'success': False, 'error': str(e), 'traceback': tb}


def update_parameters(params_dict, sw_app=None):
    """Adam-CAD (CADAM) tarzı canlı parametre/ölçü güncellemesi.

    SolidWorks içindeki boyutları (`IModelDoc2.Parameter("D1@Sketch1")`) metre cinsinden
    günceller ve `EditRebuild3()` çağırır.
    """
    app = sw_app or get_sw_app(launch_if_needed=False)
    if not app:
        return {'success': False, 'error': 'SolidWorks bağlı değil.'}
    doc = getattr(app, 'ActiveDoc', None)
    doc = doc() if callable(doc) else doc
    if not doc:
        return {'success': False, 'error': 'Açık bir SolidWorks dokümanı yok.'}

    updated = []
    for key, val in (params_dict or {}).items():
        try:
            val_m = float(val) / 1000.0
            param = doc.Parameter(str(key))
            if param is not None:
                param.SystemValue = val_m
                updated.append(key)
        except Exception:
            pass
    try:
        doc.EditRebuild3()
    except Exception:
        pass
    return {'success': True, 'updated': updated}


def capture_viewport_image(width=900, height=600, sw_app=None):
    """Aktif SolidWorks viewport'unun ekran görüntüsünü base64 data URL olarak döndürür."""
    try:
        app = sw_app or get_sw_app(launch_if_needed=False)
        if not app:
            return {'success': False, 'error': 'SolidWorks bağlı değil.'}
        doc = getattr(app, 'ActiveDoc', None)
        doc = doc() if callable(doc) else doc
        if not doc:
            return {'success': False, 'error': 'Aktif SolidWorks dokümanı yok.'}

        fd, bmp_path = tempfile.mkstemp(suffix='.bmp')
        os.close(fd)
        try:
            save_fn = getattr(doc, 'SaveBMP', None)
            ok = save_fn(bmp_path, int(width), int(height)) if callable(save_fn) else False
            if not ok or not os.path.isfile(bmp_path):
                return {'success': False, 'error': 'SolidWorks SaveBMP başarısız oldu.'}

            # Varsa Pillow ile PNG'ye çevir, yoksa doğrudan BMP base64 döndür
            try:
                from PIL import Image
                import io
                with Image.open(bmp_path) as im:
                    buf = io.BytesIO()
                    im.save(buf, format='PNG')
                    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
                return {'success': True, 'image': 'data:image/png;base64,' + b64}
            except Exception:
                with open(bmp_path, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode('ascii')
                return {'success': True, 'image': 'data:image/bmp;base64,' + b64}
        finally:
            try:
                os.remove(bmp_path)
            except Exception:
                pass
    except Exception as e:
        tb = traceback.format_exc()
        aicad_log(f"[SolidWorks] capture_viewport_image hatası: {e}\n{tb}")
        return {'success': False, 'error': str(e)}
