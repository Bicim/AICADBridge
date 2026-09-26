"""
Fusion 360 AI CAD Studio Add-in (AICADBridge)
Doğal dil ile 3D modelleme asistanı.
Çoklu sağlayıcı destekli (Ollama, OpenAI, Anthropic, Google, Groq, OpenRouter, DeepSeek)
ve Self-Healing CAD code generation loop.
"""

import adsk.core
import adsk.fusion
import http.server
import json
import math
import os
import re
import threading
import time
import traceback
import urllib.error
import urllib.request

# Global references
app = None
ui = None
palette = None
custom_event = None
handlers = []

PALETTE_ID = 'AICADBridge_Palette'
PALETTE_NAME = 'AI CAD Studio'
CMD_ID = 'AICADBridge_ShowPaletteCmd'
CMD_NAME = 'AI CAD Studio'
CMD_DESC = 'Yapay zeka ile doğal dilden 3D model oluşturan CAD stüdyosu panelini açar.'
TOOLBAR_PANEL_ID = 'AICADBridge_ToolbarPanel'
TOOLBAR_PANEL_NAME = 'AI CAD'
CUSTOM_EVENT_ID = 'AICADBridge_Custom_Event'

# Threading & Task tracking
task_lock = threading.Lock()
pending_tasks = {}

# ── File Logger ──
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aicad_debug.log')

def aicad_log(msg):
    """Zaman damgasıyla aicad_debug.log dosyasına yazar."""
    try:
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

def get_active_palette():
    """Mevcut açık paleti güvenli şekilde bulur."""
    global palette, ui
    if palette:
        return palette
    if ui:
        try:
            return ui.palettes.itemById(PALETTE_ID)
        except Exception:
            pass
    return None

# ── Provider Configuration ──
PROVIDERS = {
    'ollama': {
        'name': 'Ollama (Yerel)',
        'chat_url': 'http://localhost:11434/v1/chat/completions',
        'models_url': 'http://localhost:11434/api/tags',
        'format': 'openai',
        'needs_key': False,
    },
    'openai': {
        'name': 'OpenAI',
        'chat_url': 'https://api.openai.com/v1/chat/completions',
        'models_url': 'https://api.openai.com/v1/models',
        'format': 'openai',
        'needs_key': True,
    },
    'anthropic': {
        'name': 'Anthropic',
        'chat_url': 'https://api.anthropic.com/v1/messages',
        'models_url': 'https://api.anthropic.com/v1/models',
        'format': 'anthropic',
        'needs_key': True,
    },
    'google': {
        'name': 'Google',
        'chat_url': 'https://generativelanguage.googleapis.com/v1beta/models',
        'models_url': 'https://generativelanguage.googleapis.com/v1beta/models',
        'format': 'google',
        'needs_key': True,
    },
    'groq': {
        'name': 'Groq',
        'chat_url': 'https://api.groq.com/openai/v1/chat/completions',
        'models_url': 'https://api.groq.com/openai/v1/models',
        'format': 'openai',
        'needs_key': True,
    },
    'openrouter': {
        'name': 'OpenRouter',
        'chat_url': 'https://openrouter.ai/api/v1/chat/completions',
        'models_url': 'https://openrouter.ai/api/v1/models',
        'format': 'openai',
        'needs_key': True,
    },
    'local': {
        'name': 'Yerel Model (Local)',
        'chat_url': 'http://localhost:1234/v1/chat/completions',
        'models_url': 'http://localhost:1234/v1/models',
        'format': 'openai',
        'needs_key': False,
    },
    'deepseek': {
        'name': 'DeepSeek',
        'chat_url': 'https://api.deepseek.com/chat/completions',
        'models_url': 'https://api.deepseek.com/models',
        'format': 'openai',
        'needs_key': True,
    },
}

