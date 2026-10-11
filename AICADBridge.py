"""
Fusion 360 AI CAD Studio Add-in (AICADBridge)
Doğal dil ile 3D modelleme asistanı.
Çoklu sağlayıcı destekli (Ollama, OpenAI, Anthropic, Google, Groq, OpenRouter, DeepSeek)
ve Self-Healing CAD code generation loop.

İnce giriş noktası: yaşam döngüsü (run/stop) burada; tüm mantık
`aicad_bridge` paketi içinde modüler olarak yaşar.
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import adsk.core

from aicad_bridge import events, runtime
from aicad_bridge.bridge import local_http
from aicad_bridge.ui import palette as ui_palette
from aicad_bridge.ui import toolbar as ui_toolbar


def run(context):
    try:
        runtime.aicad_log("=== AICADBridge run() başlatıldı ===")
        runtime.app = adsk.core.Application.get()
        runtime.ui = runtime.app.userInterface

        try:
            runtime.app.unregisterCustomEvent(runtime.CUSTOM_EVENT_ID)
        except Exception:
            pass

        runtime.custom_event = runtime.app.registerCustomEvent(runtime.CUSTOM_EVENT_ID)
        custom_handler = events.CustomEventHandler()
        runtime.custom_event.add(custom_handler)
        runtime.handlers.append(custom_handler)

        ui_toolbar.setup_toolbar_button()
        ui_palette.create_palette()
        local_http.start_local_bridge_server()
        runtime.aicad_log("AICADBridge başarıyla başlatıldı, palet ve web köprüsü açıldı.")

    except Exception:
        tb = traceback.format_exc()
        runtime.aicad_log(f"AICADBridge Başlatma Hatası: {tb}")
        if runtime.ui:
            runtime.ui.messageBox(f"AICADBridge Başlatma Hatası:\n{tb}")


def stop(context):
    try:
        runtime.aicad_log("=== AICADBridge stop() çağrıldı ===")
        local_http.stop_local_bridge_server()

        ui_palette.dispose_palette()
        ui_toolbar.cleanup_toolbar()

        if runtime.app and runtime.custom_event:
            runtime.app.unregisterCustomEvent(runtime.CUSTOM_EVENT_ID)
            runtime.custom_event = None

        runtime.handlers.clear()
        runtime.aicad_log("AICADBridge başarıyla durduruldu.")
    except Exception:
        pass
