"""Harici tarayıcılar için yerel HTTP köprüsü (localhost:49876)."""

import http.server
import json
import os
import threading

import adsk.core
import adsk.fusion

from aicad_bridge import config as app_config, events, runtime
from aicad_bridge.llm import pipeline as llm_pipeline
from aicad_bridge.llm.client import call_llm_api
from aicad_bridge.llm.models import fetch_models
from aicad_bridge.runtime import LOCAL_HTTP_PORT, aicad_log


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
                'activeDesign': bool(adsk.fusion.Design.cast(runtime.app.activeProduct)) if runtime.app else False
            }
            self.wfile.write(json.dumps(res).encode('utf-8'))
        elif path == '/config':
            # .env / config.py tabanlı yapılandırma (harici tarayıcı modu)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(app_config.get_public_settings()).encode('utf-8'))
        elif path in ('/design_state', '/inspect'):
            self._set_cors_headers(200)
            res = events.get_design_state_on_main_thread()
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
            exec_res = events.run_code_on_main_thread(code)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(exec_res).encode('utf-8'))

        elif path == '/open_folder':
            folder = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            try:
                os.startfile(folder)
            except Exception:
                pass
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({'status': 'ok', 'folder': folder}).encode('utf-8'))

        elif path in ('/design_state', '/inspect'):
            self._set_cors_headers(200)
            res = events.get_design_state_on_main_thread()
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

        elif path == '/pipeline_helper':
            # İki aşamalı hat (Planner/Coder) yardımcıları — harici tarayıcı modu.
            # Bu handler arka plan thread'inde çalıştığı için tasarım inceleme ve
            # viewport yakalama ana thread'e olay köprüsü üzerinden taşınır.
            res = llm_pipeline.run_pipeline_helper(
                body,
                inspect_state=events.get_design_state_on_main_thread,
                capture_viewport=events.capture_viewport_on_main_thread)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(res).encode('utf-8'))

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
    try:
        class ReusableTCPServer(http.server.HTTPServer):
            allow_reuse_address = True

        runtime.local_http_server = ReusableTCPServer(('127.0.0.1', LOCAL_HTTP_PORT), LocalBridgeHTTPHandler)
        aicad_log(f"Yerel Web Köprüsü 127.0.0.1:{LOCAL_HTTP_PORT} portunda başlatıldı.")

        def serve():
            try:
                runtime.local_http_server.serve_forever()
            except Exception:
                pass

        runtime.local_http_thread = threading.Thread(target=serve, daemon=True)
        runtime.local_http_thread.start()
    except Exception as e:
        aicad_log(f"Yerel Web Köprüsü başlatılamadı: {e}")


def stop_local_bridge_server():
    """Yerel HTTP sunucusunu durdurur."""
    if runtime.local_http_server:
        try:
            runtime.local_http_server.shutdown()
            runtime.local_http_server.server_close()
            aicad_log("Yerel Web Köprüsü durduruldu.")
        except Exception:
            pass
        runtime.local_http_server = None