# System prompt for LLM
SYSTEM_PROMPT = """You are "AI CAD Studio", an autonomous Autodesk Fusion 360 3D Modeling Engineer and Copilot.
You converse fluently and naturally in Turkish (or the user's language).

CRITICAL ARCHITECTURAL RULES:

1. THE USER DOES NOT RUN SCRIPTS - NEVER OUTPUT EXECUTION INSTRUCTIONS:
   - The user is an end-user / designer, NOT a programmer.
   - The user will NEVER manually run code, copy-paste scripts, or open menus.
   - Our system automatically extracts your Python code and runs it directly in Autodesk Fusion 360 behind the scenes!
   - STRICT BAN: NEVER write "Nasıl Çalıştırılır?", "Scripts and Add-ins", "Alt+Shift+F", "My Scripts", "Create", "Run butonuna basın", or any instructions telling the user to copy/paste/execute code.
   - Simply explain the 3D design features and steps conversationally.

2. PROJE ANLAMA VE SORU SORMA PRENSİBİ (WHEN TO ASK QUESTIONS):
   - NE ZAMAN SORU SORULMALI:
     * Kullanıcı genel, belirsiz veya fikir alma amaçlı bir taleple geldiğinde (örneğin "aklımda bir proje var", "uçak yapmak istiyorum ama nasıl yapsam?", "bir şey tasarlayalım"):
       Projeyi tam olarak anlamak, fikir alışverişi yapmak ve projeyi sağlam bir temel üzerine inşa etmek için 1-2 kısa, net ve amaca yönelik soru sor (Örn: "Nasıl bir uçak tipi düşünüyorsun: Yolcu uçağı mı, savaş jeti mi, planör mü? Özel bir ölçü var mı yoksa standart ölçülerle ben mi başlayayım?").
   - NE ZAMAN SORU SORULMAMALI (KESİNTİSİZ MODELLEME):
     * Kullanıcı doğrudan "uçak yap", "4 ayaklı masa çiz", "drone modelle", "devam et", "sıradaki adımı yap", "sen karar ver ve başla" gibi net bir talimat verdiğinde ASLA durup retorik soru sorma ("şunu mu ekleyelim bunu mu?" gibi vakit kaybettirme)!
     * Derhal tam donanımlı Fusion 360 Python kodunu ```python ... ``` bloğu içinde üret ve modeli inşa et!

3. BİR İŞE BAŞLADIĞINDA O İŞİ BİTİRENE KADAR DEVAM ET (COMPLETE & ROBUST MODELING):
   - Bir tasarım talep edildiğinde, gereksiz yere yarım bırakıp durma!
   - Modeli temel ve ana bileşenleriyle bir bütün olarak (örneğin uçaksa: aerodinamik gövde, ana kanatlar, kuyruk dengeliyicileri ve motorlar; masaysa: tabla ve 4 ayak) eksiksiz ve orantılı bir katı model olarak oluştur!
   - Parçaları sadece tek bir izole silindir yapıp bırakma; ana hatlarıyla bitmiş, tanınabilir 3D bir nesne oluştur.
   - Kullanıcı devam etmesini istediğinde de sıradaki mantıklı detay parçayı doğrudan modelle.

4. FUSION 360 PYTHON API CRITICAL RULES:
   - INTERNAL UNITS: Fusion 360 API internally uses CENTIMETERS (cm) for ALL linear dimensions.
     * 1 mm = 0.1 cm
     * 10 mm = 1.0 cm
     * 50 mm = 5.0 cm
     * 100 mm = 10.0 cm
     Always convert mm to cm in your code coordinates and extrusions!
   - IMPORTS: Always import adsk.core, adsk.fusion, math.
   - ACCESS ROOT COMPONENT:
     app = adsk.core.Application.get()
     design = adsk.fusion.Design.cast(app.activeProduct)
     rootComp = design.rootComponent

   - MANDATORY 3D SOLID CREATION (Extrude / Katılama Kesinlikle Zorunludur):
     CRITICAL: Every generated script MUST finish by creating 3D solid geometry (using extrudes.add with NewBodyFeatureOperation).
     NEVER output code that only draws a 2D sketch without extruding it into a 3D solid body!
     A 2D sketch alone has no 3D volume, is invisible to the user, and is considered an absolute failure.
     
     * Standard Extrude (Single Profile):
       extrudes = rootComp.features.extrudeFeatures
       prof = sketch.profiles.item(0)
       extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
       extInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(height_in_cm))
       extrudes.add(extInput)

     * Multiple Profiles (e.g. Twin Engines, Landing Gear Wheels, Dual Wings):
       extrudes = rootComp.features.extrudeFeatures
       for i in range(sketch.profiles.count):
           p = sketch.profiles.item(i)
           extInput = extrudes.createInput(p, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
           extInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(height_in_cm))
           extrudes.add(extInput)

   - Ensure the code runs independently and robustly.

5. EXISTING DESIGN INSPECTION & CONTINUATION:
   - When the user asks to continue, modify, or add features ("kaldığın yerden devam et", "mevcut tasarımı oku", "kanatları ekle"):
   - Read the [MEVCUT FUSION 360 TASARIM DURUMU] provided in the prompt context carefully.
   - Inspect the existing body names, bounding boxes [minPoint, maxPoint in mm], and dimensions.
   - Always align and position your new sketches and features accurately relative to these existing body coordinates.
   - CRITICAL SAFETY RULE: ALWAYS use `adsk.fusion.FeatureOperations.NewBodyFeatureOperation` when adding new solid parts or features to an existing design!
   - STRICT BAN: NEVER use `CutFeatureOperation` or `JoinFeatureOperation` on empty space or when the extrude does not physically intersect a body, as this causes the fatal crash "RuntimeError: 3 : Kesilecek veya kesişecek hedef gövde bulunamadı!".
   - STRICT BAN: NEVER write `ui.messageBox(...)` or `except: ui.messageBox(...)` in the generated Python code!
   - STRICT BAN: NEVER catch exceptions and swallow them (`except: pass` or `except: print(e)`). Let exceptions raise normally so the automatic Self-Healing system can repair them!

6. DİNAMİK VE İLGİLİ ÖNERİLER (DYNAMIC SUGGESTIONS):
   - Her yanıtının en sonuna, SADECE o an tasarlanan veya konuşulan projeye özel 2-3 adet mantıklı sonraki adım veya fikir önerisi ekle:
     Biçim: [ÖNERİLER: Öneri 1 | Öneri 2 | Öneri 3]
     Örnek (Uçak için): [ÖNERİLER: Jet motorlarını ekle | Kanat uçlarına winglet koy | Kokpit kanopisini detaylandır]
     Örnek (Masa için): [ÖNERİLER: Çekmece ekle | Kenarları yuvarlatılmış yap | Ayaklara destek çıtası koy]
     Örnek (Soru sorma aşamasında): [ÖNERİLER: Standart ölçülerle başla | Ölçüleri ben vereyim | Sen karar ver ve modelle]
"""


def extract_python_code(text):
    """LLM yanıtından saf Python kodunu temizler. Kod bloğu yoksa boş döner."""
    if not text:
        return ""
    match = re.search(r'```(?:python)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


# ── Model Fetching ──

def _http_get(url, headers=None, timeout=8):
    """Basit HTTP GET isteği. localhost başarısız olursa 127.0.0.1 dener."""
    hdrs = {'User-Agent': 'Fusion360-AICADBridge'}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        if 'localhost' in url:
            try:
                alt_url = url.replace('localhost', '127.0.0.1')
                alt_req = urllib.request.Request(alt_url, headers=hdrs, method='GET')
                with urllib.request.urlopen(alt_req, timeout=timeout) as resp:
                    return json.loads(resp.read().decode('utf-8'))
            except Exception:
                pass
        raise e


def fetch_models(provider, api_key='', base_url=None):
    """Sağlayıcıdan kullanılabilir model listesini çeker."""
    try:
        if provider == 'local':
            return _fetch_openai_compat_models('local', api_key, base_url=base_url or 'http://localhost:1234/v1')

        prov = PROVIDERS.get(provider)
        if not prov:
            return {'success': False, 'error': f'Bilinmeyen sağlayıcı: {provider}', 'models': []}

        if provider == 'ollama':
            return _fetch_ollama_models()
        elif provider == 'google':
            return _fetch_google_models(api_key)
        elif provider == 'anthropic':
            return _fetch_anthropic_models(api_key)
        else:
            # OpenAI-uyumlu format (OpenAI, Groq, OpenRouter, DeepSeek, Local)
            return _fetch_openai_compat_models(provider, api_key, base_url=base_url)

    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')[:500]
        try:
            err_json = json.loads(err_body)
            msg = err_json.get('error', {}).get('message', str(e))
        except Exception:
            msg = f"HTTP {e.code}: {err_body or str(e)}"
        return {'success': False, 'error': msg, 'models': []}
    except urllib.error.URLError as e:
        if provider in ('ollama', 'local') or (base_url and any(k in base_url for k in ('1234', '11434', '8080', 'localhost'))):
            return {'success': False, 'error': 'Yerel model sunucusuna ulaşılamıyor. LM Studio veya Ollama uygulamasının açık olduğundan ve sunucunun başlatıldığından emin olun.', 'models': []}
        return {'success': False, 'error': f'Bağlantı hatası: {str(e.reason)}', 'models': []}
    except Exception as e:
        return {'success': False, 'error': str(e), 'models': []}


def _fetch_ollama_models():
    """Yerel Ollama sunucusundaki modelleri listeler."""
    data = _http_get('http://localhost:11434/api/tags', timeout=2)
    models = []
    for m in data.get('models', []):
        name = m.get('name', '')
        if name:
            size_gb = m.get('size', 0) / (1024 ** 3)
            label = f"{name} ({size_gb:.1f}GB)" if size_gb > 0.1 else name
            models.append({'id': name, 'name': label})
    return {'success': True, 'models': models}


def _fetch_openai_compat_models(provider, api_key, base_url=None):
    """OpenAI-uyumlu /v1/models endpoint'inden model listesi çeker."""
    if base_url:
        url = base_url.rstrip('/') + '/models'
    else:
        prov = PROVIDERS.get(provider, {})
        url = prov.get('models_url', 'http://localhost:1234/v1/models')

    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    data = _http_get(url, headers=headers, timeout=10)
    raw_models = data.get('data', [])

    models = []
    for m in raw_models:
        mid = m.get('id', '')
        if not mid:
            continue
        # Provider-bazlı filtreleme
        if provider == 'openai':
            # Sadece sohbet modellerini göster
            if not any(k in mid for k in ('gpt-', 'o1-', 'o3-', 'o4-', 'chatgpt-')):
                continue
            # Eski / dahili modelleri atla
            if any(k in mid for k in ('instruct', 'realtime', 'audio', 'search', 'tts', 'whisper', 'dall-e', 'embedding')):
                continue
        elif provider in ('groq', 'openrouter', 'deepseek', 'local'):
            pass

        name = m.get('name', mid)
        if not name or name == mid:
            name = mid
        models.append({'id': mid, 'name': name})

    # Sırala
    models.sort(key=lambda x: x['name'])
    return {'success': True, 'models': models}


def _fetch_anthropic_models(api_key):
    """Anthropic /v1/models endpoint'inden model listesi çeker."""
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
    }
    try:
        data = _http_get('https://api.anthropic.com/v1/models', headers=headers)
        models = []
        for m in data.get('data', []):
            mid = m.get('id', '')
            name = m.get('display_name', mid)
            if mid:
                models.append({'id': mid, 'name': name})
        models.sort(key=lambda x: x['name'])
        return {'success': True, 'models': models}
    except Exception:
        # Fallback: bilinen modeller
        fallback = [
            {'id': 'claude-sonnet-4-20250514', 'name': 'Claude Sonnet 4'},
            {'id': 'claude-opus-4-20250514', 'name': 'Claude Opus 4'},
            {'id': 'claude-3-5-sonnet-20241022', 'name': 'Claude 3.5 Sonnet'},
            {'id': 'claude-3-5-haiku-20241022', 'name': 'Claude 3.5 Haiku'},
        ]
        return {'success': True, 'models': fallback}


