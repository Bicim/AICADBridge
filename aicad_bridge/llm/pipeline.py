"""İki aşamalı (Planner + Coder) CAD üretim hattı: plan doğrulama, prompt kurma ve geometrik doğrulama.

Mimari:
    - LLM çağrılarının kendisi tarayıcı/JS tarafında yapılır (mevcut callLLM altyapısı,
      thinking modu, CORS fallback dahil). Bu modül adsk'a BAĞLI DEĞİLDİR.
    - Buradaki işler: Planner/Coder promptlarını kurmak, plan JSON'unu şemaya göre
      doğrulamak, snippets/loader.py ile few-shot örnek seçmek ve inspect çıktısını
      plan beklentileriyle karşılaştırmak. Birim testlerinde bağımsız çalışır.
    - Fusion ana thread'ine erişim gerektiren işler (tasarım inceleme, viewport
      görüntüsü) çağıran taraf tarafından enjekte edilir (run_pipeline_helper):
      palet doğrudan, HTTP köprüsü custom event üzerinden enjekte eder.
"""

import json
import os
import re
import sys


# --------------------------------------------------------------------------
# Snippet kütüphanesi (repo kökündeki snippets/loader.py)
# --------------------------------------------------------------------------
def _import_snippets_loader():
    try:
        from snippets import loader
        return loader
    except Exception:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if root not in sys.path:
            sys.path.insert(0, root)
        from snippets import loader
        return loader


try:
    _SNIPPETS = _import_snippets_loader()
except Exception:
    _SNIPPETS = None

# Temel feature_type'lar (index.json ile uyumlu; index varsa birleşim kullanılır)
BASE_FEATURE_TYPES = {
    'extrude', 'cut', 'hole', 'fillet', 'chamfer', 'pattern', 'mirror',
    'shell', 'revolve', 'sweep', 'loft', 'parameter', 'construction', 'combine',
}

KNOWN_FEATURE_TYPES = set(BASE_FEATURE_TYPES)
try:
    if _SNIPPETS is not None:
        for _entry in _SNIPPETS.load_index().get('snippets', []):
            KNOWN_FEATURE_TYPES.add(_entry.get('feature_type', ''))
    KNOWN_FEATURE_TYPES.discard('')
except Exception:
    pass

# Yaygın eş anlamlı / tekil-çoğul tür adları -> normalize edilmiş feature_type
_TYPE_ALIASES = {
    'extrude': 'extrude', 'extrusion': 'extrude', 'solid': 'extrude', 'body': 'extrude',
    'sketch_circle_extrude': 'extrude', 'sketch_rectangle_extrude': 'extrude',
    'cut': 'cut', 'extrude_cut': 'cut', 'pocket': 'cut', 'remove': 'cut', 'subtract': 'cut',
    'hole': 'hole', 'holes': 'hole', 'drill': 'hole', 'hole_feature': 'hole',
    'fillet': 'fillet', 'fillets': 'fillet', 'round': 'fillet', 'fillet_edges': 'fillet',
    'chamfer': 'chamfer', 'chamfers': 'chamfer', 'bevel': 'chamfer', 'chamfer_edges': 'chamfer',
    'pattern': 'pattern', 'circular_pattern': 'pattern', 'rectangular_pattern': 'pattern',
    'array': 'pattern', 'repeat': 'pattern',
    'mirror': 'mirror', 'mirror_feature': 'mirror', 'reflect': 'mirror',
    'shell': 'shell', 'shell_body': 'shell', 'hollow': 'shell',
    'revolve': 'revolve', 'revolve_profile': 'revolve', 'rotate': 'revolve',
    'sweep': 'sweep', 'sweep_path': 'sweep',
    'loft': 'loft', 'loft_profiles': 'loft', 'blend': 'loft',
    'parameter': 'parameter', 'parameters': 'parameter', 'user_parameter': 'parameter',
    'user_parameters': 'parameter',
    'construction': 'construction', 'construction_plane': 'construction', 'plane': 'construction',
    'combine': 'combine', 'combine_bodies': 'combine', 'join': 'combine', 'boolean': 'combine',
}


