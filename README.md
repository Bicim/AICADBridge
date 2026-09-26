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
├── config.py                   # Port ve genel yapılandırmalar
├── inspect_state.py            # Fusion 360 durum okuyucu
├── AddInIcon.svg               # Eklenti ikonu
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

3. **API anahtarlarınızı yapılandırın** (.env dosyasını düzenleyin):
   `env
   ANTHROPIC_API_KEY=your_claude_key
   OPENAI_API_KEY=your_openai_key
   GOOGLE_API_KEY=your_gemini_key
   `

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

---

## 🤖 Desteklenen AI Modeller / Supported AI Models

| Provider | Modeller |
|----------|---------|
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus |
| **OpenAI** | GPT-4o, GPT-4 Turbo |
| **Google** | Gemini 1.5 Pro, Gemini 2.0 Flash |
| **DeepSeek** | DeepSeek Coder V2 |
| **Ollama** | Llama 3, CodeLlama, Mistral (lokal) |

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