def _fetch_google_models(api_key):
    """Google Gemini API'den model listesi çeker."""
    url = f'https://generativelanguage.googleapis.com/v1beta/models?key={api_key}'
    data = _http_get(url)
    models = []
    for m in data.get('models', []):
        methods = m.get('supportedGenerationMethods', [])
        if 'generateContent' not in methods:
            continue
        mid = m.get('name', '').replace('models/', '')
        display = m.get('displayName', mid)
        if mid:
            models.append({'id': mid, 'name': display})
    models.sort(key=lambda x: x['name'])
    return {'success': True, 'models': models}


# ── LLM Chat API ──

def call_llm_api(provider, model, messages, api_key=None, timeout=90, base_url=None):
    """Sağlayıcıya uygun formatta LLM API çağrısı yapar."""
    prov = PROVIDERS.get(provider)
    if not prov:
        raise ValueError(f"Desteklenmeyen sağlayıcı: {provider}")

    # Yerel modeller donanıma bağlı olarak daha yavaş yanıt verebilir; zaman aşımını geniş tut
    if provider == 'local':
        timeout = max(timeout, 150)

    fmt = prov['format']

    if fmt == 'anthropic':
        return _call_anthropic(model, messages, api_key, timeout)
    elif fmt == 'google':
        return _call_google(model, messages, api_key, timeout)
    else:
        return _call_openai_compat(provider, model, messages, api_key, timeout, base_url=base_url)


def translate_api_error_tr(err_msg, provider=""):
    """API hata mesajlarını kullanıcı dostu ve anlaşılır Türkçeye dönüştürür."""
    if not err_msg:
        return "Bilinmeyen bir hata oluştu."
    
    s = str(err_msg)
    p_name = PROVIDERS.get(provider, {}).get('name', provider.capitalize()) if provider else "API"

    if re.search(r'currently experiencing high demand|spikes in demand|high demand', s, re.I):
        return f"{p_name} modeli şu anda aşırı sunucu yoğunluğu yaşıyor. Lütfen birkaç saniye sonra tekrar deneyin veya alternatif bir modele geçin."
    if re.search(r'provider returned error', s, re.I):
        return f"{p_name} sunucusu şu an bu modele yanıt veremedi. Model geçici olarak kapalı olabilir, lütfen farklı bir model seçin veya tekrar deneyin."
    if re.search(r'resource has been exhausted|quota|insufficient_quota|exceeded your current quota|credits exhausted|insufficient credits|balance', s, re.I):
        return f"{p_name} kullanım kotası aşıldı veya hesap bakiyesi yetersiz. Lütfen hesabınızı kontrol edin."
    if re.search(r'api_key_invalid|invalid_api_key|incorrect api key|invalid x-api-key|invalid api key|unauthorized|401', s, re.I):
        return f"Geçersiz {p_name} API anahtarı. Lütfen Ayarlar menüsünden API anahtarınızı kontrol edin."
    if re.search(r'rate limit|rate_limit_exceeded|too many requests|429', s, re.I):
        return f"{p_name} istek sınırı (Rate limit) aşıldı. Lütfen 10-15 saniye bekleyip tekrar deneyin."
    if re.search(r'location is not supported|user location|country not supported', s, re.I):
        return f"Bulunduğunuz bölge bu {p_name} servisi tarafından desteklenmiyor. OpenRouter üzerinden erişmeyi deneyebilirsiniz."
    if re.search(r'model not found|does not exist|model_not_found|404', s, re.I):
        return f"Seçilen model bulunamadı veya hesabınızın bu modele erişim yetkisi yok."
    if re.search(r'overloaded|capacity|service unavailable|503|502', s, re.I):
        return f"{p_name} sunucuları aşırı yük altında veya geçici olarak hizmet dışı (HTTP 503). Lütfen biraz bekleyin."
    if re.search(r'internal server error|500', s, re.I):
        return f"{p_name} tarafında dahili bir sunucu hatası oluştu (HTTP 500). Lütfen tekrar deneyin."
    if re.search(r'connection refused|bağlanılamadı|failed to connect', s, re.I):
        if provider in ('ollama', 'local'):
            return "Yerel model sunucusuna ulaşılamıyor. LM Studio veya Ollama uygulamasının açık olduğundan ve yerel sunucunun başlatıldığından emin olun."
        return f"{p_name} servisine bağlanılamadı. Servisin çalıştığından emin olun."
    
    return f"{p_name} Hatası: {s}"