# --------------------------------------------------------------------------
# Promptlar
# --------------------------------------------------------------------------
PLANNER_PROMPT = """You are the PLANNER module of "AI CAD Studio" for Autodesk Fusion 360.
Your ONLY job: convert the user's modeling request into a JSON feature plan.

STRICT OUTPUT RULES:
- Return ONLY valid JSON. No markdown fences, no explanations, no Python code.
- If the request is purely conversational (greeting, general question, NOT a CAD command), return exactly: {"chat": true}

JSON SCHEMA:
{"chat": false,
 "parameters": [{"name": "cap_mm", "value": 40, "unit": "mm"}],
 "features": [{"id": "govde", "type": "extrude", "description": "40mm capinda silindir govde", "params": {}}]}

ALLOWED "type" VALUES (EXACTLY these, nothing else):
- extrude: yeni kati govde (daire/dikdortgen/cokgen profil) — params ornegi: {"shape": "circle", "diameter_mm": 40, "height_mm": 20, "x_mm": 0, "y_mm": 0}
- cut: mevcut govdeden malzeme kaldirma (yuva/oluk/pencere)
- hole: delik(ler) — params: {"count": 4, "diameter_mm": 5, "depth_mm": 10}
- fillet: kenar yuvarlatma — params: {"radius_mm": 3}
- chamfer: pah — params: {"distance_mm": 2}
- pattern: cogaltma — params: {"kind": "circular", "count": 6, "spacing_mm": 20, "total_angle_deg": 360}
- mirror: duzlem boyunca aynalama
- shell: ici bos kabuk — params: {"wall_thickness_mm": 2}
- revolve: eksende dondurerek govde
- sweep: yol boyunca tarama
- loft: kesitler arasi gecis
- parameter: yalnizca kullanici parametresi tanimlama
- construction: referans duzlem/geometri
- combine: govde birlestirme/kesme (boolean)

PLANNING RULES:
- "parameters": tum onemli olculeri user parameter olarak listele (mm varsayilan).
- "features": mantikli URETIM SIRASINDA olmali — once ana govdeler (extrude/revolve/sweep/loft), sonra delik/kesmeler (hole/cut), en son yuzey islemleri (fillet/chamfer) ve cogaltmalar (pattern/mirror).
- Kullanicinin verdigi sayilari aynen kullan; verilmeyenler icin makul varsayilanlar sec ve description'da belirt.
- Her feature benzersiz ve anlami bir "id" almali (govde, tabla, delik_1, ...).
- Plan normalde en az bir kati govde ureten unsur (extrude/revolve/sweep/loft) ICERMELI; yalnizca mevcut tasarimi degistiren isteklerde (delik ac, kenarlari yuvarlat) bu sart gerekmez.
- Mevcut tasarimi degistiriyorsan yalnizca yeni/degisen unsurlari planla ve description'larda mevcut govde adlarina basvur.
"""

CODER_PROMPT = """You are the CODER module of "AI CAD Studio" for Autodesk Fusion 360.
You write ONE self-contained Fusion 360 Python script that implements ONE feature of a larger plan.

OUTPUT: ONLY a single ```python ... ``` code block. Nothing else.
CRITICAL RULES:
- INTERNAL UNITS: Fusion 360 API uses CENTIMETERS. Convert every mm value with /10.
- Always import adsk.core, adsk.fusion, math.
- Root component access: app = adsk.core.Application.get(); design = adsk.fusion.Design.cast(app.activeProduct); rootComp = design.rootComponent
- New solids MUST be created with extrudes/revolveFeatures/sweepFeatures/loftFeatures .add(...) using adsk.fusion.FeatureOperations.NewBodyFeatureOperation. Never leave a closed profile un-extruded.
- Cut/Join ONLY when the profile physically intersects an existing body; otherwise use NewBodyFeatureOperation.
- If the plan provides "parameters", define them as USER PARAMETERS (design.userParameters.add(name, adsk.core.ValueInput.createByString('... mm'), 'mm', ...)) and use them in the code.
- Prefer REAL Fusion features over manual sketch-cuts when applicable: holeFeatures for holes, filletFeatures for rounds, chamferFeatures for chamfers.
- Position new geometry relative to the previously created steps/features listed in the prompt.
- STRICT BAN: ui.messageBox(...), try/except that swallows errors. Let exceptions raise so the Self-Healing system can repair them.
"""

