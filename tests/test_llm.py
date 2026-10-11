from aicad_bridge.llm.client import translate_api_error_tr
from aicad_bridge.llm.prompt import SYSTEM_PROMPT, extract_python_code
from aicad_bridge.llm.registry import PROVIDERS


def test_system_prompt_design_protocols():
    assert "TASARIM PLANI" in SYSTEM_PROMPT
    assert "nasıl yapalım" in SYSTEM_PROMPT
    assert "EK DOSYA" in SYSTEM_PROMPT
    assert "PARÇA LİSTESİ" in SYSTEM_PROMPT


def test_extract_python_code_with_python_block():
    text = "İşte kod:\n```python\nimport adsk.core\nprint(1)\n```\nTamamlandı."
    assert extract_python_code(text) == "import adsk.core\nprint(1)"


def test_extract_python_code_with_plain_block():
    text = "```\nprint(2)\n```"
    assert extract_python_code(text) == "print(2)"


def test_extract_python_code_empty_when_no_code():
    assert extract_python_code("Sadece sohbet yanıtı") == ""
    assert extract_python_code("") == ""
    assert extract_python_code(None) == ""


def test_translate_quota_error():
    msg = translate_api_error_tr("You exceeded your current quota", "openai")
    assert "kota" in msg.lower()


def test_translate_auth_error():
    msg = translate_api_error_tr("incorrect api key provided", "openai")
    assert "anahtar" in msg.lower()


def test_translate_local_connection_error():
    msg = translate_api_error_tr("connection refused", "local")
    assert "LM Studio" in msg or "Ollama" in msg


def test_translate_rate_limit_error():
    msg = translate_api_error_tr("Rate limit exceeded for requests", "groq")
    assert "Rate limit" in msg or "istek sınırı" in msg


def test_providers_registry_shape():
    assert len(PROVIDERS) == 8
    assert PROVIDERS['ollama']['needs_key'] is False
    assert PROVIDERS['local']['needs_key'] is False
    assert PROVIDERS['anthropic']['format'] == 'anthropic'
    assert PROVIDERS['google']['format'] == 'google'
    for key, prov in PROVIDERS.items():
        assert prov['chat_url'], key
        assert prov['models_url'], key
        assert prov['format'] in ('openai', 'anthropic', 'google'), key
        assert prov['name'], key