def _call_openai_compat(provider, model, messages, api_key, timeout, base_url=None):
    """OpenAI-uyumlu chat/completions endpoint'ine istek gönderir."""
    if base_url:
        url = base_url.rstrip('/') + '/chat/completions'
    else:
        prov = PROVIDERS.get(provider, {})
        url = prov.get('chat_url', 'http://localhost:1234/v1/chat/completions')

    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    payload = {'model': model, 'messages': messages, 'temperature': 0.2}
    req_body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=req_body, headers=headers, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_data = json.loads(resp.read().decode('utf-8'))
            choices = resp_data.get('choices', [])
            if not choices:
                raise Exception("LLM boş yanıt döndürdü.")
            return choices[0].get('message', {}).get('content', '')
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')[:800]
        try:
            err_json = json.loads(err_body)
            msg = err_json.get('error', {}).get('message', str(e))
        except Exception:
            msg = f"HTTP {e.code}: {err_body or str(e)}"
        raise Exception(translate_api_error_tr(msg, provider))
    except urllib.error.URLError as e:
        if 'localhost' in url:
            try:
                alt_url = url.replace('localhost', '127.0.0.1')
                alt_req = urllib.request.Request(alt_url, data=req_body, headers=headers, method='POST')
                with urllib.request.urlopen(alt_req, timeout=timeout) as resp:
                    resp_data = json.loads(resp.read().decode('utf-8'))
                    choices = resp_data.get('choices', [])
                    if choices:
                        return choices[0].get('message', {}).get('content', '')
            except Exception:
                pass
        if provider in ('ollama', 'local') or (base_url and any(k in base_url for k in ('1234', '11434', '8080', 'localhost'))):
            raise Exception("Yerel model sunucusuna ulaşılamıyor. LM Studio veya Ollama uygulamasının açık olduğundan ve yerel sunucunun başlatıldığından emin olun.")
        raise Exception(f"Ağ Hatası ({provider}): {str(e.reason)}")


def _call_anthropic(model, messages, api_key, timeout):
    """Anthropic /v1/messages formatında istek gönderir."""
    system_text = ''
    chat_messages = []
    for m in messages:
        if m['role'] == 'system':
            system_text += m['content'] + '\n'
        else:
            chat_messages.append({'role': m['role'], 'content': m['content']})

    payload = {
        'model': model,
        'max_tokens': 4096,
        'messages': chat_messages,
        'temperature': 0.2,
    }
    if system_text.strip():
        payload['system'] = system_text.strip()

    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
    }

    req_body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=req_body, headers=headers, method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_data = json.loads(resp.read().decode('utf-8'))
            content_blocks = resp_data.get('content', [])
            texts = [b.get('text', '') for b in content_blocks if b.get('type') == 'text']
            return '\n'.join(texts)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')[:800]
        try:
            err_json = json.loads(err_body)
            msg = err_json.get('error', {}).get('message', str(e))
        except Exception:
            msg = f"HTTP {e.code}: {err_body or str(e)}"
        raise Exception(translate_api_error_tr(msg, 'anthropic'))


def _call_google(model, messages, api_key, timeout):
    """Google Gemini generateContent formatında istek gönderir."""
    system_text = ''
    contents = []
    for m in messages:
        if m.get('role') == 'system':
            content = m.get('content', '')
            if isinstance(content, str):
                system_text += content + '\n'
        else:
            role = 'user' if m.get('role') == 'user' else 'model'
            if 'parts' in m:
                contents.append({'role': role, 'parts': m['parts']})
            elif isinstance(m.get('content'), list):
                parts = []
                for item in m['content']:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        parts.append({'text': item.get('text', '')})
                    elif isinstance(item, dict) and item.get('type') == 'image_url':
                        url = item.get('image_url', {}).get('url', '')
                        if ',' in url:
                            header, b64 = url.split(',', 1)
                            mime = header.split(';')[0].split(':')[1] if ':' in header else 'image/png'
                            parts.append({'inlineData': {'mimeType': mime, 'data': b64}})
                contents.append({'role': role, 'parts': parts})
            else:
                contents.append({'role': role, 'parts': [{'text': str(m.get('content', ''))}]})

    payload = {'contents': contents}
    if system_text.strip():
        payload['systemInstruction'] = {'parts': [{'text': system_text.strip()}]}
    payload['generationConfig'] = {'temperature': 0.3}

    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
    headers = {'Content-Type': 'application/json'}

    req_body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=req_body, headers=headers, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_data = json.loads(resp.read().decode('utf-8'))
            candidates = resp_data.get('candidates', [])
            if not candidates:
                raise Exception("Google API boş yanıt döndürdü.")
            parts = candidates[0].get('content', {}).get('parts', [])
            return '\n'.join(p.get('text', '') for p in parts)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')[:800]
        try:
            err_json = json.loads(err_body)
            msg = err_json.get('error', {}).get('message', str(e))
        except Exception:
            msg = f"HTTP {e.code}: {err_body or str(e)}"
        raise Exception(translate_api_error_tr(msg, 'google'))


