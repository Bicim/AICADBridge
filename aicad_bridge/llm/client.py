"""Çoklu sağlayıcı LLM istemcisi ve hata çevirisi."""

import json
import re
import urllib.error
import urllib.request

from aicad_bridge.llm.registry import PROVIDERS


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
