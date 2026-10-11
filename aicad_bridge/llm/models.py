"""Sağlayıcılardan kullanılabilir model listelerinin çekilmesi."""

import json
import urllib.error
import urllib.request

from aicad_bridge.llm.registry import PROVIDERS


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