SOLIDWORKS_CODER_PROMPT = """You are the CODER module of "AI CAD Studio (SolidWorks · Adam-CAD Edition)" for SolidWorks.
You write ONE self-contained SolidWorks Python script that implements ONE feature of a larger plan.

OUTPUT: ONLY a single ```python ... ``` code block. Nothing else.
CRITICAL RULES:
- DO NOT import adsk.core or adsk.fusion! This is SolidWorks, NOT Fusion 360.
- The helper object `sw` (and `cad`) plus raw COM objects (`swApp`, `swModel`, `featMgr`, `sketchMgr`, `math`) are ALREADY injected into the global execution scope.
- Use `sw` helper methods where ALL dimensions are in MILLIMETERS (mm):
  * `sw.define_parameter(name, value_mm)`
  * `sw.extrude_cylinder(diameter_mm, height_mm, x_mm=0, y_mm=0, plane='top')`
  * `sw.extrude_box(width_mm, length_mm, height_mm, x_mm=0, y_mm=0, plane='top', centered=True)`
  * `sw.extrude_polygon(sides, diameter_mm, height_mm, x_mm=0, y_mm=0, plane='top')`
  * `sw.cut_hole(diameter_mm, depth_mm=None, x_mm=0, y_mm=0, plane='top', through_all=True)`
  * `sw.cut_bolt_circle(hole_diameter_mm, bolt_circle_diameter_mm, count, depth_mm=None, plane='top')`
  * `sw.cut_box(width_mm, length_mm, depth_mm=None, x_mm=0, y_mm=0, plane='top')`
  * `sw.fillet_edges(radius_mm)`
  * `sw.chamfer_edges(distance_mm, angle_deg=45)`
  * `sw.shell_body(wall_thickness_mm)`
  * `sw.revolve_profile(points_mm=[(0,0), (r1,0), (r2,h), (0,h)], angle_deg=360, plane='front')`
  * `sw.rebuild()`
- If using raw COM (`sketchMgr` / `featMgr`), remember SolidWorks internal units are METERS (`mm / 1000.0`).
- STRICT BAN: Never swallow exceptions with try/except pass.
"""


# --------------------------------------------------------------------------
# Plan JSON çözümleme ve doğrulama
# --------------------------------------------------------------------------
def parse_plan_json(text):
    """LLM yanıtını plan JSON'una çevirir; çözümlenemezse None döner.

    Sırasıyla denenir: ```json çiti, doğrudan metin, ilk '{' ... son '}' dilimi.
    """
    if not text or not text.strip():
        return None
    candidates = []
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.I)
    if fence:
        candidates.append(fence.group(1).strip())
    candidates.append(text.strip())
    start = text.find('{')
    end = text.rfind('}')
    if 0 <= start < end:
        candidates.append(text[start:end + 1])
    for cand in candidates:
        if not cand or not cand.startswith('{'):
            continue
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return None


