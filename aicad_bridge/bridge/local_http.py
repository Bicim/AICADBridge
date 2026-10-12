"""Harici tarayıcılar ve SolidWorks bağımsız modu için yerel HTTP köprüsü (localhost:49876)."""

import http.server
import json
import os
import threading
import urllib.parse

try:
    import adsk.core
    import adsk.fusion
except ImportError:
    adsk = None

from aicad_bridge import adapters, config as app_config, events, runtime
from aicad_bridge.adapters import solidworks
from aicad_bridge.llm import pipeline as llm_pipeline
from aicad_bridge.llm.client import call_llm_api
from aicad_bridge.llm.models import fetch_models
from aicad_bridge.runtime import LOCAL_HTTP_PORT, aicad_log

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LocalBridgeHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Harici web tarayıcıları (Chrome/Edge) ile Fusion 360 / SolidWorks arasındaki yerel HTTP köprüsü."""

    def _set_cors_headers(self, status=200, content_type='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors_headers(200)

    def _parse_query(self):
        if '?' not in self.path:
            return {}
        qs = self.path.split('?', 1)[1]
        return {k: v[0] for k, v in urllib.parse.parse_qs(qs).items() if v}

    def do_GET(self):
        path = self.path.split('?')[0]
        query = self._parse_query()

        if path in ('/app', '/index.html', '/ui'):
            html_file = os.path.join(_REPO_ROOT, 'index.html')
            if os.path.isfile(html_file):
                self._set_cors_headers(200, content_type='text/html; charset=utf-8')
                with open(html_file, 'rb') as f:
                    self.wfile.write(f.read())
                return

        if path in ('/health', '/status', '/'):
            target = adapters.get_active_cad_target(query.get('cad_target'))
            sw_avail = solidworks.is_available()
            fusion_avail = bool(adsk and runtime.app)
            if target == 'solidworks':
                active_design = sw_avail
                app_name = 'SolidWorks'
            else:
                try:
                    active_design = bool(adsk.fusion.Design.cast(runtime.app.activeProduct)) if (adsk and runtime.app) else False
                except Exception:
                    active_design = False
                app_name = 'Fusion360'

            self._set_cors_headers(200)
            res = {
                'status': 'ok',
                'app': app_name,
                'cad_target': target,
                'connected': True,
                'solidworksConnected': sw_avail,
                'fusionConnected': fusion_avail,
                'version': '1.1.0-solidworks',
                'activeDesign': active_design,
            }
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif path == '/config':
            self._set_cors_headers(200)
            pub = app_config.get_public_settings()
            self.wfile.write(json.dumps(pub).encode('utf-8'))

        elif path == '/cad_target':
            self._set_cors_headers(200)
            target = adapters.get_active_cad_target()
            self.wfile.write(json.dumps({
                'ok': True,
                'cad_target': target,
                'solidworksConnected': solidworks.is_available(),
                'fusionConnected': bool(adsk and runtime.app),
            }).encode('utf-8'))

        elif path in ('/design_state', '/inspect'):
            target = adapters.get_active_cad_target(query.get('cad_target'))
            self._set_cors_headers(200)
            res = events.get_design_state_on_main_thread(cad_target=target)
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

        req_target = adapters.get_active_cad_target(body.get('cad_target'))

        if path == '/execute':
            code = body.get('code', '')
            aicad_log(f"Yerel Web Köprüsünden ({req_target}) kod çalıştırma isteği alındı (uzunluk: {len(code)})")
            exec_res = events.run_code_on_main_thread(code, cad_target=req_target)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(exec_res).encode('utf-8'))

        elif path == '/cad_target':
            new_target = body.get('cad_target') or body.get('target')
            try:
                resolved = adapters.set_active_cad_target(new_target)
                aicad_log(f"Aktif CAD hedefi değiştirildi: {resolved}")
                self._set_cors_headers(200)
                self.wfile.write(json.dumps({
                    'ok': True,
                    'cad_target': resolved,
                    'solidworksConnected': solidworks.is_available(),
                    'fusionConnected': bool(adsk and runtime.app),
                }).encode('utf-8'))
            except Exception as e:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({'ok': False, 'error': str(e)}).encode('utf-8'))

        elif path == '/update_params':
            params = body.get('params') or {}
            res = solidworks.update_parameters(params)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif path == '/open_folder':
            folder = _REPO_ROOT
            try:
                os.startfile(folder)
            except Exception:
                pass
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({'status': 'ok', 'folder': folder}).encode('utf-8'))

        elif path in ('/design_state', '/inspect'):
            self._set_cors_headers(200)
            res = events.get_design_state_on_main_thread(cad_target=req_target)
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
            body_with_target = dict(body)
            body_with_target.setdefault('cad_target', req_target)
            res = llm_pipeline.run_pipeline_helper(
                body_with_target,
                inspect_state=lambda: events.get_design_state_on_main_thread(cad_target=req_target),
                capture_viewport=lambda w=900, h=600: events.capture_viewport_on_main_thread(w, h, cad_target=req_target),
            )
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
        pass


def start_local_bridge_server():
    """Yerel HTTP köprü sunucusunu arka plan daemon thread'inde başlatır."""
    try:
        class ReusableTCPServer(http.server.ThreadingHTTPServer):
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
