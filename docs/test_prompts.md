# 🧪 Test Komutları — Basitten Karmaşığa

Bu dosya, AICADBridge'in **iki aşamalı üretim hattını** (Planner → Coder → Doğrulama),
**basit komut kuralını**, **self-healing** ve **vision kontrolünü** uçtan uca test etmek
için hazırlanmış 10 komut içerir. Komutlar Türkçe ve İngilizce karışıktır; her biri için
beklenen sonuç ve somut kontrol noktaları listelenmiştir.

## Doğrulama Araçları

Her komuttan sonra şu kaynaklarla kontrol yapın:

| Araç | Nerede | Ne Kontrol Edilir |
|------|--------|-------------------|
| 📋 Plan adım listesi | Sohbet balonu | Planlanan feature sayısı, türleri, sırası |
| 🔍 Doğrulama satırları | Sohbet balonu (tur sonuçları) | Gövde/yüz/kenar/silindirik yüz/hacim değişimi, planla uyum |
| 👁️ Görsel kontrol satırı | Sohbet balonu | Vision destekli sağlayıcıda modelin komuta uyumu |
| 🔧🔧 Onarım satırları | Adım notları | Self-healing turları (hata durumunda) |
| [+ Teknik Kod] | Sohbet balonu | Gerçek API çağrıları: `holeFeatures`, `filletFeatures`, `chamferFeatures`, `userParameters` |
| Gövde/ölçü incelemesi | Fusion 360 çalışma alanı | Gövde sayısı, bounding-box ölçüleri (mm), hacim (cm³) |

