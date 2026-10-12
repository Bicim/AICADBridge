# AICADBridge Tanıtım Sitesi — Faz 2: Yaratıcı Yön Önerisi (Onay Kapısı)

> Kural (brief §14): **bu öneri onaylanmadan build'e geçilmez.**

## 1. Sayfa grameri (tek gramer) — `chaptered editorial`

**Seçim:** Bölümlü editoryal (pear.no ritmi). Gerekçe: ürün gerçekleri (Bölüm 3)
doğrusal, dürüst, "nasıl çalışır → demo → sınırlar → kurulum" hikâyesi; bölümler
kesintisiz tek dünya etkisi yerine okunabilir kısa bölümler ister.

**Grammar karıştırma yok — tek istisna:** demo perdesi (Act 2-5), *ayrı bir
gramer dayatmadan*, tam koyu zeminli tek bir "obje sayfası" olarak akar. Bu,
chaptered yapının içinde bir **zemin değiştiren bölüm**'dür (sayfa karanlık
nesneye geçişte sert kesim yapar) — live-surface davranışı gramer olarak değil,
o bölümün *malzemesi* olarak kullanılır.

## 2. Duygu eğrisi (feeling curve) — 8 perde, tek tepe

| Perde | Duygu | Ekranda ne yaratır |
|-------|-------|--------------------|
| 1. Hero | Merak, sakinlik | Tek cümle; imza hareket başlar (komut yazılmaya başlar) |
| 2. Komut → kod | "Bu kadar mı?" | Türkçe komut solda, Fusion API kodu sağda belirir (`--sc-p`) |
| 3. Model oluşur | Tatmin | Flanş (100mm + 4×M6) scroll ile adım adım şekillenir |
| **4. PEAK: Self-healing** | **Rahatlama** | Kod hata verir → sistem hatayı okur → kendini onarır; en büyük scroll alanı buraya ayrılır |
| 5. Sliders | Kontrol hissi | Parametre kaydırınca model ölçüsü değişir |
| 6. İki mod + sağlayıcılar | Esneklik | Palet ve tarayıcı yan yana; sağlayıcılar tipografik liste |
| 7. Açık not | Güven | Sınırlılıklar + "Kimler için değil" |
| 8. Kurulum + kapanış | Eyleme hazır | 4 adım, tek CTA (GitHub'a git) |

**Engineered peak = Perde 4.** Öncesi bilinçli sessiz, sonrası gevşeyen kapanış.
Sayfada tek tepe.

## 3. İmza hareket — "scroll = komut satırı"

Scroll çubuğu bir **komut satırı** gibi davranır: ziyaretçi indikçe Türkçe komut
harf harf yazılır; kod ve model aynı scroll değerinden (`--sc-p`) sürülür. Tepe
noktasında scroll'u geri çekince hata "geri sarılır" ve onarım yeniden oynar.
Başka hiçbir sitede yok, bespoke.

## 4. Tasarım kararı: zemin (brief §2.2 ile uyumlu)

- Sayfa zemini: **sıcak kırık beyaz, editoryal** (pear DNA'dan: typography,
  ritim, boşluk, ton).
- Ürün: sayfadaki **tek karanlık nesne** (gerçek arayüz ekran görüntüsü/kayıt).
- Neon aksan: **tek hex** `#00b8d4` (UI DNA'dan). Saf siyah yok; gri yerine tonlu
  ikincil metin; gradient metin yok.

## 5. Taste kadranları (brief §10)

- `DESIGN_VARIANCE: 7` · `MOTION_INTENSITY: 6` · `VISUAL_DENSITY: 3`
- Tipografi: **2 aile** — italik destekli editoryal serif (display/vurgu) + Inter
  (gövde). Kod: sistem monospace (bilinçli istisna).
- Gövde metni 45–75ch. `prefers-reduced-motion` için tam statik alternatif.

## 6. Metin iskeleti (brief §8'den, onaya hazır)

- Tagline TR: *"Söyle, Fusion çizsin."* / EN: *"Describe it. Fusion draws it."*
- Ana cümle: **"Fusion 360'a cümleyle konuş."** İtalik alt: *Model, kod değil niyetle başlasın.*
- "X değil, Y": *"Bir eklenti değil, Fusion'ın yanında oturan bir modelleme ortağı."*
- Bölümler: "Bir cümle yazarsın, *model gelir.*" · "Hata verir, *kendini düzeltir.*" · "Her şeyi yapmıyoruz, *bunları yapıyoruz.*"
- **Açık not:** Fusion 360 gerektirir · kendi API anahtarın gerekir (lokal Ollama istisna) · AI üretimi kod oturumda çalışır, önemli tasarımlarını çalıştırmadan önce kaydet · sürüm 1.0.0, hızla gelişiyor.
- **Kimler için değil:** Fusion 360 kullanmayanlar · tek tıkla "hatasız" model bekleyenler · API anahtarı veya lokal model kurmak istemeyenler.
- **SSS (5+):** Ücretli mi? Hangi AI'lar? Hangi OS? Verilerim nereye gidiyor? Tarayıcı modu nasıl çalışır? Hata verirse ne olur?
- Footer: "AICADBridge bağımsız bir projedir; Autodesk ile bağlantılı veya onaylanmış değildir."
- **Yasak:** em dash, 01/06 sayaçları, scroll ipucu okları, gradient metin, klişeler, uydurma sayılar.

## 7. Teknik & SEO

Statik HTML/CSS/JS (scroll-craft engine + doctor/workspace; engine dosyalarına dokunulmaz, tema = 6 renk token'ı + 2 font, özel her şey `--sc-p`). TR varsayılan + EN geçişi (`hreflang`, `lang`, dil seçici), canonical, OG + Twitter kartı, `sitemap.xml`, `robots.txt`, `SoftwareApplication` JSON-LD, LCP<2.5s hedefi, video lazy-load + poster.

## 8. Eksik asset'ler (brief §9 — kullanıcı sağlamalı)

Ajan bunları üretemez; yer tutucu **açıkça işaretlenir**, sahte arayüz çizilmez:

- [ ] **A:** Hero/komut→model kaydı (Fusion içinde silindir komutu, ~20 sn, 1080p)
- [ ] **B (PEAK):** Bilerek hata veren komut + self-healing döngüsü (~15 sn)
- [ ] **C:** Parametrik slider oynatma (~10 sn)
- [ ] **D:** Harici tarayıcı modu (`localhost:49876`) kaydı
- [ ] **Statik:** `index.html` arayüzünün temiz ekran görüntüsü (açık/koyu zemin)

> ⚠️ Bu videolar/ekran görüntüsü olmadan Hero/Demo/Peak perdesi **işaretli
> placeholder** ile yayına alınır.
