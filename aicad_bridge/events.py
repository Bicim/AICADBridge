"""Fusion ana thread'i ile arka plan thread'leri arasındaki görev köprüsü."""

import json
import threading
import time
import traceback

import adsk.core

from aicad_bridge import runtime
from aicad_bridge.adapters import fusion360
from aicad_bridge.messaging import get_active_palette
from aicad_bridge.runtime import CUSTOM_EVENT_ID, aicad_log


def get_design_state_on_main_thread():
    """Fusion ana thread'inde aktif tasarımı analiz edip sonucunu bekler."""
    if not runtime.app or not runtime.custom_event:
        return fusion360.inspect_current_design()
    task_id = str(time.time())
    evt = threading.Event()
    with runtime.task_lock:
        runtime.pending_tasks[task_id] = {'event': evt, 'result': None}

    payload = {'action': 'get_design_state', 'task_id': task_id}
    runtime.app.fireCustomEvent(CUSTOM_EVENT_ID, json.dumps(payload))

    completed = evt.wait(timeout=10.0)
    with runtime.task_lock:
        task_data = runtime.pending_tasks.pop(task_id, None)

    if not completed or not task_data or not task_data.get('result'):
        return fusion360.inspect_current_design()
    return task_data['result']


def run_code_on_main_thread(code):
    """Fusion ana thread'inde Python kodunu çalıştırır ve sonucunu bekler."""
    task_id = str(time.time())
    evt = threading.Event()
    task = {'event': evt, 'result': None}
    with runtime.task_lock:
        runtime.pending_tasks[task_id] = task

    payload = {'action': 'execute_code', 'task_id': task_id, 'code': code}
    runtime.app.fireCustomEvent(CUSTOM_EVENT_ID, json.dumps(payload))

    completed = evt.wait(timeout=45.0)
    with runtime.task_lock:
        task_data = runtime.pending_tasks.pop(task_id, None)

    if not completed or not task_data or not task_data.get('result'):
        return {'success': False, 'error': 'İşlem zaman aşımına uğradı (45 saniye).', 'traceback': ''}
    return task_data['result']


def capture_viewport_on_main_thread(width=900, height=600):
    """Fusion ana thread'inde viewport ekran görüntüsü alıp sonucunu bekler."""
    if not runtime.app or not runtime.custom_event:
        return fusion360.capture_viewport_image(width, height)
    task_id = str(time.time())
    evt = threading.Event()
    with runtime.task_lock:
        runtime.pending_tasks[task_id] = {'event': evt, 'result': None}

    payload = {'action': 'capture_viewport', 'task_id': task_id, 'width': width, 'height': height}
    runtime.app.fireCustomEvent(CUSTOM_EVENT_ID, json.dumps(payload))

    completed = evt.wait(timeout=15.0)
    with runtime.task_lock:
        task_data = runtime.pending_tasks.pop(task_id, None)

    if not completed or not task_data or not task_data.get('result'):
        return {'success': False, 'error': 'Viewport görüntüsü alınamadı (zaman aşımı).'}
    return task_data['result']


class CustomEventHandler(adsk.core.CustomEventHandler):
    """Arka plan thread'lerinden gelen komutları Fusion ana thread'inde yürütür."""
    def notify(self, args):
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
                res = fusion360.execute_code(code)
                with runtime.task_lock:
                    if task_id in runtime.pending_tasks:
                        runtime.pending_tasks[task_id]['result'] = res
                        runtime.pending_tasks[task_id]['event'].set()

            elif act == 'get_design_state':
                task_id = payload.get('task_id')
                res = fusion360.inspect_current_design()
                with runtime.task_lock:
                    if task_id in runtime.pending_tasks:
                        runtime.pending_tasks[task_id]['result'] = res
                        runtime.pending_tasks[task_id]['event'].set()

            elif act == 'capture_viewport':
                task_id = payload.get('task_id')
                res = fusion360.capture_viewport_image(payload.get('width', 900), payload.get('height', 600))
                with runtime.task_lock:
                    if task_id in runtime.pending_tasks:
                        runtime.pending_tasks[task_id]['result'] = res
                        runtime.pending_tasks[task_id]['event'].set()

        except Exception as e:
            tb = traceback.format_exc()
            aicad_log(f"CustomEventHandler HATA: {e}\n{tb}")