# ── Core CAD Inspection & Execution ──

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
    global app
    try:
        if not app:
            app = adsk.core.Application.get()
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

                bodies.append({
                    'name': body.name,
                    'is_solid': body.isSolid,
                    'is_visible': body.isVisible,
                    'faces_count': body.faces.count if hasattr(body, 'faces') else 0,
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

        return {
            'has_design': True,
            'doc_name': doc.name,
            'default_units': default_units,
            'bodies_count': len(bodies),
            'bodies': bodies,
            'sketches_count': len(sketches),
            'sketches': sketches,
            'summary_text': summary_text
        }
    except Exception as e:
        tb = traceback.format_exc()
        aicad_log(f"inspect_current_design hatası: {e}\n{tb}")
        return {'has_design': False, 'error': str(e), 'summary_text': 'Tasarım durumu okunamadı.'}


def get_design_state_on_main_thread():
    """Fusion ana thread'inde aktif tasarımı analiz edip sonucunu bekler."""
    global app, custom_event
    if not app or not custom_event:
        return inspect_current_design()
    task_id = str(time.time())
    evt = threading.Event()
    with task_lock:
        pending_tasks[task_id] = {'event': evt, 'result': None}
    
    payload = {'action': 'get_design_state', 'task_id': task_id}
    app.fireCustomEvent(CUSTOM_EVENT_ID, json.dumps(payload))

    completed = evt.wait(timeout=10.0)
    with task_lock:
        task_data = pending_tasks.pop(task_id, None)

    if not completed or not task_data or not task_data.get('result'):
        return inspect_current_design()
    return task_data['result']


def execute_code(code):
    """Ana thread üzerinde aktif Fusion dokümanında Python kodunu güvenle yürütür."""
    global app, ui
    try:
        if not app:
            app = adsk.core.Application.get()
        if not ui and app:
            ui = app.userInterface

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
                sketch_info = f" ({final_sketches - initial_sketches} adet 2D eskiz çizildi fakat katılanmadı)"
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


# ── Palette messaging ──

def send_palette_message(action, data):
    """Palete güvenli mesaj gönderir."""
    global app, custom_event
    aicad_log(f"send_palette_message: action={action}")
    p = get_active_palette()
    if p:
        try:
            p.sendInfoToHTML(action, json.dumps(data))
            aicad_log(f"send_palette_message doğrudan palete iletildi: action={action}")
            return
        except Exception as e:
            aicad_log(f"Doğrudan palette.sendInfoToHTML başarısız ({e}), CustomEvent deneniyor...")

    if app and custom_event:
        payload = {
            'action': 'send_to_html',
            'html_action': action,
            'html_data': data
        }
        app.fireCustomEvent(CUSTOM_EVENT_ID, json.dumps(payload))


def run_code_on_main_thread(code):
    """Fusion ana thread'inde Python kodunu çalıştırır ve sonucu bekler."""
    global app, custom_event
    task_id = str(time.time())
    evt = threading.Event()
    task = {'event': evt, 'result': None}
    with task_lock:
        pending_tasks[task_id] = task

    payload = {'action': 'execute_code', 'task_id': task_id, 'code': code}
    app.fireCustomEvent(CUSTOM_EVENT_ID, json.dumps(payload))

    completed = evt.wait(timeout=45.0)
    with task_lock:
        task_data = pending_tasks.pop(task_id, None)

    if not completed or not task_data or not task_data.get('result'):
        return {'success': False, 'error': 'İşlem zaman aşımına uğradı (45 saniye).', 'traceback': ''}
    return task_data['result']


# ── CAD Generation Worker (Fallback Background Thread) ──

def generate_cad_worker(data):
    """Arka plan thread'inde LLM çağrısı ve Self-Healing CAD döngüsünü yürütür."""
    provider = data.get('provider', 'ollama')
    model = data.get('model', '')
    prompt = data.get('prompt', '')
    api_key = data.get('apiKey', '')
    base_url = data.get('baseUrl') or data.get('base_url')
    timeout = data.get('timeout', 90)
    if provider == 'local':
        timeout = max(timeout, 150)
    aicad_log(f"generate_cad_worker başladı: provider={provider}, model={model}, baseUrl={base_url}, prompt='{prompt}'")

    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': prompt}
    ]

    # Mevcut Fusion 360 tasarımını kontrol et ve varsa bağlama ekle
    try:
        current_design = get_design_state_on_main_thread()
        if current_design and current_design.get('has_design') and current_design.get('bodies_count', 0) > 0:
            if '[MEVCUT FUSION 360 TASARIM DURUMU]' not in prompt:
                design_summary = current_design.get('summary_text', '')
                design_addon = (
                    f"\n\n[MEVCUT FUSION 360 TASARIM DURUMU]:\n{design_summary}\n"
                    f"(Lütfen yeni parçayı bu mevcut katı gövdelere uygun koordinatlarda konumlandır "
                    f"ve kesinlikle FeatureOperations.NewBodyFeatureOperation kullan.)"
                )
                if re.search(r'devam|sonraki|sıradak|ilerle|kaldığın|tamam|ekle|yap|bitir|çiz|oluştur|model nerede|görünmüyor', prompt, re.I):
                    design_addon += (
                        "\n\n[KESİNTİSİZ ADIM ADIM MODELLEME TALİMATI]:\n"
                        "Kullanıcı tasarıma devam etmeni ve Fusion 360 ekranında somut 3D parçayı hemen oluşturmanı istiyor! "
                        "KESİNLİKLE soru sorma, 'şunu mu yapalım bunu mu' gibi seçenek sunup bekleme! "
                        "Mevcut modeldeki gövdeleri incele ve sıradaki eksik parçayı kendin belirleyerek "
                        "DOĞRUDAN Fusion 360 Python kodunu ```python ... ``` bloğu içinde üret!\n"
                        "ÖNEMLİ ZORUNLULUK: Kodun sonunda çizdiğin kapalı profili 'extrudes.add(extInput)' ve 'NewBodyFeatureOperation' ile "
                        "mutlaka 3D katı gövdeye dönüştür! Sadece 2D eskiz çizip bırakma!"
                    )
                messages[1]['content'] += design_addon
                aicad_log(f"generate_cad_worker: Tasarım durumu LLM bağlamına eklendi ({current_design.get('bodies_count')} gövde).")
    except Exception as d_err:
        aicad_log(f"generate_cad_worker tasarım durumu ekleme hatası: {d_err}")

    prov_name = PROVIDERS.get(provider, {}).get('name', provider)

    # 1. Deneme: Kod Üretimi
    send_palette_message('statusUpdate', {
        'status': 'loading',
        'message': f'{prov_name} · {model} ile oluşturuluyor...'
    })

    try:
        raw_reply = call_llm_api(provider, model, messages, api_key, timeout=timeout, base_url=base_url)
        aicad_log(f"LLM yanıtı alındı (uzunluk: {len(raw_reply)})")
    except Exception as e:
        aicad_log(f"generate_cad_worker LLM çağrı hatası: {e}")
        send_palette_message('taskResult', {
            'status': 'error',
            'message': str(e),
            'error': traceback.format_exc(),
        })
        return

    code = extract_python_code(raw_reply)
    if not code:
        aicad_log("Modelden doğrudan Python kodu gelmedi, sohbet/rehberlik yanıtı olarak iletiliyor.")
        send_palette_message('taskResult', {
            'status': 'chat',
            'message': raw_reply,
        })
        return

    # 1. Deneme: Fusion'da Çalıştırma
    send_palette_message('statusUpdate', {
        'status': 'loading',
        'message': 'Fusion 360 içinde yürütülüyor...',
    })

    exec_res = run_code_on_main_thread(code)

    if exec_res['success']:
        new_b = exec_res.get('new_bodies', [])
        b_info = f" ({', '.join(new_b)} eklendi)" if new_b else ""
        send_palette_message('taskResult', {
            'status': 'success',
            'message': f'CAD Modeli başarıyla oluşturuldu!{b_info}',
        })
        return

    # Multi-Attempt Self-Healing Loop: Hata Alındığında pes etmeden onarmaya devam et (3 Denemeye kadar)
    current_code = code
    current_exec_res = exec_res
    healing_attempts = 0
    max_healing_attempts = 3

    while not current_exec_res.get('success') and healing_attempts < max_healing_attempts:
        healing_attempts += 1
        err_msg = current_exec_res.get('error', 'Bilinmeyen hata')
        err_tb = current_exec_res.get('traceback', '')
        aicad_log(f"{healing_attempts}. Onarım Denemesi başlatılıyor: {err_msg}")

        send_palette_message('statusUpdate', {
            'status': 'healing',
            'message': f'Hata tespit edildi, onarılıyor... (Deneme {healing_attempts}/{max_healing_attempts})',
        })

        specific_tip = ""
        if 'HİÇBİR YENİ 3D KATI GÖVDE EKLENMEDİ' in err_msg or 'No bodies added' in err_msg:
            specific_tip = "ÖNEMLİ İPUCU: Çizim sadece 2D eskiz olarak kaldı! Mutlaka kapalı profili extrudes.add(extInput) ve NewBodyFeatureOperation ile 3D katı gövdeye dönüştür.\n"
        elif 'Kesilecek veya kesişecek hedef gövde bulunamadı' in err_msg:
            specific_tip = "ÖNEMLİ İPUCU: CutFeatureOperation veya JoinFeatureOperation boşlukta hata verir! Kesinlikle 'adsk.fusion.FeatureOperations.NewBodyFeatureOperation' kullan.\n"
        elif 'profiles.item' in err_msg:
            specific_tip = "ÖNEMLİ İPUCU: Eskiz profili kapalı değil veya bulunamadı! Çizgilerin uç uca tam kapandığından emin ol ya da sketch.profiles.count kontrolü yap.\n"

        healing_prompt = (
            f"Fusion 360 API şu hatayı verdi ({healing_attempts}. deneme):\n{err_msg}\n\n"
            f"Detaylı Traceback:\n{err_tb}\n\n"
            f"{specific_tip}"
            f"Lütfen çizimi, düzlemi veya parametreleri düzelterek kodu yeniden ver. "
            f"Sadece ```python ... ``` bloğu içinde saf ve hatasız Fusion 360 Python kodu döndür."
        )

        messages_attempt = [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt},
            {'role': 'assistant', 'content': f"```python\n{current_code}\n```"},
            {'role': 'user', 'content': healing_prompt}
        ]

        try:
            raw_reply_h = call_llm_api(provider, model, messages_attempt, api_key, timeout=timeout, base_url=base_url)
            code_h = extract_python_code(raw_reply_h)
        except Exception as e:
            aicad_log(f"Self-Healing LLM hatası: {e}")
            break

        if not code_h:
            aicad_log(f"Self-Healing: Model geçerli kod üretemedi (Deneme {healing_attempts})")
            break

        current_code = code_h

        send_palette_message('statusUpdate', {
            'status': 'loading',
            'message': f'Düzeltilen kod yürütülüyor ({healing_attempts}/{max_healing_attempts})...',
        })

        current_exec_res = run_code_on_main_thread(current_code)
        if current_exec_res.get('success'):
            break

    if current_exec_res.get('success'):
        new_b = current_exec_res.get('new_bodies', [])
        b_info = f" ({', '.join(new_b)} eklendi)" if new_b else ""
        send_palette_message('taskResult', {
            'status': 'success',
            'message': f'CAD Modeli onarılarak başarıyla oluşturuldu!{b_info}',
        })
    else:
        send_palette_message('taskResult', {
            'status': 'error',
            'message': f"Onarım tamamlanamadı: {current_exec_res.get('error', 'Bilinmeyen hata')}",
        })


