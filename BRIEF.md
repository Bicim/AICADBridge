# AICADBridge Resmi Web Sitesi: Build Brief

Bu dosya bir kodlama ajanına (Claude Code, Cursor, Codex) verilir. Amaç: AICADBridge için canlıya alınacak resmi tanıtım sitesini, aşağıdaki referansları **analiz ederek ve araç olarak kullanarak** üretmek.

## Nasıl kullanılır

1. Bu dosyayı projenin köküne `BRIEF.md` olarak koy.
2. Bölüm 5'teki kurulum komutlarını çalıştır.
3. Ajana en alttaki "Başlangıç Promptu"nu ver.

---

## 1. Rol ve hedef

Sen kıdemli bir creative developer ve art directorsun. **AICADBridge** için tek sayfalık, scroll odaklı, premium hissettiren resmi bir ürün sitesi yapacaksın.

Sitenin tek işi: ziyaretçiye ürünü 10 saniyede anlatmak, bir şey yapabildiğini kanıtlamak ve GitHub'a / kuruluma yönlendirmek.

Site dili: **Türkçe varsayılan, İngilizce geçişli** (README zaten iki dilli). `hreflang`, `lang` ve dil seçici dahil.

---

## 2. Referanslar ve her birinden ne alınacak

| # | Referans | Ne için kullanılacak | Ne alınmayacak |
|---|----------|----------------------|----------------|
| 0 | https://github.com/yunusayyldz/AICADBridge | **Tek gerçek kaynak.** Ürün bilgisi, kurulum, mimari, özellikler. Ayrıca `index.html` içindeki gerçek arayüz renkleri ve hissi. | Repo'da olmayan hiçbir özelliği iddia etme. |
| 1 | https://pear.no/ | **Ses, dil ve sayfa mantığı.** Aşağıda detay. | Metinlerini, videolarını (`/films/*.mp4`), neoklasik pear görselini ve OG görselini kopyalama. Yapı ve ton ödünç alınır, içerik alınmaz. |
| 2 | https://github.com/zanwei/design-dna | **Tasarım DNA'sını çıkarmak** (Analyze) ve ondan üretmek (Generate). | Referansı birebir klonlamak. DNA, ilham ve ölçü içindir. |
| 3 | https://github.com/nateherkai/scroll-craft | **Scroll hareketi motoru, sayfa grameri, imza hareket, kendi kendini doğrulama.** | Engine dosyalarını (`scrollcraft.js/.css`) proje başına düzenleme. Skill'in kendi kuralı bu. |
| 4 | https://github.com/Leonxlnx/taste-skill | **Anti-slop tasarım tabanı:** tipografi, boşluk, hareket kadranları, pre-flight kontrolü. | v2 deneysel; takılırsa `design-taste-frontend-v1` kullan. |

### 2.1 pear.no'dan alınacak somut kalıplar

Siteyi inceledim. Kopyalanmayacak ama **kalıp olarak** kullanılacak şeyler:

- **Tek cümlelik, ritmik tagline + ikinci satırda italik vurgu.** Pear: "Pear makes you appear." altında italik alt başlık. AICADBridge'de aynı yapı: kısa ana cümle, altında italik serif ile tamamlayıcı cümle.
- **Başlıklarda italik serif vurgu ve zorlu satır kırılımı.** Başlığın yarısı normal, yarısı italik.
- **"Full disclosure" etiketli açık not bölümleri.** Pear her iddianın altına dürüst şartı koyuyor. AICADBridge karşılığı: **"Açık not"** etiketi ile sınırlılıklar.
- **"We say no more often than yes" bölümü.** Kimin için olmadığını söyleyen bölüm güven kurar. AICADBridge karşılığı: **"Kimler için değil"**.
- **"Asked before" tarzı SSS.** Kısa soru, dürüst, kısa cevap. Başlık: **"Sıkça sorulanlar"** veya **"Daha önce sorulanlar"**.
- **Üstte sabit, 4 maddelik çapa navigasyonu** (The Model / The Work / The Terms / Questions). AICADBridge: Nasıl çalışır / Demo / Kurulum / Sorular.
- **Sade, yasal satırlı footer** (şirket bilgisi + tek iletişim adresi) ve **tek net CTA** (sürekli tekrarlanan "Request Partnership →" gibi).
- **Dil:** "Not X, but Y" kontrastı (Pear: "not an agency on the clock, a partner in the upside"). AICADBridge için bir "X değil, Y" cümlesi türet.

