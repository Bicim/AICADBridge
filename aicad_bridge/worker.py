"""Arka plan CAD üretim görevi: LLM çağrısı + Self-Healing döngüsü (Fusion 360 & SolidWorks)."""

import re
import traceback

from aicad_bridge import adapters, events, messaging
from aicad_bridge.llm.client import call_llm_api
from aicad_bridge.llm.prompt import extract_python_code, get_system_prompt
from aicad_bridge.llm.registry import PROVIDERS
from aicad_bridge.runtime import aicad_log


def generate_cad_worker(data):
    """Arka plan thread'inde LLM çağrısı ve Self-Healing CAD döngüsünü yürütür."""
    provider = data.get('provider', 'ollama')
    model = data.get('model', '')
    prompt = data.get('prompt', '')
    api_key = data.get('apiKey', '')
    base_url = data.get('baseUrl') or data.get('base_url')
    timeout = data.get('timeout', 90)
    cad_target = adapters.get_active_cad_target(data.get('cad_target'))
    cad_label = 'SolidWorks' if cad_target == 'solidworks' else 'Fusion 360'
    sys_prompt = get_system_prompt(cad_target)

    if provider == 'local':
        timeout = max(timeout, 150)
    aicad_log(f"generate_cad_worker başladı: cad={cad_target}, provider={provider}, model={model}, prompt='{prompt}'")

    messages = [
        {'role': 'system', 'content': sys_prompt},
        {'role': 'user', 'content': prompt}
    ]

    # Mevcut CAD tasarımını kontrol et ve varsa bağlama ekle
    try:
        current_design = events.get_design_state_on_main_thread(cad_target=cad_target)
        if current_design and current_design.get('has_design') and current_design.get('bodies_count', 0) > 0:
            if '[MEVCUT' not in prompt:
                design_summary = current_design.get('summary_text', '')
                if cad_target == 'solidworks':
                    design_addon = (
                        f"\n\n[MEVCUT SOLIDWORKS TASARIM DURUMU]:\n{design_summary}\n"
                        f"(Lütfen yeni parçayı mevcut katı gövdelere uygun koordinatlarda konumlandır "
                        f"ve `sw` yardımcı fonksiyonlarını milimetre cinsinden kullan.)"
                    )
                else:
                    design_addon = (
                        f"\n\n[MEVCUT FUSION 360 TASARIM DURUMU]:\n{design_summary}\n"
                        f"(Lütfen yeni parçayı bu mevcut katı gövdelere uygun koordinatlarda konumlandır "
                        f"ve kesinlikle FeatureOperations.NewBodyFeatureOperation kullan.)"
                    )
                if re.search(r'devam|sonraki|sıradak|ilerle|kaldığın|tamam|ekle|yap|bitir|çiz|oluştur|model nerede|görünmüyor', prompt, re.I):
                    design_addon += (
                        f"\n\n[KESİNTİSİZ ADIM ADIM MODELLEME TALİMATI]:\n"
                        f"Kullanıcı tasarıma devam etmeni ve {cad_label} ekranında somut 3D parçayı hemen oluşturmanı istiyor! "
                        f"KESİNLİKLE soru sorma, doğrudan {cad_label} Python kodunu ```python ... ``` bloğu içinde üret!"
                    )
                messages[1]['content'] += design_addon
                aicad_log(f"generate_cad_worker: Tasarım durumu LLM bağlamına eklendi ({current_design.get('bodies_count')} gövde).")
    except Exception as d_err:
        aicad_log(f"generate_cad_worker tasarım durumu ekleme hatası: {d_err}")

    prov_name = PROVIDERS.get(provider, {}).get('name', provider)

    # 1. Deneme: Kod Üretimi
    messaging.send_palette_message('statusUpdate', {
        'status': 'loading',
        'message': f'{prov_name} · {model} ile oluşturuluyor...'
    })

    try:
        raw_reply = call_llm_api(provider, model, messages, api_key, timeout=timeout, base_url=base_url)
        aicad_log(f"LLM yanıtı alındı (uzunluk: {len(raw_reply)})")
    except Exception as e:
        aicad_log(f"generate_cad_worker LLM çağrı hatası: {e}")
        messaging.send_palette_message('taskResult', {
            'status': 'error',
            'message': str(e),
            'error': traceback.format_exc(),
        })
        return

    code = extract_python_code(raw_reply)
    if not code:
        aicad_log("Modelden doğrudan Python kodu gelmedi, sohbet/rehberlik yanıtı olarak iletiliyor.")
        messaging.send_palette_message('taskResult', {
            'status': 'chat',
            'message': raw_reply,
        })
        return

    # 1. Deneme: CAD Ortamında Çalıştırma
    messaging.send_palette_message('statusUpdate', {
        'status': 'loading',
        'message': f'{cad_label} içinde yürütülüyor...',
    })

    exec_res = events.run_code_on_main_thread(code, cad_target=cad_target)

    if exec_res['success']:
        new_b = exec_res.get('new_bodies', [])
        b_info = f" ({', '.join(new_b)} eklendi)" if new_b else ""
        messaging.send_palette_message('taskResult', {
            'status': 'success',
            'message': f'CAD Modeli {cad_label} içinde başarıyla oluşturuldu!{b_info}',
        })
        return

    # Multi-Attempt Self-Healing Loop: Hata Alındığında pes etmeden onarmaya devam et (3 Denemeye kadar)
    current_code = code
    current_exec_res = exec_res
    healing_attempts = 0
    max_healing_attempts = 3

    while not current_exec_res.get('success') and healing_attempts < max_healing_attempts:
        healing_attempts += 1
        err_msg = current_exec_res.get('error', 'Bilinmeyen hata')
        err_tb = current_exec_res.get('traceback', '')
        aicad_log(f"{healing_attempts}. Onarım Denemesi başlatılıyor: {err_msg}")

        messaging.send_palette_message('statusUpdate', {
            'status': 'healing',
            'message': f'Hata tespit edildi, onarılıyor... (Deneme {healing_attempts}/{max_healing_attempts})',
        })

        specific_tip = ""
        if cad_target == 'solidworks':
            if 'adsk' in err_msg:
                specific_tip = "ÖNEMLİ İPUCU: Bu ortam SolidWorks'tür! Kesinlikle `import adsk` kullanma; hazır enjekte edilen `sw` yardımcısını (`sw.extrude_cylinder`, `sw.extrude_box`, `sw.cut_hole`, vb.) kullan.\n"
            elif 'HİÇBİR YENİ 3D KATI GÖVDE' in err_msg:
                specific_tip = "ÖNEMLİ İPUCU: 3D katı gövde oluşturulmadı! `sw.extrude_cylinder(...)`, `sw.extrude_box(...)` veya `featMgr.FeatureExtrusion2(...)` çağrısı yap.\n"
        else:
            if 'HİÇBİR YENİ 3D KATI GÖVDE EKLENMEDİ' in err_msg or 'No bodies added' in err_msg:
                specific_tip = "ÖNEMLİ İPUCU: Çizim sadece 2D eskiz olarak kaldı! Mutlaka kapalı profili extrudes.add(extInput) ve NewBodyFeatureOperation ile 3D katı gövdeye dönüştür.\n"
            elif 'Kesilecek veya kesişecek hedef gövde bulunamadı' in err_msg:
                specific_tip = "ÖNEMLİ İPUCU: CutFeatureOperation veya JoinFeatureOperation boşlukta hata verir! Kesinlikle 'adsk.fusion.FeatureOperations.NewBodyFeatureOperation' kullan.\n"
            elif 'profiles.item' in err_msg:
                specific_tip = "ÖNEMLİ İPUCU: Eskiz profili kapalı değil veya bulunamadı! Çizgilerin uç uca tam kapandığından emin ol ya da sketch.profiles.count kontrolü yap.\n"

        healing_prompt = (
            f"{cad_label} API şu hatayı verdi ({healing_attempts}. deneme):\n{err_msg}\n\n"
            f"Detaylı Traceback:\n{err_tb}\n\n"
            f"{specific_tip}"
            f"Lütfen çizimi, düzlemi veya parametreleri düzelterek kodu yeniden ver. "
            f"Sadece ```python ... ``` bloğu içinde saf ve hatasız {cad_label} Python kodu döndür."
        )

        messages_attempt = [
            {'role': 'system', 'content': sys_prompt},
            {'role': 'user', 'content': prompt},
            {'role': 'assistant', 'content': f"```python\n{current_code}\n```"},
            {'role': 'user', 'content': healing_prompt}
        ]

        try:
            raw_reply_h = call_llm_api(provider, model, messages_attempt, api_key, timeout=timeout, base_url=base_url)
            code_h = extract_python_code(raw_reply_h)
        except Exception as e:
            aicad_log(f"Self-Healing LLM hatası: {e}")
            break

        if not code_h:
            aicad_log(f"Self-Healing: Model geçerli kod üretemedi (Deneme {healing_attempts})")
            break

        current_code = code_h

        messaging.send_palette_message('statusUpdate', {
            'status': 'loading',
            'message': f'Düzeltilen kod yürütülüyor ({healing_attempts}/{max_healing_attempts})...',
        })

        current_exec_res = events.run_code_on_main_thread(current_code, cad_target=cad_target)
        if current_exec_res.get('success'):
            break

    if current_exec_res.get('success'):
        new_b = current_exec_res.get('new_bodies', [])
        b_info = f" ({', '.join(new_b)} eklendi)" if new_b else ""
        messaging.send_palette_message('taskResult', {
            'status': 'success',
            'message': f'CAD Modeli onarılarak başarıyla oluşturuldu!{b_info}',
        })
    else:
        messaging.send_palette_message('taskResult', {
            'status': 'error',
            'message': f"Onarım tamamlanamadı: {current_exec_res.get('error', 'Bilinmeyen hata')}",
        })