# --- Fusion Event Handlers ---

class PaletteHTMLEventHandler(adsk.core.HTMLEventHandler):
    """HTML Arayüzünden gelen mesajları karşılar."""
    def notify(self, args):
        try:
            html_args = adsk.core.HTMLEventArgs.cast(args)
            action = html_args.action
            data_str = html_args.data
            aicad_log(f"PaletteHTMLEventHandler: action='{action}' alındı.")
            data = json.loads(data_str) if data_str else {}

            if action == 'executeCADCode':
                code = data.get('code', '')
                aicad_log(f"executeCADCode doğrudan icra ediliyor (uzunluk: {len(code)})")
                res = execute_code(code)
                html_args.returnData = json.dumps(res)
                return

            elif action == 'callLLM':
                provider = data.get('provider', '')
                model = data.get('model', '')
                messages = data.get('messages', [])
                api_key = data.get('apiKey', '')
                base_url = data.get('baseUrl') or data.get('base_url')
                timeout = data.get('timeout', 90)
                if provider == 'local':
                    timeout = max(timeout, 150)
                aicad_log(f"callLLM isteği: provider={provider}, model={model}, baseUrl={base_url}")
                try:
                    raw_reply = call_llm_api(provider, model, messages, api_key=api_key, timeout=timeout, base_url=base_url)
                    html_args.returnData = json.dumps({'success': True, 'reply': raw_reply})
                except Exception as e:
                    tb = traceback.format_exc()
                    aicad_log(f"callLLM hatası: {e}\n{tb}")
                    html_args.returnData = json.dumps({'success': False, 'error': str(e), 'traceback': tb})
                return

            elif action == 'initUI':
                def check_ollama():
                    result = fetch_models('ollama')
                    send_palette_message('setOllamaModels', result)
                threading.Thread(target=check_ollama, daemon=True).start()
                html_args.returnData = json.dumps({'status': 'initUI_started'})
                return

            elif action == 'fetchModels':
                provider = data.get('provider', '')
                api_key = data.get('apiKey', '')
                base_url = data.get('baseUrl') or data.get('base_url')
                aicad_log(f"fetchModels doğrudan çalıştırılıyor: provider={provider}, base_url={base_url}")
                try:
                    result = fetch_models(provider, api_key, base_url=base_url)
                    result['provider'] = provider
                    html_args.returnData = json.dumps(result)
                    try:
                        send_palette_message('modelsResult', result)
                    except Exception:
                        pass
                except Exception as e:
                    tb = traceback.format_exc()
                    aicad_log(f"fetchModels hatası: {e}\n{tb}")
                    html_args.returnData = json.dumps({'success': False, 'error': str(e), 'models': []})
                return

            elif action == 'generateCAD':
                aicad_log("generateCAD arka plan görevi başlatılıyor...")
                html_args.returnData = json.dumps({'status': 'generateCAD_started'})
                threading.Thread(target=generate_cad_worker, args=(data,), daemon=True).start()
                return

            elif action in ('getDesignState', 'inspectDesign'):
                aicad_log("PaletteHTMLEventHandler: getDesignState çağrıldı.")
                res = inspect_current_design()
                html_args.returnData = json.dumps({'success': True, 'design': res})
                return

            else:
                html_args.returnData = json.dumps({'status': 'ok'})

        except Exception as e:
            tb = traceback.format_exc()
            aicad_log(f"PaletteHTMLEventHandler HATA: {e}\n{tb}")
            try:
                html_args.returnData = json.dumps({'status': 'error', 'message': str(e), 'traceback': tb})
            except Exception:
                pass


class PaletteClosedHandler(adsk.core.UserInterfaceGeneralEventHandler):
    """Palet kapatıldığında tetiklenir."""
    def notify(self, args):
        aicad_log("Palet kapatıldı.")


