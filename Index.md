---
title: AICADBridge - Ana Dizin (MOC)
date: 2026-09-11
tags: [aicad, fusion360, cadam, moc, ana-dizin]
status: aktif
---

# 🚀 AICADBridge — Ana Dizin (Map of Content)

**AICADBridge**, Autodesk Fusion 360 için geliştirilen yapay zeka destekli CAD üretim, akıllı parametrik modelleme ve köprü mimarisidir.

---

## 🧭 Hızlı Gezinti

- 📌 [[Proje_Ozeti]]: Projenin genel mimarisi, teknik altyapısı ve dosya yapısı.
- 🔬 [[CADAM_Tersine_Muhendislik_Mimarisi]]: `Adam-CAD/CADAM` reposundan Clean-Room prensibiyle entegre edilen 5 temel özellik.
- 📝 [[Yapilan_Islemler_Gunlugu]]: 11 Eylül 2026 oturumunda tamamlanan tüm değişiklikler ve testler.
- 🎯 [[Gelecek_Oturum_Yol_Haritasi]]: Bir sonraki oturum için belirlenen öncelikli görevler ve hazırlıklar.

---

## 📊 Sistem ve Mimari Durumu

| Katman | Teknoloji / Yöntem | Durum |
|---|---|---|
| **Fusion 360 Add-In** | Python 3.x (`adsk.core`, `adsk.fusion`) | ✅ Aktif & Çalışıyor |
| **Webview Arayüzü** | Modern Vanilla HTML/CSS/JS (Dark Neon Theme) | ✅ Güncellendi (3650+ Satır) |
| **İletişim Köprüsü** | Çift Yönlü: `adsk.fusionSendData` + `HTTP:49876` | ✅ Kararlı |
| **Konuşma Geçmişi** | `localStorage` JSON tabanlı çoklu oturum | ✅ Entegre edildi |
| **Thinking Modu** | Claude Beta + Gemini Thinking Budget | ✅ Entegre edildi |
| **Model Grupları** | Güçlü / Ultra Hızlı / Yerel Kategorileri | ✅ Entegre edildi |
| **Parametrik Modelleme** | Dinamik Slider + Canlı Debounce Fusion Render | ✅ Entegre edildi |

---

## ⚡ Bir Sonraki Oturuma Başlarken

Bir sonraki oturumu açtığınızda doğrudan şu adımlarla başlayabilirsiniz:
1. [[Gelecek_Oturum_Yol_Haritasi]] dosyasındaki yapılacaklar listesini gözden geçirin.
2. Fusion 360 içinde eklentiyi yeniden başlatmak için: **Scripts and Add-Ins** (`Shift+S`) -> **AICADBridge** -> **Restart**.
3. Tarayıcıda test etmek için: `file:///C:/Users/Yunus/AppData/Roaming/Autodesk/Autodesk%20Fusion%20360/API/AddIns/AICADBridge/index.html` adresini açın.