def validate_plan(plan):
    """Plan sözlüğünü şemaya göre doğrular ve normalize eder.

    Döner: (ok, normalized_plan, hata_mesajı)
    """
    if not isinstance(plan, dict):
        return False, None, 'Plan bir JSON nesnesi değil.'

    if plan.get('chat') is True:
        return True, {'chat': True, 'parameters': [], 'features': []}, ''

    features = plan.get('features')
    if not isinstance(features, list) or not features:
        return False, None, '"features" boş veya liste değil; en az bir unsur gerekli (veya sohbet için {"chat": true}).'

    norm_features = []
    seen_ids = {}
    for i, f in enumerate(features):
        if not isinstance(f, dict):
            return False, None, f'features[{i}] bir nesne değil.'
        ftype = str(f.get('type', '')).strip().lower()
        ftype = _TYPE_ALIASES.get(ftype, ftype)
        if ftype not in KNOWN_FEATURE_TYPES:
            allowed = ', '.join(sorted(KNOWN_FEATURE_TYPES))
            return False, None, f'features[{i}].type="{ftype}" bilinmiyor. İzinli türler: {allowed}.'
        fid = str(f.get('id') or 'feature_{}'.format(i + 1)).strip() or 'feature_{}'.format(i + 1)
        if fid in seen_ids:
            seen_ids[fid] += 1
            fid = '{}_{}'.format(fid, seen_ids[fid])
        else:
            seen_ids[fid] = 1
        params = f.get('params') if isinstance(f.get('params'), dict) else {}
        desc = str(f.get('description', '')).strip()
        if not desc:
            desc = '{} ({})'.format(fid, ftype)
        norm_features.append({'id': fid, 'type': ftype, 'description': desc, 'params': params})

    parameters = []
    raw_params = plan.get('parameters')
    if isinstance(raw_params, list):
        for p in raw_params:
            if isinstance(p, dict) and p.get('name'):
                parameters.append({
                    'name': str(p['name']),
                    'value': p.get('value'),
                    'unit': str(p.get('unit', 'mm')) or 'mm',
                })

    return True, {'chat': False, 'parameters': parameters, 'features': norm_features}, ''


# --------------------------------------------------------------------------
# Basit komut kuralı (planner'ı atla)
# --------------------------------------------------------------------------
# Basit komut kalıpları — Türkçe ekler için gövde + \w* sonek eşleşmesi kullanılır.
# NOT: Sonunda k bulunan köklerde ünsüz yumuşaması (k->ğ: delik->deliği,
# yükseklik->yüksekliği) için [kğ] alternatifi kullanılır.
_SIMPLE_CYLINDER_RE = re.compile(
    r'\b(silindir\w*|boru\w*|mil\b|çubuk\w*|daire\w*|çember\w*|dis[kğ]\w*|cylinder\w*|tube\w*|rod\b|circle\w*|disc\w*)', re.I)
_SIMPLE_BOX_RE = re.compile(
    r'\b(kutu\w*|dikdörtgen\w*|kare\w*|plaka\w*|blo[kğ]\w*|taban\w*|box\w*|rectangle\w*|square\w*|plate\w*|block\w*)', re.I)
# Ekli Türkçe biçimler ("deliği", "yuvarlatılmış"...) nedeniyle gövde kökleriyle aranır
_COMPLEX_HINT_RE = re.compile(
    r'(deli[kğ]|delme|pah\b|yuvarlat|radyus|radius|desen|pattern|ayna|mirror|kabu[kğ]|shell|içi\s*boş|revolve|döndür|sweep|loft|birleştir|combine|kanal|olu[kğ]|vida|yıldız|çokgen|cokgen|polygon|koni|halka|huni)', re.I)
_NUM = r'(\d+(?:[.,]\d+)?)'


def _num(pattern, text):
    m = re.search(pattern, text, re.I)
    if m:
        try:
            return float(m.group(1).replace(',', '.'))
        except ValueError:
            return None
    return None


