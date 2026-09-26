---
title: Gelecek Oturum Yol Haritası ve Hazırlıklar
date: 2026-09-11
tags: [yol-haritasi, gelecek-oturum, todo, backlog, hazirlik]
status: beklemede
---

# 🎯 Gelecek Oturum Yol Haritası ve Hazırlıklar

Bu doküman, bir sonraki çalışma oturumunda AICADBridge projesine eklenebilecek geliştirmeleri, öncelikli görevleri ve hazırlıkları içerir.

---

## 🚀 Bir Sonraki Oturumda Yapılacak Öncelikli Görevler

### 1. 💾 Parametrik Tasarım Önayarları (Presets)
- **Açıklama:** Kullanıcının oluşturduğu parametrik modelleri ve ayarlanmış slider değerlerini yerel bir "Preset" olarak kaydetmesi (`localStorage` veya `.json` dosyası).
- **Kullanım Senaryosu:** "Özelleştirilmiş Flanş", "M8 Somun Yuvası", "Dişli Kutusu" gibi tasarımların tek tıkla geri çağrılabilmesi.

### 2. 📤 Konuşma Geçmişini JSON Olarak İçe / Dışa Aktarma
- **Açıklama:** Sidebar'daki konuşma geçmişine **"JSON Olarak İndir"** ve **"JSON Yükle"** butonları eklemek.
- **Kullanım Senaryosu:** Başka bir bilgisayara geçerken veya yedek alırken oturumların taşınabilmesi.

### 3. 📐 Fusion 360 Canlı Bounding Box & Ölçüm Analizi (`getDesignState`)
- **Açıklama:** Fusion 360 içindeki mevcut gövdelerin (bodies) x/y/z ölçülerini ve hacimlerini otomatik okuyup AI prompt'una context (bağlam) olarak ekleme yeteneğini genişletmek.
- **Kullanım Senaryosu:** AI'ın "Mevcut kutunun üzerine 5mm kalınlığında kapak ekle" dendiğinde mevcut kutunun ölçülerini otomatik bilmesi.

### 4. 🔄 Parametrik Modda Otomatik Hata Onarma (Self-Healing)
- **Açıklama:** Slider değeri aşırı uç bir değere çekildiğinde (örn: delik çapı gövde çapından büyük olduğunda) Fusion 360'tan dönen geometrik hata mesajını yakalayıp kullanıcıya arayüzde görsel uyarı vermek.

### 5. 📦 3D Model Tek Tıkla Dışa Aktarma (Export STEP / STL / 3MF)
- **Açıklama:** Arayüze "3D Yazıcı için STL İndir" veya "Üretim için STEP Al" butonu eklemek; Python köprüsü üzerinden Fusion 360 export yöneticisini tetiklemek.

---

## 📋 Hızlı Kontrol Listesi (Checklist)

- [ ] Preset kaydet / yükle UI ve JS mantığı
- [ ] Export / Import JSON düğmeleri (Sidebar)
- [ ] Parametrik modda hata yakalama arayüzü
- [ ] STEP/STL ihracat komutu entegrasyonu
- [ ] Canlı bounding box okuyucunun arayüz durum rozetine bağlanması

---

## 💡 Sonraki Oturuma Başlarken Verilebilecek Hızlı Komutlar

- *"Gelecek_Oturum_Yol_Haritasi dosyasındaki 1. ve 2. maddeleri (Preset ve Export/Import) uygulayalım."*
- *"Parametrik mod için hata yakalama ve geri bildirim sistemini kuralım."*
- *"Fusion 360 tasarım durumunu (bounding box) arayüzde gösterelim."*
