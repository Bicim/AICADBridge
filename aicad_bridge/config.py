"""Uygulama yapılandırması: .env / ortam değişkenlerinden model ve üretim hattı ayarları.

Öncelik sırası (yüksekten düşüğe):
    1. Gerçek ortam değişkenleri (işletim sistemi / Fusion süreci)
    2. Repo kökündeki .env dosyası
    3. Bu modüldeki DEFAULTS değerleri

Model adları bilinçli olarak kodda tutulmaz; kullanıcı .env üzerinden kendi
sağlayıcısının güncel model adını girer. Planner (plan JSON'u üreten aşama) ve
Coder (feature başına kod üreten aşama) için ayrı model seçilebilir; boş
bırakıldığında ikisi de sohbet (ana) modelini kullanır.

Sadece standart kütüphane kullanır; adsk'a bağlı değildir (birim testlerde
bağımsız çalışır).
"""

import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_FILE = os.path.join(_REPO_ROOT, '.env')

# Kod içi varsayılanlar (.env ya da ortam değişkenleriyle geçersiz kılınabilir).
DEFAULTS = {
    # Üretim hattı (Planner / Coder) model ayarları — boş = sohbet modeli kullanılır
    'AICAD_PLANNER_PROVIDER': '',
    'AICAD_PLANNER_MODEL': '',
    'AICAD_CODER_PROVIDER': '',
    'AICAD_CODER_MODEL': '',
    # Yanıt uzunluğu sınırları (Anthropic çağrılarında kullanılır)
    'AICAD_MAX_TOKENS': '16384',
    'AICAD_VISION_MAX_TOKENS': '4096',
    # Anthropic tarayıcıdan model listesi çekemediğinde (CORS) kullanılacak
    # yedek model listesi: virgülle ayrılmış model id'leri. Boş = liste yok,
    # kullanıcı model adını arayüzden elle girer.
    'AICAD_ANTHROPIC_MODELS': '',
}

_cache = {}


def parse_env_file(path):
    """.env dosyasını çözümleyip {anahtar: değer} sözlüğü döndürür (dosya yoksa boş sözlük).

    - Boş satırlar ve '#' ile başlayan satırlar atlanır (yorumlar kendi satırında olmalı).
    - Değerler çevresindeki çift/tek tırnaklardan temizlenir.
    """
    values = {}
    if not path or not os.path.isfile(path):
        return values
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                if key:
                    values[key] = value
    except Exception:
        pass
    return values


def _apply_env_file():
    """.env değerlerini ortam değişkenlerine yazar (gerçek env değişkenleri önceliklidir)."""
    for key, value in parse_env_file(_ENV_FILE).items():
        os.environ.setdefault(key, value)


def _get(key):
    _apply_env_file()
    return os.environ.get(key) or DEFAULTS.get(key, '')


def _get_int(key, fallback):
    try:
        return int(str(_get(key)).strip())
    except (TypeError, ValueError):
        return fallback


def get_settings(refresh=False):
    """Tüm yapılandırma ayarlarını sözlük olarak döndürür (sonuç önbelleklenir)."""
    if not refresh and 'settings' in _cache:
        return _cache['settings']
    settings = {
        'planner': {
            'provider': str(_get('AICAD_PLANNER_PROVIDER')).strip().lower(),
            'model': str(_get('AICAD_PLANNER_MODEL')).strip(),
        },
        'coder': {
            'provider': str(_get('AICAD_CODER_PROVIDER')).strip().lower(),
            'model': str(_get('AICAD_CODER_MODEL')).strip(),
        },
        'max_tokens': _get_int('AICAD_MAX_TOKENS', 16384),
        'vision_max_tokens': _get_int('AICAD_VISION_MAX_TOKENS', 4096),
        'anthropic_models': [m.strip() for m in str(_get('AICAD_ANTHROPIC_MODELS')).split(',') if m.strip()],
    }
    _cache['settings'] = settings
    return settings


def get_public_settings(refresh=False):
    """UI'ya (palet / harici tarayıcı) gönderilebilir genel yapılandırma görünümü."""
    s = get_settings(refresh)
    return {
        'planner': dict(s['planner']),
        'coder': dict(s['coder']),
        'max_tokens': s['max_tokens'],
        'vision_max_tokens': s['vision_max_tokens'],
        'anthropic_models': list(s['anthropic_models']),
    }