def is_simple_command(prompt):
    """Tek silindir/kutu gibi basit komutlarda planner LLM çağrısını atlamak için kural.

    Uygunsa hazır tek-feature'lı plan döner, değilse None döner.
    """
    if not prompt or not prompt.strip():
        return None
    t = prompt.strip()
    if len(t) > 200 or _COMPLEX_HINT_RE.search(t):
        return None
    cyl = bool(_SIMPLE_CYLINDER_RE.search(t))
    box = bool(_SIMPLE_BOX_RE.search(t))
    if cyl == box:  # ikisi birden veya hiçbiri -> basit değil
        return None
    shape = 'circle' if cyl else 'rect'
    params = {'shape': shape}
    dia = (_num(r'(?:çap\w*|diameter|kalınlı[kğ]\w*|kalinli[kğ]\w*)\s*[:=]?\s*' + _NUM, t)
           or _num(_NUM + r'\s*(?:mm)?\s*(?:çap\w*|diameter)', t))
    height = _num(r'(?:yüksekli[kğ]\w*|height|boy\w*|uzun\w*)\s*[:=]?\s*' + _NUM, t)
    width = _num(r'(?:genişli[kğ]\w*|genisli[kğ]\w*|width|en\b)\s*[:=]?\s*' + _NUM, t)
    length = _num(r'(?:uzunlu[kğ]\w*|length|derinli[kğ]\w*|depth)\s*[:=]?\s*' + _NUM, t)
    if shape == 'circle':
        if dia is not None:
            params['diameter_mm'] = dia
        if height is None and length is not None:
            height = length
        if height is not None:
            params['height_mm'] = height
    else:
        for key, val in (('width_mm', width), ('length_mm', length or dia), ('height_mm', height)):
            if val is not None:
                params[key] = val
    return {
        'chat': False,
        'parameters': [],
        'features': [{
            'id': 'govde',
            'type': 'extrude',
            'description': t,
            'params': params,
        }],
    }


# --------------------------------------------------------------------------
# Coder prompt kurma (few-shot snippet seçimi dahil)
# --------------------------------------------------------------------------
def _is_sw(cad_target):
    return str(cad_target or '').strip().lower() in ('solidworks', 'sw', 'adacad', 'adamcad', 'cadam')


def _select_snippets(feature, limit=2, cad_target='fusion360'):
    """Feature türüne/anhtar kelimelerine uyan örnek snippet kodlarını döndürür."""
    if _SNIPPETS is None:
        return []
    entries = []
    try:
        entries = _SNIPPETS.find_snippets(
            feature_type=feature.get('type', ''), include_code=True, cad_target=cad_target
        ) or []
    except TypeError:
        entries = _SNIPPETS.find_snippets(feature_type=feature.get('type', ''), include_code=True) or []
    except Exception:
        entries = []
    if not entries:
        desc = feature.get('description') or ''
        for word in re.split(r'[\s,;.]+', desc)[:4]:
            if len(word) >= 4:
                try:
                    entries = _SNIPPETS.find_snippets(
                        keyword=word, include_code=True, cad_target=cad_target
                    ) or []
                except TypeError:
                    entries = _SNIPPETS.find_snippets(keyword=word, include_code=True) or []
                except Exception:
                    entries = []
                if entries:
                    break
    out = []
    for e in entries[:limit]:
        code = (e.get('code') or '').strip()
        if code:
            out.append('# ÖRNEK ({}, {}):\n{}'.format(e.get('id'), e.get('feature_type'), code))
    return out


