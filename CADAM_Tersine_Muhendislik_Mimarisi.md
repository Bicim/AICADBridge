---
title: CADAM Tersine Mühendislik Mimarisi
date: 2026-09-11
tags: [cadam, reverse-engineering, clean-room, fusion360, parametric, thinking]
status: tamamlandi
---

# 🔬 CADAM Tersine Mühendislik Mimarisi

Bu doküman, [Adam-CAD/CADAM](https://github.com/Adam-CAD/CADAM) açık kaynak projesinin **Temiz Oda Tersine Mühendisliği (Clean-Room Reverse Engineering)** analizini ve AICADBridge projesine uyarlanan özgün çözümleri belgeler.

---

## 🛡️ Temiz Oda (Clean-Room) Prensibi

Tersine mühendislik sürecinde hiçbir kaynak kod kopyalanmamıştır:
1. **Analiz Aşaması:** CADAM'ın kullanıcı deneyimi, veri akışı ve mimari bileşenleri incelendi.
2. **Özellik Çıkarımı:** En değerli 5 mimari fikir belirlendi.
3. **Sıfırdan Tasarım & Geliştirme:** Bu fikirler, Fusion 360'ın Python API'sine ve AICADBridge'in bağımsız webview mimarisine uygun olarak sıfırdan kodlandı.

---

## 🧩 Entegre Edilen 5 Temel Özellik

### 1. Konuşma Geçmişi & Çoklu Oturum (Conversation History)
- **CADAM Referansı:** Supabase PostgreSQL veritabanı + mesaj ağacı yapısı.
- **AICADBridge Çözümü:** İstemci tarafında sıfır bağımlılıkla çalışan `localStorage` JSON veritabanı (`aicad_conversations`).
- **Özellikler:**
  - Sol sidebar ikonuna tıklandığında genişleyen geçmiş listesi.
  - İlk mesajın ilk 42 karakterinden otomatik türetilen oturum başlığı.
  - Her asistan cevabında otomatik kaydetme (`saveCurrentConversation`).
  - Geçmiş konuşmaya tek tıkla dönme ve mesajları geri yükleme.
  - Güvenli silme (✕ düğmesi).

### 2. Derin Düşünce Modu (Thinking Mode - 🧠)
- **CADAM Referansı:** API çağrılarında `budgetTokens: 9000` parametresi ile reasoning açma.
- **AICADBridge Çözümü:**
  - **Claude:** `anthropic-beta: interleaved-thinking-2025-05-14`, `budget_tokens: 10000`, `max_tokens: 16000`.
  - **Gemini:** `thinkingConfig: { thinkingBudget: 8192 }`, `temperature: 1`.
  - Desteklemeyen modeller için HTTP 400 durumunda otomatik fallback ile normal moda geçiş.
  - Hem üst çubukta hızlı buton hem de ayarlar modalında detaylı toggle anahtarı.

### 3. Model Kategorileri & Akıllı Sağlayıcı Rozetleri
- **CADAM Referansı:** Modellerin kabiliyetlerine göre gruplanması.
- **AICADBridge Çözümü:**
  - `🧠 Güçlü Akıl Yürütme Modelleri`: Anthropic (`THINKING`), OpenAI (`FLAGSHIP`), Gemini (`THINKING`), DeepSeek (`REASONING`).
  - `⚡ Ultra Hızlı & API Sağlayıcıları`: Groq (`ULTRA HIZLI`), OpenRouter (`MULTİ-HUB`).
  - `🖥️ Yerel & Ücretsiz (Gizlilik Odaklı)`: Ollama (`YEREL`), Yerel Model (`OFFLINE`).
  - Dinamik grup ayırıcı başlıklar ve renkli CSS etiketleri.

### 4. Görünüm Sekmeleri (View Tabs)
- **CADAM Referansı:** React Router ve bileşen görünüm sekmeleri.
- **AICADBridge Çözümü:**
  - CSS display switch mekanizması ile `#viewChat` ve `#viewParam` arasında sıfır gecikmeli geçiş.

### 5. Parametrik Modelleme Modu (Live Parametric Sliders)
- **CADAM Referansı:** OpenSCAD tabanlı değişkenli kod üretimi.
- **AICADBridge Çözümü:**
  - Özel prompt şablonu (`PARAM_SYSTEM_PROMPT`): AI'dan `__PARAM_NAME__` placeholder'lı Fusion 360 Python kodu ve parametre metadata JSON'ı istenir.
  - Gelen metadata doğrultusunda dinamik range slider arayüzü çizilir.
  - Slider değeri değiştiğinde **400ms debounce** ile Fusion 360'a anlık Python kodu gönderilir.
  - Kullanıcı slider'ı kaydırdığı anda 3D model canlı olarak Fusion 360 ekranında güncellenir!

---

## 📊 Mimari Karşılaştırma Matrisi

| Konsept | CADAM | AICADBridge |
|---|---|---|
| **Hedef Platform** | Web / CAD Kernel Bağımsız | Autodesk Fusion 360 CPython API |
| **Durum Saklama** | Bulut Veritabanı | Yerel `localStorage` + Otomatik Senkronizasyon |
| **Kod Çalıştırma** | Uzak Sunucu / Sandbox | Doğrudan Kullanıcının Yerel Fusion 360 Oturumu |
| **Gecikme** | Ağ gecikmesine bağlı | Yerel soket/bridge ile anlık (<50ms) |
