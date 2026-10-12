"""Fusion 360 çalışma zamanı durumu: global referanslar, sabitler, görev kaydı ve loglama."""

import os
import threading
import time

PALETTE_ID = 'AICADBridge_Palette'
PALETTE_NAME = 'AI CAD Studio'
CMD_ID = 'AICADBridge_ShowPaletteCmd'
CMD_NAME = 'AI CAD Studio'
CMD_DESC = 'Yapay zeka ile doğal dilden 3D model oluşturan CAD stüdyosu panelini açar.'
TOOLBAR_PANEL_ID = 'AICADBridge_ToolbarPanel'
TOOLBAR_PANEL_NAME = 'AI CAD'
CUSTOM_EVENT_ID = 'AICADBridge_Custom_Event'
LOCAL_HTTP_PORT = 49876

app = None
ui = None
palette = None
custom_event = None
handlers = []
local_http_server = None
local_http_thread = None
active_cad_target = None

task_lock = threading.Lock()
pending_tasks = {}

LOG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'aicad_debug.log'
)


def aicad_log(msg):
    """Zaman damgasıyla aicad_debug.log dosyasına yazar."""
    try:
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass
