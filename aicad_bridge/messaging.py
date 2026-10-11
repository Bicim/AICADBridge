"""Palet ve HTML arayüzü arasındaki mesajlaşma."""

import json

from aicad_bridge import runtime
from aicad_bridge.runtime import CUSTOM_EVENT_ID, PALETTE_ID, aicad_log


def get_active_palette():
    """Mevcut açık paleti güvenli şekilde bulur."""
    if runtime.palette:
        return runtime.palette
    if runtime.ui:
        try:
            return runtime.ui.palettes.itemById(PALETTE_ID)
        except Exception:
            pass
    return None


def send_palette_message(action, data):
    """Palete güvenli mesaj gönderir."""
    aicad_log(f"send_palette_message: action={action}")
    p = get_active_palette()
    if p:
        try:
            p.sendInfoToHTML(action, json.dumps(data))
            aicad_log(f"send_palette_message doğrudan palete iletildi: action={action}")
            return
        except Exception as e:
            aicad_log(f"Doğrudan palette.sendInfoToHTML başarısız ({e}), CustomEvent deneniyor...")

    if runtime.app and runtime.custom_event:
        payload = {
            'action': 'send_to_html',
            'html_action': action,
            'html_data': data
        }
        runtime.app.fireCustomEvent(CUSTOM_EVENT_ID, json.dumps(payload))
