# 🤖 AICADBridge — AI-Powered CAD Studio for Autodesk Fusion 360

<p align="center">
  <strong>Doğal dil komutlarıyla Fusion 360'ta 3D modelleme yapın.</strong><br/>
  Design in 3D using natural language with Claude, GPT-4o, Gemini, DeepSeek or Ollama.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Fusion%20360-AddIn-orange?logo=autodesk" />
  <img src="https://img.shields.io/badge/Python-3.x-blue?logo=python" />
  <img src="https://img.shields.io/badge/AI-Claude%20%7C%20GPT--4o%20%7C%20Gemini%20%7C%20Ollama-purple" />
  <img src="https://img.shields.io/badge/Version-1.0.0-green" />
  <img src="https://img.shields.io/badge/OS-Windows%20%7C%20macOS-lightgrey" />
</p>

---

## 🎯 Projenin Amacı / Purpose

**Türkçe:** Kullanıcının doğal dilde verdiği 3D CAD modelleme komutlarını yapay zeka modelleri aracılığıyla Autodesk Fusion 360 Python API koduna dönüştürür ve anında çalıştırır.

**English:** Converts natural language 3D CAD modeling commands into Autodesk Fusion 360 Python API code via AI models and executes them instantly.

### ✨ Temel Özellikler / Key Features

- 🗣️ **Doğal Dil → 3D Model**: Türkçe veya İngilizce komutla anında CAD modeli
- 🔁 **Self-Healing CAD**: Hata durumunda otomatik hata yakalama ve onarma döngüsü
- 🎛️ **Parametric Sliders**: Canlı parametre kontrolü paneli
- 🌐 **Çift Mod Mimarisi**: Fusion 360 içi palet + harici tarayıcı desteği
- 🤖 **Çoklu AI Desteği**: Claude, GPT-4o, Gemini, DeepSeek, Ollama/LM Studio
- 🌑 **Dark Neon UI**: Modern karanlık temalı kullanıcı arayüzü

---

## 🏗️ Mimari / Architecture

AICADBridge hem Fusion 360'ın dahili web paletinde hem de harici bir Chrome/Edge tarayıcısında sorunsuz çalışır:

`
┌─────────────────────────────────────────────────────────┐
│                     index.html (UI)                     │
│              Dark Neon Chat & Parametric Panel          │
└───────────────┬─────────────────────┬───────────────────┘
                │                     │
      Dahili Palet               Harici Tarayıcı
  adsk.fusionSendData        HTTP POST localhost:49876
                │                     │
                └──────────┬──────────┘
                           │
              ┌────────────▼────────────┐
              │      AICADBridge.py     │
              │   (Fusion 360 AddIn)    │
              └────────┬────────┬───────┘
                       │        │
             Fusion 360 API    LLM Providers
             (CPython Runtime)  Claude / GPT-4o
                                Gemini / Ollama
`

### 1. Fusion 360 İçi Mod (Embedded Webview)
Fusion 360 paletinde dsk.core.HTMLEvent ve dsk.fusionSendData kullanılır.

### 2. Harici Tarayıcı Modu (Web Bridge)
Eklenti localhost:49876 üzerinde HTTP sunucusu açar. index.html dosyasını tarayıcınızdan açarak Fusion 360'ı uzaktan yönetebilirsiniz.

---

## 📁 Dosya Yapısı / File Structure

`
AICADBridge/
├── AICADBridge.py              # Ana eklenti dosyası (backend)
├── AICADBridge.manifest        # Fusion 360 eklenti tanımlayıcısı
├── index.html                  # Dark Neon kullanıcı arayüzü
├── .env.example                # Yapılandırma örneği (model ayarları, max_tokens)
├── config.py                   # Port ve genel yapılandırmalar
├── aicad_bridge/config.py      # .env okuyucu: planner/coder model + max_tokens ayarları
├── inspect_state.py            # Fusion 360 durum okuyucu
├── AddInIcon.svg               # Eklenti ikonu
├── docs/                       # Dokümantasyon (test komutları vb.)
├── commands/                   # Komut modülleri
├── lib/                        # Harici kütüphaneler
└── resources/                  # Ikon ve kaynak dosyaları
`

---

## 🚀 Kurulum / Installation

### Gereksinimler / Requirements

- Autodesk Fusion 360 (güncel sürüm)
- En az bir AI API anahtarı (Claude, OpenAI, Gemini) veya lokal Ollama

### Adımlar / Steps

1. **Repoyu klonlayın:**
   `ash
   git clone https://github.com/yunusayyldz/AICADBridge.git
   `