def build_coder_prompt(plan, feature, prev_summaries=None, context_summary=None, cad_target='fusion360'):
    """Bir feature için Coder (system, user) promptunu kurar."""
    sw_mode = _is_sw(cad_target)
    snippets = _select_snippets(feature, cad_target=cad_target)
    parts = []
    if sw_mode:
        parts.append('[GÖREV] Aşağıdaki planın SADECE belirtilen unsuru için SolidWorks (Adam-CAD `sw` helper) Python kodu yaz.')
    else:
        parts.append('[GÖREV] Aşağıdaki planın SADECE belirtilen unsuru için Fusion 360 Python kodu yaz.')
    parts.append('[PLAN PARAMETRELERİ]: ' + json.dumps(plan.get('parameters', []), ensure_ascii=False))
    parts.append('[PLANIN TAMAMI]: ' + json.dumps({'features': plan.get('features', [])}, ensure_ascii=False))
    parts.append('[SIRADAKİ UNSUR]: ' + json.dumps(feature, ensure_ascii=False))
    if prev_summaries:
        parts.append('[ÖNCEKİ ADIMLAR (tamamlandı)]:\n- ' + '\n- '.join(str(s) for s in prev_summaries))
    if context_summary:
        parts.append('[MEVCUT TASARIM DURUMU]:\n' + str(context_summary))
    if snippets:
        parts.append('[REFERANS ÖRNEK KODLAR — aynı API kalıplarını kullan]:\n' + '\n\n'.join(snippets))
    if sw_mode:
        parts.append("[KURALLAR]: adsk.core / adsk.fusion KESİNLİKLE İMPORT ETME; "
                     "doğrudan global `sw` yardımcısını (`sw.extrude_cylinder`, `sw.extrude_box`, `sw.cut_hole`, "
                     "`sw.cut_bolt_circle`, `sw.cut_box`, `sw.fillet_edges`, `sw.chamfer_edges`, `sw.shell_body`, "
                     "`sw.revolve_profile`, `sw.rebuild`) milimetre (mm) ölçüleriyle kullan; hata yutan try/except YASAK.")
    else:
        parts.append("[KURALLAR]: mm değerlerini /10 ile cm'ye çevir; yeni katı için NewBodyFeatureOperation; "
                     "planda parametre varsa userParameters.add ile tanımla ve kullan; delik/yuvarlatma/pah için "
                     "gerçek Fusion özelliklerini (holeFeatures/filletFeatures/chamferFeatures) tercih et; "
                     "ui.messageBox ve hata yutan try/except YASAK.")
    parts.append('SADECE ```python ... ``` bloğu içinde eksiksiz, çalışan kodu döndür.')
    return {'system': SOLIDWORKS_CODER_PROMPT if sw_mode else CODER_PROMPT, 'user': '\n\n'.join(parts)}


def build_correction_prompt(plan, feature, issues, current_code='', prev_summaries=None, context_summary=None, cad_target='fusion360'):
    """Doğrulama uyuşmazlığını açıklayan mesajla Coder düzeltme turu promptunu kurar."""
    sw_mode = _is_sw(cad_target)
    issue_lines = []
    for it in issues:
        issue_lines.append(it.get('text', '') if isinstance(it, dict) else str(it))
    parts = []
    parts.append('[GÖREV] Doğrulama sonucunda uyuşmazlık tespit edildi. Aşağıdaki unsurun kodunu düzelt.')
    parts.append('[UYUŞMAZLIKLAR]:\n- ' + '\n- '.join(l for l in issue_lines if l))
    parts.append('[SIRADAKİ UNSUR]: ' + json.dumps(feature, ensure_ascii=False))
    parts.append('[PLANIN TAMAMI]: ' + json.dumps({'features': plan.get('features', [])}, ensure_ascii=False))
    if prev_summaries:
        parts.append('[ÖNCEKİ ADIMLAR (tamamlandı)]:\n- ' + '\n- '.join(str(s) for s in prev_summaries))
    if context_summary:
        parts.append('[MEVCUT TASARIM DURUMU]:\n' + str(context_summary))
    if current_code:
        parts.append('[MEVCUT KOD (bunu düzelt)]:\n```python\n' + current_code + '\n```')
    parts.append('SADECE ```python ... ``` bloğu içinde düzeltilmiş, eksiksiz kodu döndür.')
    return {'system': SOLIDWORKS_CODER_PROMPT if sw_mode else CODER_PROMPT, 'user': '\n\n'.join(parts)}


