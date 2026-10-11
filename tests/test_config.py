"""Yapılandırma modülü (.env / config.py) birim testleri — adsk gerektirmez."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aicad_bridge import config  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Her testten önce AICAD_* değişkenlerini temizler ve önbelleği sıfırlar."""
    for key in list(os.environ.keys()):
        if key.startswith('AICAD_'):
            monkeypatch.delenv(key, raising=False)
    config._cache.clear()
    yield
    config._cache.clear()


def test_parse_env_file_basic(tmp_path):
    env_file = tmp_path / '.env'
    env_file.write_text(
        '# yorum satırı\n'
        'AICAD_PLANNER_MODEL=test-model\n'
        'AICAD_CODER_MODEL="tirnakli-model"\n'
        "\n"
        "AICAD_MAX_TOKENS='8192'\n"
        'GEÇERSİZ SATIR\n',
        encoding='utf-8')
    values = config.parse_env_file(str(env_file))
    assert values['AICAD_PLANNER_MODEL'] == 'test-model'
    assert values['AICAD_CODER_MODEL'] == 'tirnakli-model'   # tırnaklar temizlenir
    assert values['AICAD_MAX_TOKENS'] == '8192'
    assert 'GEÇERSİZ SATIR' not in values


def test_parse_env_file_missing(tmp_path):
    assert config.parse_env_file(str(tmp_path / 'yok.env')) == {}
    assert config.parse_env_file(None) == {}


def test_defaults_when_no_env():
    s = config.get_settings(refresh=True)
    # Model adları varsayılan olarak boştur: boş = sohbet modeli kullanılır
    assert s['planner'] == {'provider': '', 'model': ''}
    assert s['coder'] == {'provider': '', 'model': ''}
    # max_tokens yükseltilmiş varsayılanlar
    assert s['max_tokens'] == 16384
    assert s['vision_max_tokens'] == 4096
    assert s['anthropic_models'] == []


def test_settings_from_env_vars(monkeypatch):
    monkeypatch.setenv('AICAD_PLANNER_PROVIDER', 'OpenAI')
    monkeypatch.setenv('AICAD_PLANNER_MODEL', 'hizli-model')
    monkeypatch.setenv('AICAD_CODER_PROVIDER', 'anthropic')
    monkeypatch.setenv('AICAD_CODER_MODEL', 'güçlü-model')
    monkeypatch.setenv('AICAD_MAX_TOKENS', '32768')
    monkeypatch.setenv('AICAD_VISION_MAX_TOKENS', '2048')
    monkeypatch.setenv('AICAD_ANTHROPIC_MODELS', 'model-a, model-b ,,model-c')
    s = config.get_settings(refresh=True)
    assert s['planner'] == {'provider': 'openai', 'model': 'hizli-model'}  # küçük harfe iner
    assert s['coder'] == {'provider': 'anthropic', 'model': 'güçlü-model'}
    assert s['max_tokens'] == 32768
    assert s['vision_max_tokens'] == 2048
    assert s['anthropic_models'] == ['model-a', 'model-b', 'model-c']


def test_max_tokens_invalid_falls_back(monkeypatch):
    monkeypatch.setenv('AICAD_MAX_TOKENS', 'geçersiz')
    monkeypatch.setenv('AICAD_VISION_MAX_TOKENS', '')
    s = config.get_settings(refresh=True)
    assert s['max_tokens'] == 16384
    assert s['vision_max_tokens'] == 4096


def test_env_file_values_respect_real_env(monkeypatch, tmp_path):
    # .env dosyasındaki değer gerçek ortam değişkenini EZMEZ (öncelik: gerçek env)
    env_file = tmp_path / '.env'
    env_file.write_text('AICAD_MAX_TOKENS=111\nAICAD_PLANNER_MODEL=env-dosyasi-modeli\n', encoding='utf-8')
    values = config.parse_env_file(str(env_file))
    assert values['AICAD_MAX_TOKENS'] == '111'

    monkeypatch.setenv('AICAD_MAX_TOKENS', '222')
    for key, value in values.items():
        os.environ.setdefault(key, value)
    try:
        s = config.get_settings(refresh=True)
        assert s['max_tokens'] == 222           # gerçek env kazanır
        assert s['planner']['model'] == 'env-dosyasi-modeli'  # .env değeri kullanılır
    finally:
        for key in values:
            if os.environ.get(key) == values[key]:
                os.environ.pop(key, None)


def test_public_settings_shape():
    pub = config.get_public_settings(refresh=True)
    assert set(pub.keys()) == {'planner', 'coder', 'max_tokens', 'vision_max_tokens', 'anthropic_models'}
    assert pub['planner']['model'] == ''
    assert pub['max_tokens'] == 16384


def test_settings_cached():
    s1 = config.get_settings(refresh=True)
    s2 = config.get_settings()  # önbellekten
    assert s1 is s2