2. **Fusion 360 AddIns klasörüne taşıyın:**
   `
   Windows: %APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\
   macOS:   ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/
   `

3. **API anahtarlarınızı ve model ayarlarınızı yapılandırın:**

   Repodaki `.env.example` dosyasını `.env` olarak kopyalayın ve düzenleyin:

   ``
   cp .env.example .env
   ``

   Model adlarını koda gömmek yerine `.env` üzerinden yönetin. **Model adları sağlayıcıya göre sık değişir; kendi sağlayıcınızın güncel model adını sağlayıcının konsolundan kopyalayıp girin.** Örnek:

   `env
   # Üretim hattı (İki Aşamalı: Planner -> Coder) — boş bırakılırsa sohbet modeli kullanılır
   AICAD_PLANNER_PROVIDER=openai
   AICAD_PLANNER_MODEL=kendi_saglayicinin_guncel_model_adi
   AICAD_CODER_PROVIDER=anthropic
   AICAD_CODER_MODEL=kendi_saglayicinin_guncel_model_adi

   # Yanıt uzunluğu sınırları (varsayılanlar: 16384 / 4096)
   AICAD_MAX_TOKENS=16384
   AICAD_VISION_MAX_TOKENS=4096

   # API anahtarları (isteğe bağlı; UI kendi anahtarlarını tarayıcıda saklar)
   ANTHROPIC_API_KEY=your_claude_key
   OPENAI_API_KEY=your_openai_key
   GOOGLE_API_KEY=your_gemini_key
   ``

   Aynı ayarlar Fusion 360 içindeki **⚙️ Ayarlar → 🏭 Üretim Hattı (Planner & Coder)** bölümünden de yapılabilir (UI seçimi `.env` varsayılanını geçersiz kılar).

4. **Fusion 360'ta etkinleştirin:**
   Tools → Add-Ins → Scripts and Add-Ins → AICADBridge → Run

---

## 🎮 Örnek Komutlar / Example Commands

`
TR: "50mm çapında, 80mm yüksekliğinde, merkezinde 20mm delik bulunan bir silindir çiz"
EN: "Create a cylinder 50mm diameter, 80mm height with a 20mm hole in the center"

TR: "Flanş modeline 4 adet eşit aralıklı M6 cıvata deliği aç"
EN: "Add 4 equally spaced M6 bolt holes to the flange model"
`

> 🧪 Basitten karmaşığa **10 doğrulanmış test komutu** (beklenen sonuçlar, ölçü/delik/fillet kontrol noktaları ve regression notlarıyla): **[docs/test_prompts.md](docs/test_prompts.md)**

---

## 🤖 Desteklenen AI Modeller / Supported AI Models

Aşağıdaki sağlayıcılar desteklenir; **model adları koda gömülmez** — arayüzdeki "Modelleri Listele" ile sağlayıcınızdan güncel listeyi çekin veya model adını elle girin:

| Provider | Model Seçimi |
|----------|--------------|
| **Anthropic** | API'den çekilir (CORS engeli varsa: `.env` → `AICAD_ANTHROPIC_MODELS` ile liste tanımlayın veya adı elle girin) |
| **OpenAI** | API'den çekilir ("Modelleri Listele") |
| **Google** | API'den çekilir ("Modelleri Listele") |
| **Groq / OpenRouter / DeepSeek** | API'den çekilir ("Modelleri Listele") |
| **Ollama / LM Studio / llama.cpp** | Yerel sunucudan otomatik taranır |

> 💡 **Önemli:** Model adları sağlayıcılar tarafından sık değiştirilir. Liste gelmezse **kendi sağlayıcınızın güncel model adını** sağlayıcının konsolundan kopyalayıp arayüzdeki model alanına girin. Planner ve Coder aşamaları için ayrı model seçmek üzere `.env` içindeki `AICAD_PLANNER_MODEL` / `AICAD_CODER_MODEL` anahtarlarını veya Ayarlar → 🏭 Üretim Hattı bölümünü kullanın.

---

## 🔧 Self-Healing CAD

Kod çalışma hatası verdiğinde sistem otomatik olarak:
1. Hata mesajını yakalar
2. Fusion 360 tasarım durumunu okur
3. Hatayı AI modeline gönderir
4. Düzeltilmiş kodu alır ve yeniden çalıştırır

---

## 👤 Yazar / Author

**Yunus Ayyıldız** — [@yunusayyldz](https://github.com/yunusayyldz)

---

## 📄 Lisans / License

MIT License — Copyright (c) 2026 Yunus Ayyıldız

---

<p align="center">Made with ❤️ for the Fusion 360 community | Powered by AI</p>
