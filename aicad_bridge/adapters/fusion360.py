"""Fusion 360 CAD adapterı: tasarım durumu okuma ve kod yürütme."""

import ast
import math
import os
import traceback

import adsk.core
import adsk.fusion

from aicad_bridge import runtime
from aicad_bridge.runtime import aicad_log


class SafeUIWrapper:
    """Yapay zeka scriptlerinin ekrana bloklayıcı modal messagebox açmasını engeller ve hataları yakalar."""
    def __init__(self, real_ui):
        self._real_ui = real_ui
        self.intercepted_errors = []

    def messageBox(self, text, *args, **kwargs):
        msg = str(text)
        aicad_log(f"[SafeUI] Script modal messagebox çağrısı engellendi: {msg[:160]}")
        if any(w in msg for w in ("Hata", "Error", "Traceback", "RuntimeError", "Exception", "bulunamadı")):
            self.intercepted_errors.append(msg)
        return 0

    def __getattr__(self, name):
        return getattr(self._real_ui, name) if self._real_ui else None


def inspect_current_design():
    """Aktif Fusion 360 dokümanındaki gövdeleri, eskizleri ve boyutları detaylı inceler."""
    try:
        if not runtime.app:
            runtime.app = adsk.core.Application.get()
        app = runtime.app
        if not app:
            return {'has_design': False, 'message': 'Fusion 360 uygulamasına erişilemedi.'}

        doc = app.activeDocument
        if not doc:
            return {'has_design': False, 'message': 'Açık bir Fusion 360 dokümanı yok.'}

        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)
        if not design:
            return {
                'has_design': False,
                'doc_name': doc.name,
                'message': 'Aktif doküman bir Fusion 360 tasarım dokümanı değil.'
            }

        root_comp = design.rootComponent
        units_mgr = design.unitsManager
        default_units = units_mgr.defaultLengthUnits or 'mm'

        bodies = []
        for i in range(root_comp.bRepBodies.count):
            try:
                body = root_comp.bRepBodies.item(i)
                bbox = body.boundingBox
                # Fusion API dahili olarak cm kullanır; mm'ye çevirelim:
                min_x_mm = round(bbox.minPoint.x * 10, 2)
                min_y_mm = round(bbox.minPoint.y * 10, 2)
                min_z_mm = round(bbox.minPoint.z * 10, 2)
                max_x_mm = round(bbox.maxPoint.x * 10, 2)
                max_y_mm = round(bbox.maxPoint.y * 10, 2)
                max_z_mm = round(bbox.maxPoint.z * 10, 2)

                dx_mm = round(abs(max_x_mm - min_x_mm), 2)
                dy_mm = round(abs(max_y_mm - min_y_mm), 2)
                dz_mm = round(abs(max_z_mm - min_z_mm), 2)

                vol_cm3 = round(body.volume, 2) if hasattr(body, 'volume') else 0.0

                # Yüz/kenar sayıları ve silindirik yüz sayısı (delik doğrulaması için)
                faces_count = 0
                edges_count = 0
                cylinder_faces_count = 0
                if hasattr(body, 'faces'):
                    faces_count = body.faces.count
                    for fi in range(body.faces.count):
                        try:
                            face_geom = body.faces.item(fi).geometry
                            if face_geom and face_geom.objectType == adsk.core.Cylinder.classType():
                                cylinder_faces_count += 1
                        except Exception:
                            pass
                if hasattr(body, 'edges'):
                    edges_count = body.edges.count

                bodies.append({
                    'name': body.name,
                    'is_solid': body.isSolid,
                    'is_visible': body.isVisible,
                    'faces_count': faces_count,
                    'edges_count': edges_count,
                    'cylinder_faces_count': cylinder_faces_count,
                    'volume_cm3': vol_cm3,
                    'bounds_mm': {
                        'min': [min_x_mm, min_y_mm, min_z_mm],
                        'max': [max_x_mm, max_y_mm, max_z_mm]
                    },
                    'dimensions_mm': {'width_x': dx_mm, 'length_y': dy_mm, 'height_z': dz_mm}
                })
            except Exception as b_err:
                aicad_log(f"Gövde {i} okunurken hata: {b_err}")

        sketches = []
        for i in range(root_comp.sketches.count):
            try:
                sk = root_comp.sketches.item(i)
                sketches.append({
                    'name': sk.name,
                    'is_visible': sk.isVisible,
                    'profiles_count': sk.profiles.count
                })
            except Exception as sk_err:
                aicad_log(f"Eskiz {i} okunurken hata: {sk_err}")

        summary_lines = []
        if not bodies and not sketches:
            summary_lines.append("Fusion 360 çalışma alanı şu anda boş (Henüz bir gövde veya eskiz yok).")
        else:
            summary_lines.append(f"Aktif Doküman: '{doc.name}'")
            if bodies:
                summary_lines.append(f"Mevcut Katı Gövdeler ({len(bodies)} Adet):")
                for b in bodies:
                    dims = b['dimensions_mm']
                    b_min = b['bounds_mm']['min']
                    b_max = b['bounds_mm']['max']
                    summary_lines.append(
                        f" - '{b['name']}': Boyutlar (X={dims['width_x']}mm, Y={dims['length_y']}mm, Z={dims['height_z']}mm) | "
                        f"Sınır Koordinatları: X[{b_min[0]}..{b_max[0]}], Y[{b_min[1]}..{b_max[1]}], Z[{b_min[2]}..{b_max[2]}] mm | "
                        f"Hacim: {b['volume_cm3']} cm³"
                    )
            if sketches:
                summary_lines.append(f"Mevcut Eskizler: " + ", ".join([f"'{s['name']}' ({s['profiles_count']} profil)" for s in sketches]))

        summary_text = "\n".join(summary_lines)

        # Toplam metrikler (iki aşamalı hattın geometrik doğrulaması için)
        total_faces = sum(int(b.get('faces_count', 0) or 0) for b in bodies)
        total_edges = sum(int(b.get('edges_count', 0) or 0) for b in bodies)
        total_cylinder_faces = sum(int(b.get('cylinder_faces_count', 0) or 0) for b in bodies)
        total_volume_cm3 = round(sum(float(b.get('volume_cm3', 0.0) or 0.0) for b in bodies), 2)

        return {
            'has_design': True,
            'doc_name': doc.name,
            'default_units': default_units,
            'bodies_count': len(bodies),
            'bodies': bodies,
            'sketches_count': len(sketches),
            'sketches': sketches,
            'total_faces': total_faces,
            'total_edges': total_edges,
            'total_cylinder_faces': total_cylinder_faces,
            'total_volume_cm3': total_volume_cm3,
            'summary_text': summary_text
        }
    except Exception as e:
        tb = traceback.format_exc()
        aicad_log(f"inspect_current_design hatası: {e}\n{tb}")
        return {'has_design': False, 'error': str(e), 'summary_text': 'Tasarım durumu okunamadı.'}


