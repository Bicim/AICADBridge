"""AICADBridge — SolidWorks & Adam-CAD (CADAM) Bağımsız Köprü Sunucusu.

Bu betik Fusion 360 eklentisine ihtiyaç duymadan doğrudan Windows üzerinde çalışır,
`127.0.0.1:49876` portunda yerel HTTP köprüsünü başlatır ve COM API (`SldWorks.Application`)
üzerinden açık olan SolidWorks oturumuna bağlanır.

Kullanım:
    py solidworks_server.py
    py solidworks_server.py --no-browser
"""

import argparse
import os
import sys
import time
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aicad_bridge import adapters, runtime
from aicad_bridge.adapters import solidworks
from aicad_bridge.bridge import local_http
from aicad_bridge.runtime import LOCAL_HTTP_PORT


def main():
    parser = argparse.ArgumentParser(description="AICADBridge SolidWorks (Adam-CAD) Köprü Sunucusu")
    parser.add_argument('--port', type=int, default=LOCAL_HTTP_PORT, help='HTTP sunucu portu (varsayılan: 49876)')
    parser.add_argument('--no-browser', action='store_true', help='Tarayıcıyı otomatik açma')
    parser.add_argument('--launch-sw', action='store_true', help='SolidWorks kapalıysa otomatik başlatmayı dene')
    args = parser.parse_args()

    runtime.LOCAL_HTTP_PORT = args.port
    local_http.LOCAL_HTTP_PORT = args.port
    adapters.set_active_cad_target('solidworks')

    print("=" * 64)
    print("  AICADBridge — SolidWorks & Adam-CAD (CADAM) AI Copilot")
    print("=" * 64)

    sw_app = solidworks.get_sw_app(launch_if_needed=args.launch_sw)
    if sw_app:
        state = solidworks.inspect_current_design(sw_app)
        doc_info = state.get('doc_name', 'Yeni Parça Hazır') if state.get('has_design') else 'Açık parça yok (ilk komutta otomatik oluşturulur)'
        print(f"  [OK] SolidWorks COM bağlantısı aktif! ({doc_info})")
    else:
        print("  [!] SolidWorks şu an açık görünmüyor.")
        print("      SolidWorks'ü açtığınızda köprü otomatik olarak bağlanacaktır.")

    local_http.start_local_bridge_server()
    url = f"http://127.0.0.1:{args.port}/app?cad=solidworks"
    print(f"  [OK] Yerel Köprü Sunucusu: http://127.0.0.1:{args.port}")
    print(f"  [OK] AI CAD Studio Arayüzü: {url}")
    print("-" * 64)
    print("  Durdurmak için Ctrl+C tuşlarına basın.")
    print("=" * 64)

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[AICADBridge] Sunucu kapatılıyor...")
        local_http.stop_local_bridge_server()


if __name__ == '__main__':
    main()