class CustomEventHandler(adsk.core.CustomEventHandler):
    """Arka plan thread'lerinden gelen komutları Fusion ana thread'inde yürütür."""
    def notify(self, args):
        global app, ui
        try:
            event_args = adsk.core.CustomEventArgs.cast(args)
            payload = json.loads(event_args.additionalInfo)
            act = payload.get('action')
            aicad_log(f"CustomEventHandler tetiklendi: act={act}")

            if act == 'send_to_html':
                p = get_active_palette()
                if p:
                    html_action = payload.get('html_action')
                    html_data = json.dumps(payload.get('html_data', {}))
                    p.sendInfoToHTML(html_action, html_data)
                    aicad_log(f"CustomEventHandler HTML'e gönderdi: {html_action}")
                else:
                    aicad_log("CustomEventHandler: Aktif palet bulunamadı!")

            elif act == 'execute_code':
                task_id = payload.get('task_id')
                code = payload.get('code', '')
                res = execute_code(code)
                with task_lock:
                    if task_id in pending_tasks:
                        pending_tasks[task_id]['result'] = res
                        pending_tasks[task_id]['event'].set()

            elif act == 'get_design_state':
                task_id = payload.get('task_id')
                res = inspect_current_design()
                with task_lock:
                    if task_id in pending_tasks:
                        pending_tasks[task_id]['result'] = res
                        pending_tasks[task_id]['event'].set()

        except Exception as e:
            tb = traceback.format_exc()
            aicad_log(f"CustomEventHandler HATA: {e}\n{tb}")


class ShowPaletteCommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            show_palette()
        except Exception as e:
            tb = traceback.format_exc()
            aicad_log(f"Palet açılırken hata oluştu: {e}\n{tb}")
            try:
                create_palette()
            except Exception:
                pass


class ShowPaletteCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            cmd = args.command
            on_execute = ShowPaletteCommandExecuteHandler()
            cmd.execute.add(on_execute)
            handlers.append(on_execute)
        except Exception:
            traceback.print_exc()


def create_palette():
    """AI CAD Studio paletini oluşturur veya var olanı temizleyip yeniden açar."""
    global palette, app, ui, handlers
    palettes = ui.palettes
    existing = palettes.itemById(PALETTE_ID)
    if existing:
        try:
            existing.deleteMe()
        except Exception:
            pass

    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, 'index.html').replace('\\', '/')

    palette = palettes.add(
        id=PALETTE_ID, name=PALETTE_NAME, htmlFileURL=html_path,
        isVisible=True, showCloseButton=True, isResizable=True,
        width=420, height=720, useNewWebBrowser=True
    )

    html_handler = PaletteHTMLEventHandler()
    palette.incomingFromHTML.add(html_handler)
    handlers.append(html_handler)

    close_handler = PaletteClosedHandler()
    palette.closed.add(close_handler)
    handlers.append(close_handler)

    try:
        palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
    except Exception as dock_err:
        aicad_log(f"create_palette dockingState ayarlanamadı (zararsız): {dock_err}")

    try:
        palette.isVisible = True
    except Exception:
        pass

    return palette


def show_palette():
    global palette
    if not palette:
        create_palette()
    else:
        try:
            palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
        except Exception as dock_err:
            aicad_log(f"show_palette dockingState ayarlanamadı (zararsız): {dock_err}")
        try:
            palette.isVisible = True
        except Exception:
            create_palette()


def setup_toolbar_button():
    global ui, handlers
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_folder = os.path.join(current_dir, 'resources')
        if not os.path.exists(icon_folder):
            icon_folder = os.path.join(current_dir, 'commands', 'paletteShow', 'resources')

        workspace = ui.workspaces.itemById('FusionSolidEnvironment')
        if not workspace:
            aicad_log("FusionSolidEnvironment bulunamadı!")
            return

        cmd_def = ui.commandDefinitions.itemById(CMD_ID)
        if cmd_def:
            try:
                cmd_def.deleteMe()
            except Exception:
                pass
            cmd_def = None

        cmd_def = ui.commandDefinitions.addButtonDefinition(
            CMD_ID,
            CMD_NAME,
            CMD_DESC,
            icon_folder
        )
        on_cmd_created = ShowPaletteCommandCreatedHandler()
        cmd_def.commandCreated.add(on_cmd_created)
        handlers.append(on_cmd_created)

        # 1. Modern Ribbon Tab: FusionSolidEnvironment -> SolidTab
        panel = None
        try:
            solid_tab = workspace.toolbarTabs.itemById('SolidTab')
            if solid_tab:
                panel = solid_tab.toolbarPanels.itemById(TOOLBAR_PANEL_ID)
                if not panel:
                    try:
                        # Position right after SolidSelectPanel (SEÇ)
                        panel = solid_tab.toolbarPanels.add(TOOLBAR_PANEL_ID, TOOLBAR_PANEL_NAME, 'SolidSelectPanel', False)
                        aicad_log("SolidTab üzerinde SolidSelectPanel (SEÇ) yanına AI CAD paneli eklendi.")
                    except Exception as e1:
                        aicad_log(f"SolidSelectPanel yanına eklenemedi ({e1}), tab sonuna ekleniyor...")
                        panel = solid_tab.toolbarPanels.add(TOOLBAR_PANEL_ID, TOOLBAR_PANEL_NAME)
        except Exception as e:
            aicad_log(f"toolbarTabs üzerinden panel ekleme hatası: {e}")

        # 2. Fallback: workspace.toolbarPanels
        if not panel:
            try:
                panel = workspace.toolbarPanels.itemById(TOOLBAR_PANEL_ID)
                if not panel:
                    try:
                        panel = workspace.toolbarPanels.add(TOOLBAR_PANEL_ID, TOOLBAR_PANEL_NAME, 'SolidSelectPanel', False)
                    except Exception:
                        panel = workspace.toolbarPanels.add(TOOLBAR_PANEL_ID, TOOLBAR_PANEL_NAME)
            except Exception as e:
                aicad_log(f"workspace.toolbarPanels üzerinden panel ekleme hatası: {e}")

        # 3. Add command to panel and promote it to ribbon
        if panel:
            ctrl = panel.controls.itemById(CMD_ID)
            if not ctrl:
                ctrl = panel.controls.addCommand(cmd_def)
            ctrl.isPromoted = True
            ctrl.isPromotedByDefault = True
            ctrl.isVisible = True
            aicad_log(f"AI CAD Studio butonu {panel.id} paneline eklendi ve ribbon üzerinde öne çıkarıldı (promoted).")

        # 4. Fallback in SolidScriptsAddinsPanel as secondary location
        try:
            scripts_panel = workspace.toolbarPanels.itemById('SolidScriptsAddinsPanel')
            if scripts_panel and not scripts_panel.controls.itemById(CMD_ID):
                scripts_panel.controls.addCommand(cmd_def)
        except Exception:
            pass

    except Exception as e:
        tb = traceback.format_exc()
        aicad_log(f"setup_toolbar_button HATA: {e}\n{tb}")


# ── Local Web Bridge HTTP Server (for Chrome / Edge / Web access) ──