def execute_code(code):
    """Ana thread üzerinde aktif Fusion dokümanında Python kodunu güvenle yürütür."""
    try:
        if not runtime.app:
            runtime.app = adsk.core.Application.get()
        app = runtime.app
        if not runtime.ui and app:
            runtime.ui = app.userInterface
        ui = runtime.ui

        design = adsk.fusion.Design.cast(app.activeProduct) if app else None
        if not design and app:
            aicad_log("Aktif tasarım dokümanı bulunamadı, yeni bir doküman açılıyor...")
            app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
            design = adsk.fusion.Design.cast(app.activeProduct)

        root_comp = design.rootComponent if design else None
        initial_bodies = root_comp.bRepBodies.count if root_comp else 0
        initial_features = root_comp.features.count if root_comp else 0
        initial_sketches = root_comp.sketches.count if root_comp else 0

        aicad_log(f"Kod çalıştırılıyor. rootComp={'Var' if root_comp else 'Yok'}, mevcut gövdeler={initial_bodies}")
        aicad_log(f"--- [İCRA EDİLECEK KOD BAŞLANGICI] ---\n{code}\n--- [İCRA EDİLECEK KOD BİTİŞİ] ---")

        # Sözdizimi ön kontrolü: kodu çalıştırmadan önce ast.parse ile doğrula.
        # Böylece hatalı kod exec'e hiç girmez ve Self-Healing sistemine temiz bir
        # hata mesajı iletilir (satır numarasıyla).
        try:
            ast.parse(code)
        except SyntaxError as syn_err:
            err_msg = (f"Üretilen kodda SÖZDİZİMİ HATASI var (satır {syn_err.lineno}): {syn_err.msg}. "
                       f"Kod Fusion 360 içinde ÇALIŞTIRILMADI; lütfen Python sözdizimini düzeltin.")
            aicad_log(f"Sözdizimi ön kontrolü hatası: satır {syn_err.lineno}: {syn_err.msg}")
            return {'success': False, 'error': err_msg,
                    'traceback': f'SyntaxError: {syn_err.msg} (satır {syn_err.lineno})'}

        safe_ui = SafeUIWrapper(ui)
        exec_scope = {
            'adsk': adsk,
            'app': app,
            'ui': safe_ui,
            'design': design,
            'rootComp': root_comp,
            'math': math,
            'traceback': traceback,
            '__name__': '__main__'
        }
        exec(code, exec_scope)

        # Eğer script run(context) fonksiyonu tanımladıysa ve gövde/unsur henüz eklenmediyse çalıştır
        if 'run' in exec_scope and callable(exec_scope['run']):
            curr_bodies = root_comp.bRepBodies.count if root_comp else 0
            curr_features = root_comp.features.count if root_comp else 0
            if curr_bodies == initial_bodies and curr_features == initial_features:
                aicad_log("run(context) fonksiyonu doğrudan çağrılıyor...")
                exec_scope['run'](None)

        if safe_ui.intercepted_errors:
            err_msg = safe_ui.intercepted_errors[-1]
            aicad_log(f"Script içerisinden yakalanan hata (modal engellendi): {err_msg}")
            return {'success': False, 'error': err_msg, 'traceback': err_msg}

        final_bodies = root_comp.bRepBodies.count if root_comp else 0
        final_features = root_comp.features.count if root_comp else 0
        final_sketches = root_comp.sketches.count if root_comp else 0

        aicad_log(f"İcra sonrası durum: Gövde {initial_bodies}->{final_bodies}, Unsur {initial_features}->{final_features}, Çizim {initial_sketches}->{final_sketches}")

        # Doğrulama: Yeni bir 3D katı gövde veya unsur eklendi mi?
        if final_bodies <= initial_bodies and final_features <= initial_features:
            sketch_info = ""
            if final_sketches > initial_sketches:
                sketch_info = f" ({final_sketches - initial_sketches} adet 2D eskiz çizildi fakat katılmadı)"
            err_msg = (
                f"Kod çalıştırıldı fakat Fusion 360 çalışma alanına HİÇBİR YENİ 3D KATI GÖVDE (Body) veya UNSUR (Feature) EKLENMEDİ{sketch_info}! "
                "Yalnızca 2D çizim (eskiz) yapmak yeterli değildir, parça 3D ekranda görünmez. "
                "Lütfen çizdiğiniz profilin kapalı olduğundan emin olun ve mutlaka 'extrudes = rootComp.features.extrudeFeatures' ile "
                "'extrudes.add(extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation))' çağrısı yaparak "
                "parçayı 3D katı gövdeye dönüştürün."
            )
            aicad_log(f"CAD geometri doğrulama başarısız: {err_msg}")
            return {'success': False, 'error': err_msg, 'traceback': err_msg}

        new_body_names = []
        if root_comp:
            for bi in range(initial_bodies, final_bodies):
                try:
                    new_body_names.append(root_comp.bRepBodies.item(bi).name)
                except Exception:
                    pass

        aicad_log(f"Kod Fusion 360 içinde başarıyla yürütüldü. Yeni eklenen gövdeler: {new_body_names}")
        return {
            'success': True,
            'new_bodies_count': final_bodies - initial_bodies,
            'new_bodies': new_body_names,
            'new_features_count': final_features - initial_features,
            'error': None,
            'traceback': None
        }
    except Exception as e:
        tb = traceback.format_exc()
        aicad_log(f"Kod çalıştırma hatası: {str(e)}\n{tb}")
        return {'success': False, 'error': str(e), 'traceback': tb}


def capture_viewport_image(width=900, height=600):
    """Aktif viewport'un ekran görüntüsünü base64 data URL olarak döndürür.

    Vision destekli sağlayıcılarda "model komuta uyuyor mu" görsel doğrulaması
    için kullanılır. Fusion ana thread'inden çağrılmalıdır.
    """
    import base64
    import tempfile
    try:
        if not runtime.app:
            runtime.app = adsk.core.Application.get()
        viewport = runtime.app.activeViewport
        if not viewport:
            return {'success': False, 'error': 'Aktif viewport bulunamadı.'}

        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        try:
            viewport.saveAsImageFile(path, width, height)
            with open(path, 'rb') as img_file:
                b64 = base64.b64encode(img_file.read()).decode('ascii')
            return {'success': True, 'image': 'data:image/png;base64,' + b64}
        finally:
            try:
                os.remove(path)
            except Exception:
                pass
    except Exception as e:
        tb = traceback.format_exc()
        aicad_log(f"capture_viewport_image hatası: {e}\n{tb}")
        return {'success': False, 'error': str(e)}
