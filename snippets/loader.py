"""Snippets dizini (index.json) uzerinden Fusion 360 ve SolidWorks snippet kodlarini yukler.

Sadece standart kutuphane kullanir (json, os). Fusion 360 veya aicad_bridge
paketlerine bagimliligi yoktur; hem add-in icinden hem harici araclardan
kullanilabilir.

Kullanim:
    from snippets import loader

    loader.get_snippet('fillet_edges')                                    # Fusion 360
    loader.find_snippets(feature_type='extrude', cad_target='solidworks') # SolidWorks
    loader.find_snippets(keyword='yuvarlat')                              # anahtar kelimeye gore ara
    loader.get_snippet_codes(feature_type='extrude')                      # (id, kod) listesi
"""

import json
import os

_SNIPPETS_DIR = os.path.dirname(os.path.abspath(__file__))
_INDEX_PATH = os.path.join(_SNIPPETS_DIR, 'index.json')
_SW_INDEX_PATH = os.path.join(_SNIPPETS_DIR, 'solidworks', 'index.json')
_REPO_ROOT = os.path.dirname(_SNIPPETS_DIR)

# Turkce karakterlerin ASCII karsiliklari (arama icin)
_TR_FOLD = str.maketrans('çğışüöÇĞİŞÜÖ', 'cgisuocgisuo')


def _fold(text):
    """Metni kucuk harfe cevirip Turkce karakterleri ASCII'ye katlar."""
    return str(text).lower().translate(_TR_FOLD)


def _is_sw(cad_target):
    return str(cad_target or '').strip().lower() in ('solidworks', 'sw', 'adacad', 'adamcad', 'cadam')


def load_index(cad_target='fusion360'):
    """index.json dosyasini okuyup sozluk olarak dondurur."""
    path = _SW_INDEX_PATH if (_is_sw(cad_target) and os.path.isfile(_SW_INDEX_PATH)) else _INDEX_PATH
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _entry_file_path(entry):
    """Index kaydindaki dosya yolunu (depo kokune gore) tam yola cevirir."""
    file_path = entry.get('file', '')
    if os.path.isabs(file_path):
        return file_path
    return os.path.normpath(os.path.join(_REPO_ROOT, file_path))


def _entry_keywords(entry):
    """Bir kaydin TR + EN anahtar kelimelerini tek listede dondurur."""
    keywords = entry.get('keywords', {})
    if isinstance(keywords, dict):
        tr = keywords.get('tr', []) or []
        en = keywords.get('en', []) or []
        return list(tr) + list(en)
    if isinstance(keywords, list):
        return list(keywords)
    return []


def _matches(entry, feature_type=None, keyword=None):
    """Kayit, verilen filtrelerin ikisini de (verildiyse) sagliyor mu?"""
    if feature_type is not None:
        if entry.get('feature_type', '').lower() != str(feature_type).lower():
            return False
    if keyword is not None:
        needle = _fold(keyword).strip()
        if needle:
            haystack = [entry.get('id', ''), entry.get('feature_type', '')]
            haystack += _entry_keywords(entry)
            if not any(needle in _fold(h) for h in haystack):
                return False
    return True


def get_snippet_code(entry):
    """Index kaydinin isaret ettigi dosyanin icerigini dondurur (okunamazsa None)."""
    path = _entry_file_path(entry)
    if not path or not os.path.isfile(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def find_snippets(feature_type=None, keyword=None, include_code=False, cad_target='fusion360'):
    """Filtrelere uyan snippet kayitlarini dondurur."""
    results = []
    for entry in load_index(cad_target=cad_target).get('snippets', []):
        if _matches(entry, feature_type, keyword):
            item = dict(entry)
            if include_code:
                item['code'] = get_snippet_code(entry)
            results.append(item)
    return results


def get_snippet(snippet_id, cad_target='fusion360'):
    """id ile eslesen snippet'in kod metnini dondurur (bulamazsa None)."""
    for entry in load_index(cad_target=cad_target).get('snippets', []):
        if entry.get('id', '').lower() == str(snippet_id).lower():
            return get_snippet_code(entry)
    return None


def get_snippet_codes(feature_type=None, keyword=None, cad_target='fusion360'):
    """Filtrelere uyan snippet'lerin (id, kod) listesini dondurur."""
    codes = []
    for entry in find_snippets(feature_type=feature_type, keyword=keyword, cad_target=cad_target):
        code = get_snippet_code(entry)
        if code is not None:
            codes.append((entry.get('id'), code))
    return codes