# --------------------------------------------------------------------------
# Geometrik doğrulama: plan beklentileri vs. inspect çıktısı
# --------------------------------------------------------------------------
def _param_int(params, keys, default=None):
    for k in keys:
        if k in params:
            try:
                return int(float(params[k]))
            except (TypeError, ValueError):
                continue
    return default


def _metrics_from_state(state):
    """inspect_current_design çıktısından (veya önceden alınan metrik sözlüğünden) toplamları çıkarır."""
    if not state or not state.get('has_design'):
        return {'bodies': 0, 'faces': 0, 'edges': 0, 'cylinder_faces': 0, 'volume': 0.0}
    bodies = [b for b in (state.get('bodies') or []) if isinstance(b, dict)]

    def total(field):
        return sum(int(b.get(field, 0) or 0) for b in bodies)

    return {
        'bodies': int(state.get('bodies_count', len(bodies)) or 0),
        'faces': int(state.get('total_faces', 0) or total('faces_count')),
        'edges': int(state.get('total_edges', 0) or total('edges_count')),
        'cylinder_faces': int(state.get('total_cylinder_faces', 0) or total('cylinder_faces_count')),
        'volume': float(state.get('total_volume_cm3', 0) or total('volume_cm3')),
    }


def verify_plan(plan, before_state=None, after_state=None):
    """Çalıştırmadan sonraki tasarım durumunu plan beklentileriyle karşılaştırır.

    Uyuşmazlık varsa her biri {'text', 'features'} biçiminde sorun kayıtları döner.
    'features', sorumlu tutulan plan unsur id'leridir (Coder düzeltme turu hedefi).
    """
    before_known = bool(before_state)
    before = _metrics_from_state(before_state) if before_known else \
        {'bodies': 0, 'faces': 0, 'edges': 0, 'cylinder_faces': 0, 'volume': 0.0}
    after = _metrics_from_state(after_state)

    features = plan.get('features', []) if isinstance(plan, dict) else []
    solid_ids, hole_ids, reduces_ids = [], [], []
    exp_bodies, exp_holes = 0, 0
    for f in features:
        t = f.get('type', '')
        p = f.get('params') or {}
        fid = f.get('id', '')
        if t in ('extrude', 'revolve', 'sweep', 'loft'):
            solid_ids.append(fid)
            exp_bodies += _param_int(p, ('count', 'adet', 'quantity', 'sayi', 'sayı'), 1)
        elif t == 'pattern':
            n = _param_int(p, ('count', 'adet', 'quantity', 'sayi', 'sayı'), 2)
            exp_bodies += max(0, n - 1)
            solid_ids.append(fid)
        elif t == 'mirror':
            exp_bodies += 1
            solid_ids.append(fid)
        elif t == 'hole':
            hole_ids.append(fid)
            exp_holes += _param_int(p, ('count', 'adet', 'quantity', 'sayi', 'sayı'), 1)
        elif t in ('cut', 'combine'):
            reduces_ids.append(fid)

    has_solid = bool(solid_ids)
    reduces = bool(reduces_ids)
    issues = []

    if has_solid and not reduces:
        new_bodies = after['bodies'] - before['bodies']
        if new_bodies < exp_bodies:
            issues.append({
                'text': ('Plan en az {} yeni katı gövde bekliyordu ancak {} gövde eklendi '
                         '(önce {}, sonra {}).').format(exp_bodies, new_bodies, before['bodies'], after['bodies']),
                'features': solid_ids,
            })

    if exp_holes > 0:
        new_cyl = after['cylinder_faces'] - before['cylinder_faces']
        if new_cyl < exp_holes:
            issues.append({
                'text': ('Planda {} delik istendi ancak çalıştırmadan sonra yalnızca {} yeni silindirik yüz '
                         'oluştu (silindirik yüz: {}→{}).').format(exp_holes, new_cyl,
                                                                   before['cylinder_faces'], after['cylinder_faces']),
                'features': hole_ids,
            })

    if has_solid and not reduces and after['volume'] <= before['volume'] + 1e-9:
        issues.append({
            'text': 'Plan yeni katı gövde içermesine rağmen toplam hacim artmadı; katı oluşturma başarısız olabilir.',
            'features': solid_ids,
        })

    if before_known:
        metrics = ('gövde {}→{}, yüz {}→{}, kenar {}→{}, silindirik yüz {}→{}, hacim {:.2f}→{:.2f} cm³'
                   .format(before['bodies'], after['bodies'], before['faces'], after['faces'],
                           before['edges'], after['edges'], before['cylinder_faces'], after['cylinder_faces'],
                           before['volume'], after['volume']))
    else:
        metrics = ('gövde {}, yüz {}, kenar {}, silindirik yüz {}, hacim {:.2f} cm³ (öncesi bilinmiyor)'
                   .format(after['bodies'], after['faces'], after['edges'],
                           after['cylinder_faces'], after['volume']))

    return {'ok': not issues, 'issues': issues, 'metrics': metrics,
            'before': before, 'after': after, 'before_known': before_known}