> **Not:** 1–2 arası komutlar **basit komut kuralını** (planner'ın atlanması) test eder;
> balonda "⚡ Basit komut algılandı" satırı görünmelidir. Diğerleri Planner üzerinden
> çok adımlı plan üretir.

---

## 1. Basit Silindir (TR) — Hızlı Yol

**Komut:**
```
çapı 40 mm yüksekliği 60 mm olan bir silindir yap
```

**Beklenen sonuç:**
- Basit komut kuralı tetiklenir, planner LLM çağrısı **atlanır** ("⚡ Basit komut" notu)
- Tek adımlı plan: `govde` (extrude, circle)
- 1 adet yeni katı gövde

**Kontrol noktaları:**
- [ ] Plan tam olarak 1 adım ve `extrude` türünde
- [ ] Gövde sayısı +1
- [ ] Ölçüler: çap **40 mm**, yükseklik **60 mm** (bounding-box: X=40, Y=40, Z=60)
- [ ] Hacim ≈ **75,4 cm³** (π·2²·6)
- [ ] Doğrulama satırı: "planla uyumlu ✅"

---

## 2. Simple Block (EN) — Hızlı Yol, İngilizce

**Komut:**
```
Create a 50 x 30 x 10 mm rectangular block
```

**Beklenen sonuç:**
- Basit komut kuralı (İngilizce metinle de çalışmalı), tek adımlı plan
- 1 adet kutu gövdesi

**Kontrol noktaları:**
- [ ] Plan 1 adım: `extrude` (rect)
- [ ] Ölçüler: X=**50**, Y=**30**, Z=**10 mm**
- [ ] 6 yüz, 12 kenar
- [ ] Hacim = **15 cm³** tam (tolerans ±%1)

---

## 3. Delikli Silindir (TR) — Planner + Delik Doğrulaması

**Komut:**
```
50mm çapında, 80mm yüksekliğinde, merkezinde 20mm delik bulunan bir silindir
```

**Beklenen sonuç:**
- Planner 2 feature üretir: `extrude` (silindir) + `hole` (count=1)
- Halka (boru) kesitli tek gövde

**Kontrol noktaları:**
- [ ] Plan 2 adım ve sıralama: önce gövde, sonra delik
- [ ] Dış çap **50 mm**, iç delik çapı **20 mm**, yükseklik **80 mm**
- [ ] Delik doğrulaması: doğrulama satırında **silindirik yüz 0→1** (veya daha fazla) artışı
- [ ] Hacim ≈ **131,9 cm³** (π·(2,5²−1²)·8)
- [ ] Teknik kodda tercihen gerçek `holeFeatures` (cut-extrude değil) — SYSTEM_PROMPT kuralı

---

## 4. Flanş + 4 Cıvata Deliği (TR) — Çok Adım + Delik Sayısı

**Komut:**
```
100mm çapında 10mm kalınlığında bir flanş yap ve çevresine 4 adet 8mm cıvata deliği aç
```

**Beklenen sonuç:**
- Planner 2–3 feature: `extrude` (disk) + `hole` (count=4) — veya extrude + pattern + hole
- Delikler eşit açıyla (90°) dağıtılmış

**Kontrol noktaları:**
- [ ] Flanş çapı **100 mm**, kalınlık **10 mm**
- [ ] **Delik sayısı = 4** (en kritik kontrol; doğrulama: "Planda 4 delik istendi" satırı UYUŞMAZLIĞA düşmemeli → silindirik yüz artışı ≥4)
- [ ] Delik çapı **8 mm**
- [ ] Delikler merkezden eşit uzaklıkta (bolt-circle), yaklaşık 90° aralıklı
- [ ] Hacim ≈ **76,5 cm³** (disk 78,5 − 4 delik ≈ 2,0)
- [ ] Ölçüler user parameter olarak tanımlanmış mı ([+ Teknik Kod] içinde `userParameters.add`)

---

## 5. Kutu + Kapak (EN) — Shell + Çok Gövde Montaj

**Komut:**
```
Make a box 80x60x40 mm with 2mm wall thickness and a separate lid 80x60x5 mm on top
```

**Beklenen sonuç:**
- 2+ feature: `extrude` (dış kutu) + `shell` (içi oy, wall=2) + `extrude` (kapak)
- 2 ayrı gövde: açık kutu + üstünde kapak

**Kontrol noktaları:**
- [ ] **Gövde sayısı = 2**
- [ ] Kutu dış ölçüleri: **80×60×40 mm**; kapak: **80×60×5 mm**
- [ ] Kapak kutunun ÜSTÜNDE (Z aralıkları çakışmıyor, bitişik)
- [ ] Kabuk cidar kalınlığı ≈ **2 mm** (iç boşluk ölçülebilir: ~76×56×~35 mm)
- [ ] Kapak gövdesi kabuğa `NewBodyFeatureOperation` ile eklenmiş (birleşmemiş)

---

## 6. Kenar Yuvarlamalı Braket (TR) — Gerçek Fillet

**Komut:**
```
60x40 mm L şeklinde braket yap, her kol 20mm genişliğinde, 5mm kalınlığında, tüm keskin kenarları 2mm yuvarlat
```

**Beklenen sonuç:**
- 2 feature: `extrude` (L profili) + `fillet` (radius=2)
- Tek gövde, yumuşatılmış kenarlı L formu

**Kontrol noktaları:**
- [ ] **Fillet var mı:** [+ Teknik Kod] içinde `filletFeatures` çağrısı (manuel yaklaşık profil değil)
- [ ] Radyüs = **2 mm**
- [ ] L formu: 60×40 mm genel ölçü, kol genişliği 20 mm, kalınlık **5 mm**
- [ ] Hacim ≈ **8 cm³**'ten biraz az (L alanı 1600 mm² × 5 mm, fillet düşüşüyle)
- [ ] Plan sırası: extrude önce, fillet sonra (mantıklı feature sırası kuralı)

---

## 7. Pah + Delik Birlikte (EN) — Chamfer + Hole Kombinasyonu

**Komut:**
```
Create a 40x40x20 block, chamfer all top edges by 3mm and drill a 10mm hole through the center
```

**Beklenen sonuç:**
- 3 feature sırayla: `extrude` → `chamfer` (3mm) → `hole` (10mm)

**Kontrol noktaları:**
- [ ] **Pah var mı:** `chamferFeatures` çağrısı, mesafe **3 mm**, üst kenarlarda
- [ ] Delik çapı **10 mm**, merkezden baştan sona (iç silindirik yüz = 1)
- [ ] Blok ölçüleri: **40×40×20 mm** (pah üst kenarları kısaltır, taban ölçüsü korunur)
- [ ] Plan sırası: gövde → pah → delik
- [ ] Hacim ≈ 25–26 cm³ (32 − delik 6,3 − pahlar ~0,5)

---

## 8. Dişli Benzeri Desen (TR) — Circular Pattern

**Komut:**
```
40mm çapında 10mm kalınlığında bir disk oluştur ve çevresine 12 adet 5mm çapında 10mm yüksekliğinde pin ekle
```

**Beklenen sonuç:**
- 2–3 feature: `extrude` (disk) + `extrude`/`construction` (pin) + `pattern` (kind=circular, count=12)
- Disk çevresinde 12 eşit aralıklı pin (dişli/çark görünümü)

**Kontrol noktaları:**
- [ ] **Desen sayısı = 12** (pattern feature kullanılmış; her pin için ayrı extrude YAPILMAMIŞ olmalı)
- [ ] Pin çapı **5 mm**, yükseklik **10 mm** (diskten taşan kısım)
- [ ] Pinler diskin çevresine eşit açıyla (30°) yerleşmiş, merkezden eşit uzaklıkta
- [ ] Toplam gövde sayısı: tek gövde (pinler diskte birleşik) veya 12+1 — her ikisi de kabul
- [ ] Doğrulama uyuşmazlığı yok (pattern count beklentisi)

---

## 9. Eğri Boru (EN) — Sweep

**Komut:**
```
Create a pipe with 10mm outer diameter following an L-shaped path with 100mm legs, place it flat on the ground plane
```

**Beklenen sonuç:**
- 1–2 feature: `sweep` (kesit çemberi + yol) — mümkünse tek seferde

**Kontrol noktaları:**
- [ ] **Sweep kullanılmış:** `sweepFeatures` + `Path.create` çağrıları (ard arda extrude değil)
- [ ] Boru dış çapı **10 mm** (silindirik yüz ölçülebilir)
- [ ] Yol L şeklinde: her kol **100 mm** (uçtan uca toplam yayılım ~200 mm)
- [ ] Köşe bölgesi kesintisiz/köpüksüz (gövde tek parça)
- [ ] Zemin düzlemine oturmuş (borunun alt tanjantı Z=0)

---

## 10. 4 Ayaklı Masa (TR) — En Karmaşık Montaj

**Komut:**
```
60x60 mm, 5mm kalınlığında tablası olan 50mm yüksekliğinde 4 ayaklı bir masa yap, ayaklar 10mm çapında silindir olsun
```

**Beklenen sonuç:**
- 2–3 feature: `extrude` (tabla) + `extrude`/`pattern` (ayak ×4)
- 5 gövdeli montaj: 1 tabla + 4 silindirik ayak

**Kontrol noktaları:**
- [ ] **Toplam gövde sayısı = 5**
- [ ] Tabla: **60×60×5 mm**, üstte
- [ ] Ayaklar: **10 mm çap**, toplam yükseklik **50 mm**, 4 köşede simetrik yerleşim
- [ ] Ayaklar tablaya değiyor/bitişik (Z aralıkları çakışıyor), boşlukta uçmuyor
- [ ] Ayaklar `NewBodyFeatureOperation` ile eklenmiş (tablayı kesmiyor)
- [ ] Vision kontrolü (açıkça): "model komuta uyuyor ✅" — 4 ayak görünürlüğü
- [ ] Kod, ayaklar için pattern veya döngü kullanmış; ölçüler user parameter'lı

---

## Genel Regression Notları

- **Fallback kontrolü:** Planner JSON bozuk üretilirse (bilerek bozmak için çok kısa/şifreli komut), bir yeniden istek sonrası eski tek-atış akışına düşülmeli ve model yine üretilmeli.
- **Self-healing kontrolü:** Hata alındığında (ör. "Kesilecek hedef gövde bulunamadı") adım notunda 🔧 onarım satırı ve en fazla 3 deneme görünmeli.
- **Doğrulama turları:** Uyuşmazlık varsa en fazla **2 düzeltme turu** çalışmalı; her turun sonucu kısa durum satırı olarak görünmeli.
- **Model ayrımı:** Ayarlar → 🏭 Üretim Hattı'nda planner/coder için farklı model seçilirse balonda "🤖 Modeller — Planner: X · Coder: Y" satırı görünmeli.