LOCAL_HTTP_PORT = 49876
local_http_server = None
local_http_thread = None

class LocalBridgeHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Harici web tarayıcıları (Chrome/Edge) ile Fusion 360 arasındaki yerel HTTP köprüsü."""

    def _set_cors_headers(self, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors_headers(200)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path in ('/health', '/status', '/'):
            self._set_cors_headers(200)
            res = {
                'status': 'ok',
                'app': 'Fusion360',
                'connected': True,
                'version': '1.0.0',
                'activeDesign': bool(adsk.fusion.Design.cast(app.activeProduct)) if app else False
            }
            self.wfile.write(json.dumps(res).encode('utf-8'))
        elif path in ('/design_state', '/inspect'):
            self._set_cors_headers(200)
            res = get_design_state_on_main_thread()
            self.wfile.write(json.dumps({'success': True, 'design': res}).encode('utf-8'))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({'error': 'Not found'}).encode('utf-8'))

    def do_POST(self):
        path = self.path.split('?')[0]
        content_len = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_len) if content_len > 0 else b'{}'
        
        try:
            body = json.loads(post_data.decode('utf-8'))
        except Exception:
            body = {}

        if path == '/execute':
            code = body.get('code', '')
            aicad_log(f"Yerel Web Köprüsünden kod çalıştırma isteği alındı (uzunluk: {len(code)})")
            exec_res = run_code_on_main_thread(code)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(exec_res).encode('utf-8'))

        elif path == '/open_folder':
            folder = os.path.dirname(os.path.abspath(__file__))
            try:
                os.startfile(folder)
            except Exception:
                pass
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({'status': 'ok', 'folder': folder}).encode('utf-8'))

        elif path in ('/design_state', '/inspect'):
            self._set_cors_headers(200)
            res = get_design_state_on_main_thread()
            self.wfile.write(json.dumps({'success': True, 'design': res}).encode('utf-8'))

        elif path == '/call_llm':
            provider = body.get('provider', '')
            model = body.get('model', '')
            messages = body.get('messages', [])
            api_key = body.get('apiKey', '')
            base_url = body.get('baseUrl') or body.get('base_url')
            timeout = body.get('timeout', 90)
            if provider == 'local':
                timeout = max(timeout, 150)
            try:
                raw_reply = call_llm_api(provider, model, messages, api_key=api_key, timeout=timeout, base_url=base_url)
                self._set_cors_headers(200)
                self.wfile.write(json.dumps({'success': True, 'reply': raw_reply}).encode('utf-8'))
            except Exception as e:
                self._set_cors_headers(200)
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode('utf-8'))

        elif path == '/fetch_models':
            provider = body.get('provider', '')
            api_key = body.get('apiKey', '')
            base_url = body.get('baseUrl') or body.get('base_url')
            res = fetch_models(provider, api_key=api_key, base_url=base_url)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(res).encode('utf-8'))

        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({'error': 'Endpoint bulunamadı'}).encode('utf-8'))

    def log_message(self, format, *args):
        # Sessiz log
        pass


def start_local_bridge_server():
    """Yerel HTTP köprü sunucusunu arka plan daemon thread'inde başlatır."""
    global local_http_server, local_http_thread
    try:
        class ReusableTCPServer(http.server.HTTPServer):
            allow_reuse_address = True

        local_http_server = ReusableTCPServer(('127.0.0.1', LOCAL_HTTP_PORT), LocalBridgeHTTPHandler)
        aicad_log(f"Yerel Web Köprüsü 127.0.0.1:{LOCAL_HTTP_PORT} portunda başlatıldı.")

        def serve():
            try:
                local_http_server.serve_forever()
            except Exception:
                pass

        local_http_thread = threading.Thread(target=serve, daemon=True)
        local_http_thread.start()
    except Exception as e:
        aicad_log(f"Yerel Web Köprüsü başlatılamadı: {e}")


def stop_local_bridge_server():
    """Yerel HTTP sunucusunu durdurur."""
    global local_http_server
    if local_http_server:
        try:
            local_http_server.shutdown()
            local_http_server.server_close()
            aicad_log("Yerel Web Köprüsü durduruldu.")
        except Exception:
            pass
        local_http_server = None


# --- Add-In Lifecycle ---

def run(context):
    global app, ui, custom_event, handlers
    try:
        aicad_log("=== AICADBridge run() başlatıldı ===")
        app = adsk.core.Application.get()
        ui = app.userInterface

        try:
            app.unregisterCustomEvent(CUSTOM_EVENT_ID)
        except Exception:
            pass

        custom_event = app.registerCustomEvent(CUSTOM_EVENT_ID)
        custom_handler = CustomEventHandler()
        custom_event.add(custom_handler)
        handlers.append(custom_handler)

        setup_toolbar_button()
        create_palette()
        start_local_bridge_server()
        aicad_log("AICADBridge başarıyla başlatıldı, palet ve web köprüsü açıldı.")

    except Exception:
        tb = traceback.format_exc()
        aicad_log(f"AICADBridge Başlatma Hatası: {tb}")
        if ui:
            ui.messageBox(f"AICADBridge Başlatma Hatası:\n{tb}")


def stop(context):
    global app, ui, palette, custom_event, handlers
    try:
        aicad_log("=== AICADBridge stop() çağrıldı ===")
        stop_local_bridge_server()

        if palette:
            palette.deleteMe()
            palette = None

        if ui:
            workspace = ui.workspaces.itemById('FusionSolidEnvironment')
            if workspace:
                # Clean from SolidTab
                try:
                    solid_tab = workspace.toolbarTabs.itemById('SolidTab')
                    if solid_tab:
                        p = solid_tab.toolbarPanels.itemById(TOOLBAR_PANEL_ID)
                        if p:
                            c = p.controls.itemById(CMD_ID)
                            if c:
                                c.deleteMe()
                            p.deleteMe()
                except Exception:
                    pass

                # Clean from workspace.toolbarPanels
                try:
                    p = workspace.toolbarPanels.itemById(TOOLBAR_PANEL_ID)
                    if p:
                        c = p.controls.itemById(CMD_ID)
                        if c:
                            c.deleteMe()
                        p.deleteMe()
                except Exception:
                    pass

                # Clean from SolidScriptsAddinsPanel
                try:
                    p = workspace.toolbarPanels.itemById('SolidScriptsAddinsPanel')
                    if p:
                        c = p.controls.itemById(CMD_ID)
                        if c:
                            c.deleteMe()
                except Exception:
                    pass

            cmd_def = ui.commandDefinitions.itemById(CMD_ID)
            if cmd_def:
                cmd_def.deleteMe()

        if app and custom_event:
            app.unregisterCustomEvent(CUSTOM_EVENT_ID)
            custom_event = None

        handlers.clear()
        aicad_log("AICADBridge başarıyla durduruldu.")
    except Exception:
        pass