### 2.2 Bilinçli tasarım kararı: zemin

pear.no tamamen açık zeminli ve editoryal (`color-scheme: only light`). AICADBridge'in gerçek arayüzü ise **Dark Neon**.

Öneri (ajan bunu DNA analizinden sonra doğrulasın veya gerekçesiyle değiştirsin):

- Sayfa zemini: **sıcak kırık beyaz, editoryal** (pear.no mantığı).
- Ürün arayüzü: sayfadaki **tek karanlık nesne** olarak, gerçek neon renkleriyle görünür.
- Demo sahnesinde **sert kesme ile tam karanlık zemine** geçiş (scroll-craft'ın "inverted ground" kaçışı buna izin veriyor).
- Neon aksan: **tek bir renk**, `index.html`'deki gerçek değerden alınır. Uydurma mor-mavi gradient yok.

---

## 3. Ürün gerçekleri (kaynak: repo README)

Sitedeki her iddia buraya dayanmak zorunda.

- **Ad:** AICADBridge. **Alt başlık:** AI-Powered CAD Studio for Autodesk Fusion 360.
- **Ne yapar:** Doğal dilde (TR/EN) verilen 3D CAD komutlarını AI modelleriyle Fusion 360 Python API koduna çevirir ve anında çalıştırır.
- **Özellikler:**
  - Doğal dil → 3D model.
  - **Self-Healing CAD:** hata yakalar, Fusion tasarım durumunu okur, hatayı modele gönderir, düzeltilmiş kodu yeniden çalıştırır.
  - **Parametric Sliders:** canlı parametre paneli.
  - **Çift mod:** Fusion 360 içi palet (`adsk.fusionSendData`) ve harici tarayıcı (`localhost:49876` HTTP köprüsü).
  - **Çoklu AI:** Claude, GPT-4o, Gemini, DeepSeek, Ollama / LM Studio (lokal).
  - Dark Neon arayüz.
- **Kurulum (4 adım):** repoyu klonla → Fusion 360 `AddIns` klasörüne taşı → `.env` içine API anahtarlarını yaz → Fusion'da Tools → Add-Ins → Scripts and Add-Ins → AICADBridge → Run.
- **Platform:** Windows ve macOS. **Sürüm:** 1.0.0. **Lisans:** MIT.
- **Yazar:** Yunus Ayyıldız (@yunusayyldz).
- **Örnek komutlar (sitede gerçek içerik olarak kullanılabilir):**
  - TR: "50mm çapında, 80mm yüksekliğinde, merkezinde 20mm delik bulunan bir silindir çiz"
  - TR: "Flanş modeline 4 adet eşit aralıklı M6 cıvata deliği aç"

### 3.1 Sitede YAPILMAYACAKLAR (bu projeye özel)

- **Uydurma istatistik, müşteri yorumu, logo şeridi, "X bin kullanıcı", fiyat tablosu yok.** Repo'nun 1 commit'i ve 1 yıldızı var; sosyal kanıt uydurma. Güven, dürüstlükten ve gerçek demodan gelecek.
- **Model sürümü yazma.** README'deki sürümler ("Claude 3.5 Sonnet" vb.) eskimiş olabilir. Sitede yalnızca sağlayıcı adları kullan (Claude, GPT-4o, Gemini, DeepSeek, Ollama); `config.py` ve kodu kontrol edip güncel olanı doğrula.
- **Sahte dashboard / sahte arayüz çizme.** Sadece gerçek ekran kaydı veya `index.html`'in gerçek ekran görüntüsü.
- **Autodesk bağlantısı ima etme.** Footer'da: "AICADBridge bağımsız bir projedir; Autodesk ile bağlantılı veya onun tarafından onaylanmış değildir. Fusion 360 Autodesk'in markasıdır."
- **"%100 doğru model", "hatasız" gibi vaatler yok.** Self-healing bir onarma döngüsüdür, garanti değil.

---

## 4. Çakışma çözüm sırası

Dört araç aynı anda konuşursa şu sıra geçerli:

1. **Ürün gerçekleri (Bölüm 3)** her şeyin üstünde.
2. **scroll-craft:** scroll mekaniği, sayfa grameri, doğrulama ve sayısal tasarım tabanı (tipografi, boşluk, kontrast).
3. **design-dna:** renk, tipografi ve ölçü değerleri (token'lar) bu çıktıdan gelir.
4. **taste-skill:** anti-slop denetimi ve pre-flight; yukarıdakilerle çelişmediği yerde.
5. **pear.no:** ton, bölüm mantığı ve metin kalıbı. Piksel kopyası değil.

Not: scroll-craft kendi `taste.md` tasarım tabanına sahip. taste-skill ile sayısal çakışma olursa scroll-craft'ınki kazanır.

---

## 5. Kurulum (Faz 0)

```bash
# design-dna
npx skills add zanwei/design-dna

# taste-skill (varsayılan v2 deneysel)
npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend"
# ajan yarım çıktı veriyorsa ek olarak:
npx skills add https://github.com/Leonxlnx/taste-skill --skill "full-output-enforcement"
```

```text
# scroll-craft (Claude Code içinde)
/plugin marketplace add nateherkai/scroll-craft
/plugin install nateherk-design
/reload-plugins            # kurulum özeti isterse
/nateherk-design:scrollcraft
```

scroll-craft ön koşulları: Node 18+, **tam bir ffmpeg build'i**, build klasöründe `playwright-core` + Chrome. İlk iş:

```bash
node scripts/doctor.mjs
node scripts/workspace.mjs --ensure
```

`KIE_AI_API_KEY` **gerekmez**. Kendi ekran kaydımızla çalışacağız (Bölüm 9).

---

## 6. Faz 1: Design DNA (design-dna)

1. **Analyze:** `https://pear.no/` (canlı URL + tam sayfa ekran görüntüleri, masaüstü ve mobil) ve AICADBridge `index.html` arayüzünün ekran görüntüsünü ver.
2. Skill'in şemasına göre **eksiksiz** iki JSON üret:
   - `design-dna/pear.dna.json` (editoryal dil, tipografi ritmi, boşluk, hareket)
   - `design-dna/aicadbridge-ui.dna.json` (neon palet, panel dili, bileşenler)
3. Çelişkileri JSON içinde not et (ör. pear açık zemin, ürün koyu zemin).
4. **Generate** aşamasında ikisini birleştir: **tipografi, ritim, boşluk ve ton pear DNA'sından; ürün nesnesinin rengi ve bileşen dili UI DNA'sından.**
5. İlk geçiş yetersiz görünürse skill'in önerdiği **polish iterasyonunu** çalıştır: aynı referansları tekrar ekle ve hiyerarşi, süsleme, tipografik ritim, hareket, malzemelik ve genel arayüzü referansa göre denetleyip sonuçları mevcut uygulamaya geri işle.

---

## 7. Faz 2: Yaratıcı yön (scroll-craft)

scroll-craft'ın prosedürünü sırayla uygula: interview → grammar → score → build → verify.

### 7.1 Sayfa grameri

Sekiz gramerden **tek** birini seç ve nedenini yaz. Önerim: **chaptered editorial** (pear.no'nun bölümlü editoryal ritmi) + demo sahnesinde **live surface** davranışı. Başka bir grameri daha uygun bulursan gerekçeyle değiştir. Karıştırma; gramerler birbirini dışlar.

### 7.2 Feeling curve (öneri, ajan rafine eder)

Her perde için: duygu, sonra onu ekranda neyin yarattığı.

| Perde | Duygu | Ekranda ne sebep olur |
|-------|-------|-----------------------|
| 1. Hero | Merak, sakinlik | Tek cümle, ilk komut yazılmaya başlar |
| 2. Komut → kod | "Bu kadar mı?" | Türkçe cümle, sağda Fusion API kodu belirir |
| 3. Model oluşur | Tatmin | Flanş, scroll ile adım adım şekillenir (4 adet M6 delik) |
| 4. **PEAK: Self-healing** | Rahatlama | Kod hata verir, sistem hatayı okur, kendini onarır |
| 5. Sliders | Kontrol hissi | Parametre kaydırınca model ölçüsü değişir |
| 6. İki mod + sağlayıcılar | Esneklik | Palet ve tarayıcı yan yana; sağlayıcılar tipografik liste |
| 7. Açık not | Güven | Sınırlılıklar ve "kimler için değil" |
| 8. Kurulum + kapanış | Eyleme hazır | 4 adım, tek CTA |

**Engineered peak = Perde 4.** Asset bütçesi, öncesindeki sessizlik ve en fazla scroll alanı buraya gider. Sayfada tek peak olacak.

### 7.3 İmza hareket (signature move)

Bu siteye özel, başka yerde olmayan **tek** etkileşim. Öneri: **scroll çubuğu "komut satırı" olur.** Ziyaretçi aşağı indikçe komut harf harf yazılır, kod ve model aynı scroll değerinden (`--sc-p`) sürülür. Peak'te scroll'u geri çekince hata "geri sarılıp" onarım yeniden oynar. Daha iyi bir fikir bulursan değiştir; ama mutlaka bespoke olsun.

### 7.4 Parmak izi kapısı (fingerprint gate)

İlk build'de kayıt boş; yine de `FINGERPRINTS.md`'ye kaydı yaz (grammar, nav, hero, act shape, close, signature move).

### 7.5 Engine kuralı

Engine dosyalarına **dokunma**. Tema: 6 renk token'ı + 2 font. Özel şeyleri `--sc-p` ile sür. Config objesinden sayfa üreten runtime kurma.

---

## 8. Faz 3: Metin (copy)

Ton: pear.no gibi **kısa, kendinden emin, süssüz, dürüst.** Mühendislere ve üreticilere yazılıyor.

**Tagline adayları** (birini seç, ya da daha iyisini yaz; sonuncusu pear'daki "ana cümle + italik tamamlayıcı" kalıbının karşılığı):

- TR: *"Söyle, Fusion çizsin."*
- EN: *"Describe it. Fusion draws it."*
- Ana cümle: **"Fusion 360'a cümleyle konuş."** Altında italik: *Model, kod değil niyetle başlasın.*

**Bölüm başlıkları** (iki parçalı, ikinci parça italik):

- Nasıl çalışır: "Bir cümle yazarsın, *model gelir.*"
- Self-healing: "Hata verir, *kendini düzeltir.*"
- Açık not: "Her şeyi yapmıyoruz, *bunları yapıyoruz.*"

**"Açık not" içeriği (repo'dan doğrulanıp yazılacak):**
- Fusion 360 gerektirir; AI sağlayıcı için kendi API anahtarın gerekir (lokal Ollama istisna).
- AI üretimi kod Fusion oturumunda çalışır: önemli tasarımlarını çalıştırmadan önce kaydet. *(Kodda bir sandbox/onay mekanizması var mı kontrol et; varsa söyle, yoksa bu uyarı kalsın.)*
- Sürüm 1.0.0. Hızla gelişen bir proje.

**"Kimler için değil":** Fusion 360 kullanmayanlar, tek tıkla "hatasız" model bekleyenler, API anahtarı veya lokal model kurmak istemeyenler.

**SSS (en az 5):** Ücretli mi? (MIT, sadece kendi API maliyetin.) Hangi AI'lar? Hangi OS? Verilerim nereye gidiyor? (Seçtiğin sağlayıcıya; Ollama ile lokal kalır; kodu doğrula.) Tarayıcı modu nasıl çalışır? Hata verirse ne olur?

**Yasak:** em dash (—), "01 / 06" sayaçları, scroll ipucu okları, gradient metin, "devrim niteliğinde / yeni nesil / sınırları zorlayan" klişeleri, uydurma sayılar.

---

## 9. Asset planı (en kritik eksik)

Sitenin kalitesi **gerçek görüntüye** bağlı. Ajan bunları üretemez; kullanıcı sağlamalı:

1. **Ekran kaydı A (hero/komut → model):** Fusion içinde AICADBridge paletine "50mm çapında, 80mm yüksekliğinde... silindir" yaz, model oluşsun. 1080p, 20 sn.
2. **Ekran kaydı B (PEAK):** Bilerek hata verecek bir komut; self-healing döngüsü görünür. En az 15 sn.
3. **Ekran kaydı C:** Parametric slider'ları oynatma. 10 sn.
4. **Ekran kaydı D:** Harici tarayıcı modunda (`localhost:49876`) aynı iş.
5. **Statik:** `index.html` arayüzünün temiz ekran görüntüsü (açık ve koyu zeminde).

Ajan bu videoları `encode` script'iyle **scrub edilebilir** hale getirir (scroll-craft `assets.md`). Videolar yoksa ajan bunu bildirmeli ve placeholder'ı **açıkça işaretlemeli**, sahte arayüz çizmemeli.

---

## 10. Faz 4: Teknik gereksinimler ve taste kadranları

- **Stack:** Statik çıktı (HTML/CSS/JS veya Astro/Next static export). Sunucu gerektirmeyen, CDN'de çalışan.
- **taste-skill kadranları (öneri):** `DESIGN_VARIANCE: 7`, `MOTION_INTENSITY: 6`, `VISUAL_DENSITY: 3`.
- **Tipografi:** En fazla 2 aile: italik destekli editoryal bir serif (display) + temiz bir sans (gövde). Kod blokları için sistem monospace'i bilinçli istisna olarak belirt. Sıkı takip, gövde metni 45–75ch.
- **Renk:** 6 rol + 1 aksan. Saf siyah yok. İkincil metin gri değil, tonlu.
- **Hareket:** `prefers-reduced-motion` için tam, anlamlı bir statik alternatif.
- **Erişilebilirlik:** Kontrast ölçülsün (kompozit sayfada). Klavye ile gezinme, görünür odak halkası, video için alt metin/transkript.
- **Performans:** LCP < 2.5 sn hedefi. Video lazy-load, poster karelerle. Toplam ilk yük bütçesi belirle ve raporla.
- **SEO ve paylaşım:** Anlamlı `<title>`/meta description (TR+EN), canonical, `hreflang`, Open Graph + Twitter kartı (kendi üretilmiş OG görseli), `sitemap.xml`, `robots.txt`, `SoftwareApplication` JSON-LD.
- **Çıktı:** Eksiksiz dosyalar. "...geri kalanı aynı" gibi yer tutucu yok (taste-skill `full-output-enforcement`).

---

## 11. Faz 5: Doğrulama

1. scroll-craft'ın headless doğrulamasını çalıştır: **dead scroll, hiçbir zaman tam opaklığa ulaşmayan metinler, kompozit kontrast, poster'da takılan video** raporlansın.
2. **Contact sheet** üret ve kullanıcıya göster; makine çalıştığını kanıtlar, anlamlı olup olmadığını insan karar verir.
3. taste-skill **pre-flight** kontrolünü çalıştır ve sonucu yaz.
4. Mobil (375px), tablet, masaüstü ekran görüntüleri; başlık 4+ satıra sarmasın.
5. Lighthouse (performans, erişilebilirlik, SEO) skorlarını raporla.

---

## 12. Faz 6: Canlıya alma kontrol listesi

**Kullanıcının canlıdan önce yapması gerekenler (ajan hatırlatsın):**

- [ ] Repo'daki `CADAM_Tersine_Muhendislik_Mimarisi.md` dosyasını gözden geçir: başka bir açık kaynak projeyi tersine mühendislikle analiz ediyor gibi görünüyor. Atıf, lisans ve ticari kullanım uyumunu doğrula. Siteyi duyurmadan önce açık bir karar ver (kalsın / atıflı kalsın / kaldır).
- [ ] `.env` ve API anahtarlarının repo geçmişinde olmadığından emin ol.
- [ ] Repo'ya görsel (README banner, ekran görüntüsü) ve gerçek bir Release ekle; sitedeki "İndir" CTA'sı buna bağlansın.
- [ ] Autodesk marka uyarısı footer'da.
- [ ] Alan adı, iletişim e-postası ve (gerekiyorsa) gizlilik notu hazır.
- [ ] Analitik kullanılacaksa çerezsiz bir çözüm tercih et (çerez bandı gerektirmesin).

**Yayın:** Statik host (Cloudflare Pages, Vercel veya GitHub Pages), özel alan adı, HTTPS, `www` yönlendirmesi, 404 sayfası.

---

## 13. Teslim kriterleri (hepsi sağlanmadan "bitti" deme)

- [ ] Tek bir sayfa grameri, tek peak, tek imza hareket; gerekçeleri yazılı.
- [ ] Her iddia Bölüm 3'e dayanıyor; uydurma sayı yok.
- [ ] `pear.dna.json` ve `aicadbridge-ui.dna.json` repoda.
- [ ] `FINGERPRINTS.md` dolu.
- [ ] Doğrulama raporu + contact sheet + pre-flight sonucu.
- [ ] TR/EN, reduced-motion, mobil, SEO, OG tamam.
- [ ] pear.no'dan hiçbir metin, medya veya görsel birebir alınmadı.
- [ ] Eksik asset'ler (Bölüm 9) açıkça listelendi.

---

## 14. Başlangıç Promptu (kopyala-yapıştır)

```text
BRIEF.md dosyasını baştan sona oku ve onu tek gerçek talimat olarak kabul et.

Görev: AICADBridge (https://github.com/yunusayyldz/AICADBridge) için canlıya alınacak, Türkçe/İngilizce, scroll odaklı resmi tanıtım sitesi yap.

Referanslar ve rolleri:
- https://pear.no/ -> ses, bölüm mantığı, "açık not" ve "kimler için değil" kalıpları, italik serif vurgulu başlıklar. İçeriği kopyalama.
- https://github.com/zanwei/design-dna -> pear.no'yu ve AICADBridge index.html arayüzünü analiz edip iki DNA JSON üret, sonra bunlardan üret.
- https://github.com/nateherkai/scroll-craft -> scroll motoru, tek sayfa grameri, tek peak, bespoke imza hareket, headless doğrulama. Engine'e dokunma.
- https://github.com/Leonxlnx/taste-skill -> anti-slop denetimi, tipografi/boşluk, pre-flight.

Çalışma sırası:
1. Önce repo README'sini ve index.html'i oku; ürün gerçeklerini Bölüm 3 ile karşılaştır, fark varsa bana söyle.
2. Faz 0 kurulumlarını yap; doctor'ı çalıştır, eksik varsa dur ve bildir.
3. Faz 1: iki Design DNA JSON.
4. Faz 2: grammar, feeling curve, peak ve imza hareket önerini yaz; BANA ONAYLATMADAN build'e geçme.
5. Onaydan sonra Faz 3-4: metin ve build.
6. Faz 5: doğrulama, contact sheet, pre-flight.
7. Faz 6: canlı kontrol listesini bana ver.

Kesin kurallar:
- Uydurma istatistik, yorum, logo, fiyat, model sürümü yok.
- Sahte arayüz/dashboard çizme; gerçek ekran kaydı yoksa placeholder'ı açıkça işaretle ve Bölüm 9'daki eksikleri listele.
- Em dash (—) kullanma.
- Eksiksiz dosya yaz, yer tutucu yorum bırakma.
- Bir kural diğerleriyle çelişirse Bölüm 4'teki sırayı uygula.
```