# --------------------------------------------------------------------------
# Palet / HTTP köprüsü için op göndericisi
# --------------------------------------------------------------------------
def run_pipeline_helper(payload, inspect_state=None, capture_viewport=None):
    """pipelineHelper op'larını yürütür (LLM çağrısı YAPMAZ, hızlıdır).

    inspect_state / capture_viewport: Fusion ana thread'inde çalışması gereken
    çağrılardır; palet doğrudan fonksiyon, HTTP köprüsü olay köprüsü enjekte eder.
    """
    if not isinstance(payload, dict):
        return {'ok': False, 'error': 'Geçersiz istek.'}
    op = payload.get('op')
    cad_target = payload.get('cad_target') or 'fusion360'
    try:
        if op == 'simpleCheck':
            plan = is_simple_command(payload.get('prompt', ''))
            return {'ok': True, 'simple': plan is not None, 'plan': plan}

        if op == 'plannerPrompt':
            return {'ok': True, 'system': PLANNER_PROMPT}

        if op == 'validatePlan':
            parsed = parse_plan_json(payload.get('raw', ''))
            if parsed is None:
                return {'ok': False, 'error': 'Yanıt geçerli JSON değil (nesne bulunamadı).'}
            ok, plan, err = validate_plan(parsed)
            if not ok:
                return {'ok': False, 'error': err}
            return {'ok': True, 'chat': plan.get('chat') is True, 'plan': plan}

        if op == 'coderPrompt':
            res = build_coder_prompt(payload.get('plan') or {}, payload.get('feature') or {},
                                     payload.get('prev_summaries') or [],
                                     payload.get('context_summary'),
                                     cad_target=cad_target)
            res['ok'] = True
            return res

        if op == 'correctionPrompt':
            res = build_correction_prompt(payload.get('plan') or {}, payload.get('feature') or {},
                                          payload.get('issues') or [], payload.get('current_code', ''),
                                          payload.get('prev_summaries') or [],
                                          payload.get('context_summary'),
                                          cad_target=cad_target)
            res['ok'] = True
            return res

        if op == 'verifyPlan':
            if inspect_state is None:
                return {'ok': True, 'skipped': True, 'issues': [], 'metrics': 'tasarım durumu okunamadı'}
            after = inspect_state()
            if not after or not after.get('has_design'):
                return {'ok': True, 'skipped': True, 'issues': [], 'metrics': 'aktif tasarım bulunamadı'}
            return verify_plan(payload.get('plan') or {}, payload.get('before'), after)

        if op == 'captureViewport':
            if capture_viewport is None:
                return {'success': False, 'error': 'Viewport erişimi yok.'}
            return capture_viewport(payload.get('width', 900), payload.get('height', 600))

        return {'ok': False, 'error': 'Bilinmeyen op: {}'.format(op)}
    except Exception as e:
        return {'ok': False, 'error': 'pipelineHelper hatası: {}'.format(e)}
