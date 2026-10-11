"""Fusion 360 paleti: Dark Neon arayüzün yüklenmesi ve HTML olayları."""

import json
import os
import threading
import traceback

import adsk.core

from aicad_bridge import runtime, worker
from aicad_bridge.adapters import fusion360
from aicad_bridge.llm.client import call_llm_api
from aicad_bridge.llm.models import fetch_models
from aicad_bridge.messaging import send_palette_message
from aicad_bridge.runtime import PALETTE_ID, PALETTE_NAME, aicad_log


class PaletteHTMLEventHandler(adsk.core.HTMLEventHandler):
    """HTML Arayüzünden gelen mesajları karşılar."""
    def notify(self, args):
        try:
            html_args = adsk.core.HTMLEventArgs.cast(args)
            action = html_args.action
            data_str = html_args.data
            aicad_log(f"PaletteHTMLEventHandler: action='{action}' alındı.")
            data = json.loads(data_str) if data_str else {}

            if action == 'executeCADCode':
                code = data.get('code', '')
                aicad_log(f"executeCADCode doğrudan icra ediliyor (uzunluk: {len(code)})")
                res = fusion360.execute_code(code)
                html_args.returnData = json.dumps(res)
                return

            elif action == 'callLLM':
                provider = data.get('provider', '')
                model = data.get('model', '')
                messages = data.get('messages', [])
                api_key = data.get('apiKey', '')
                base_url = data.get('baseUrl') or data.get('base_url')
                timeout = data.get('timeout', 90)
                if provider == 'local':
                    timeout = max(timeout, 150)
                aicad_log(f"callLLM isteği: provider={provider}, model={model}, baseUrl={base_url}")
                try:
                    raw_reply = call_llm_api(provider, model, messages, api_key=api_key, timeout=timeout, base_url=base_url)
                    html_args.returnData = json.dumps({'success': True, 'reply': raw_reply})
                except Exception as e:
                    tb = traceback.format_exc()
                    aicad_log(f"callLLM hatası: {e}\n{tb}")
                    html_args.returnData = json.dumps({'success': False, 'error': str(e), 'traceback': tb})
                return

            elif action == 'initUI':
                def check_ollama():
                    result = fetch_models('ollama')
                    send_palette_message('setOllamaModels', result)
                threading.Thread(target=check_ollama, daemon=True).start()
                html_args.returnData = json.dumps({'status': 'initUI_started'})
                return

            elif action == 'fetchModels':
                provider = data.get('provider', '')
                api_key = data.get('apiKey', '')
                base_url = data.get('baseUrl') or data.get('base_url')
                aicad_log(f"fetchModels doğrudan çalıştırılıyor: provider={provider}, base_url={base_url}")
                try:
                    result = fetch_models(provider, api_key, base_url=base_url)
                    result['provider'] = provider
                    html_args.returnData = json.dumps(result)
                    try:
                        send_palette_message('modelsResult', result)
                    except Exception:
                        pass
                except Exception as e:
                    tb = traceback.format_exc()
                    aicad_log(f"fetchModels hatası: {e}\n{tb}")
                    html_args.returnData = json.dumps({'success': False, 'error': str(e), 'models': []})
                return

            elif action == 'generateCAD':
                aicad_log("generateCAD arka plan görevi başlatılıyor...")
                html_args.returnData = json.dumps({'status': 'generateCAD_started'})
                threading.Thread(target=worker.generate_cad_worker, args=(data,), daemon=True).start()
                return

            elif action in ('getDesignState', 'inspectDesign'):
                aicad_log("PaletteHTMLEventHandler: getDesignState çağrıldı.")
                res = fusion360.inspect_current_design()
                html_args.returnData = json.dumps({'success': True, 'design': res})
                return

            else:
                html_args.returnData = json.dumps({'status': 'ok'})

        except Exception as e:
            tb = traceback.format_exc()
            aicad_log(f"PaletteHTMLEventHandler HATA: {e}\n{tb}")
            try:
                html_args.returnData = json.dumps({'status': 'error', 'message': str(e), 'traceback': tb})
            except Exception:
                pass


class PaletteClosedHandler(adsk.core.UserInterfaceGeneralEventHandler):
    """Palet kapatıldığında tetiklenir."""
    def notify(self, args):
        aicad_log("Palet kapatıldı.")


def create_palette():
    """AI CAD Studio paletini oluşturur veya var olanı temizleyip yeniden açar."""
    palettes = runtime.ui.palettes
    existing = palettes.itemById(PALETTE_ID)
    if existing:
        try:
            existing.deleteMe()
        except Exception:
            pass

    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    html_path = os.path.join(current_dir, 'index.html').replace('\\', '/')

    runtime.palette = palettes.add(
        id=PALETTE_ID, name=PALETTE_NAME, htmlFileURL=html_path,
        isVisible=True, showCloseButton=True, isResizable=True,
        width=420, height=720, useNewWebBrowser=True
    )
    palette = runtime.palette

    html_handler = PaletteHTMLEventHandler()
    palette.incomingFromHTML.add(html_handler)
    runtime.handlers.append(html_handler)

    close_handler = PaletteClosedHandler()
    palette.closed.add(close_handler)
    runtime.handlers.append(close_handler)

    try:
        palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
    except Exception as dock_err:
        aicad_log(f"create_palette dockingState ayarlanamadı (zararsız): {dock_err}")

    try:
        palette.isVisible = True
    except Exception:
        pass

    return palette


def show_palette():
    if not runtime.palette:
        create_palette()
    else:
        try:
            runtime.palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
        except Exception as dock_err:
            aicad_log(f"show_palette dockingState ayarlanamadı (zararsız): {dock_err}")
        try:
            runtime.palette.isVisible = True
        except Exception:
            create_palette()


def dispose_palette():
    """Paleti güvenle kapatır ve referansı temizler."""
    if runtime.palette:
        try:
            runtime.palette.deleteMe()
        except Exception:
            pass
        runtime.palette = None
