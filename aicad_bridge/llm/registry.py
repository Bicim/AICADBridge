"""Desteklenen LLM sağlayıcılarının kaydı."""

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
