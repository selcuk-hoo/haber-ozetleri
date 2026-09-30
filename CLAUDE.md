# Dünyadan Notlar — bakım rehberi

Dünya basınından haberleri toplayıp Türkçe özetleyen kişisel bir site:
https://selcuk-hoo.github.io/haber-ozetleri/ . Kullanıcıyla Türkçe konuşulur;
kod, yorum ve commit mesajları da Türkçedir. Genel tanıtım README.md'de; bu
dosya değişiklik yaparken izlenecek yolları anlatır.

## Nasıl çalışıyor

- `.github/workflows/haber.yml` yarım saatte bir `scripts/haber_uret.py`'yi
  çalıştırır: beslemeler → makale metni (trafilatura) → özet (ilk N cümle +
  kaynağa özel temizlik) → çeviri (Yemek, Gezi ve Sanat & Kültür'de Claude,
  gerisinde Google) →
  `dist/index.html`.
- Yalnız `main` dalındaki çalıştırmalar yayınlar: `dist/` her seferinde
  `gh-pages` dalına force-push edilir. `gh-pages`'e elle dokunulmaz.
- `gh-pages`'te üretimin kendi durumu da durur: `arsiv.json` (7 günlük eski
  haberler), `ceviri.json` (çeviri önbelleği), `takip.json` (haberlerin ilk
  görülme anı ve içerik imzaları, bkz. `takip.py`) ve `saglik.json` (süren
  sorun sayaçları). Her çalıştırma bunları okuyup yeniden yazar.
- Bir sorun (hiç haber getirmeyen kaynak, Google ya da Claude çevirisi
  çalışmıyor) ~3 saat sürerse depoda "Site sağlık uyarısı" kaydı (issue)
  açılır, sahibine e-posta gider; sorun geçince kapanır (`saglik.py`).

Modüller: `ayarlar.py` (elle değiştirilen her şey: kaynaklar, sayılar,
yönlendirmeler), `besleme.py`, `ozet.py` (temizlik kuralları), `ceviri.py`,
`claude_ceviri.py`, `markalar.py`, `olaylar.py` (aynı olayı birleştirme), `arsiv.py`, `takip.py` (ilk görülme,
güncellenen haberi öne alma), `saglik.py` (süren sorunlarda uyarı kaydı), `tarih.py`, `sayfa.py` +
`web/` (HTML/CSS/JS), `model.py`.

## Çalışma düzeni

1. Değişiklik geliştirme dalında yapılır, testler yerelde çalıştırılır:
   `python -m unittest discover -s tests -v`
2. Geliştirme dalına push → iş akışı orada da çalışır ama **yayınlamaz** ve
   **Google çevirisi kapalıdır** (`CEVIRI_KAPALI`, yalnız önbellek). Loglardan
   sonuca bakılır. Orada çalıştırma her zaman "success" görünür
   (`continue-on-error`, kullanıcıya boşuna e-posta gitmesin diye); gerçek
   sonuç için **işin (job) sonucuna** ve adımlara bak (`list_workflow_jobs`).
3. Sonuç iyiyse main'e merge + push. Yayından sonra canlı sayfa
   `git fetch origin gh-pages && git show origin/gh-pages:index.html` ile
   kontrol edilir (github.io'ya doğrudan erişim olmayabilir).
4. Bozuk bir test main'de yayını durdurur; bu bilinçli bir emniyet.

### Geçici teşhis adımı

Geliştirme ortamının internet erişimi kısıtlı olabilir; bir beslemeyi ya da
sitenin metnini denemek için GitHub'ın sunucusu kullanılır:

- `.github/teshis/<ad>.py` yaz (çıktı satırlarını `[TESHIS]` ile başlat).
- `haber.yml`'de `python scripts/haber_uret.py` adımından önce ekle:
  ```yaml
  - name: GEÇİCİ teşhis (...)
    if: github.ref != 'refs/heads/main'
    run: python .github/teshis/<ad>.py
  ```
- Geliştirme dalına push, logu oku.
- **Main'e merge etmeden önce hem dosyayı hem adımı kaldır** ve
  `grep -c teshis .github/workflows/haber.yml` ile 0 olduğunu gör.
- Teşhis betiği Google'a istek atacaksa az ve aralıklı at (bkz. Google).

## Reçeteler

### Özette kalıntı var ("Share", editör adı, reklam cümlesi…)

1. Canlı sayfadan ya da teşhisten **gerçek metni** bul.
2. `ozet.py` → `KAYNAK_KURALLARI[kaynak adı]` içine uygun anahtarı ekle:
   - `sil`: metnin herhangi bir yerinden silinecek kalıp. **Başlık
     kırpılmadan önce** uygulanır; metin çoğu zaman başlıkla başladığı için
     `^` ile bağlanan kalıp tutmayabilir (Phys.org editör künyesi hatası).
   - `bas`: başlık kırpıldıktan sonra metnin başındaki etiket ("NewsFeed").
   - `kes`: eşleştiği yerden sonrası atılır (ilgili haberler, malzeme listesi).
   - `cumle_at`: eşleşen cümle atılır (abonelik çağrısı, komisyon notu).
   - `baslik_sonu`: başlığın sonundan silinir (" | CNN", dizi adı).
   - `etiket_at`: yayıncının sayfa etiketlerinden biri uyan haber alınmaz
     (TechCrunch "techcrunch disrupt", "fundraising"; The Verge "good-deals").
     Reklam/indirim/etkinlik gibi yazı **türleri** için önce buna bak: başlık
     kelimeleri sonsuz çeşitli, etiket sabit. Etiketleri görmek için teşhiste
     `besleme.sayfa_etiketleri(bare_extraction(...).as_dict())` yazdır.
   - `haber_at`: başlığı uyan haber hiç alınmaz, arşivden de çıkar (etiketin
     yedeği). `birak`: başlığı uyan haber ikisine rağmen kalır (milyar dolar).
3. `tests/test_ozet.py`'ye **gerçek örnekle** test ekle (başlık dahil).
   Bir kuralın, sıradan metne dokunmadığını gösteren test de yaz.
4. Kural anahtarı `KAYNAKLAR`'daki kaynak adıyla aynı olmalı (test kontrol eder).
5. Kural haberlerin metnini değiştirir; `takip.py` bunu kaynağın
   haberlerinin çoğu (≥%30 ve ≥3) aynı turda değiştiyse "bizim değişikliğimiz"
   sayar. Yalnız bir iki haberi etkileyen kural o haberleri bir kez
   "güncellendi" diye öne alabilir; zararsız.

### Yeni kaynak

1. Beslemeyi teşhisle dene: öğe sayısı, tarihler, `makale_getir` sonucu,
   görsel, özet temizliği. 403 veren, beslemesi olmayan ya da aylarca
   yazmayan siteler elenir.
2. `ayarlar.KAYNAKLAR`'a `(kategori, ad, adres)` ekle. Kaynak ekleme/çıkarma
   **kullanıcının onayıyla** yapılır.
3. Metni Türkçeyse `TURKCE_KAYNAKLAR`'a ekle (çevrilmez; gruplama için
   İngilizcesi alınır).
4. Gerekirse: bölüm atlamak için `ATLANAN_BOLUMLER` (adres kalıbı), bir
   kaynağın yazılarını başka sekmeye yönlendirmek için `HARIC_BESLEMELER`,
   özet uzunluğu için `KATEGORI_OZET_CUMLE`, haber sayısı için
   `KATEGORI_SAYISI` / `KAYNAK_SAYISI`.

### "Bir kategori güncellenmiyor"

Önce kaynağın kendisine bak: beslemedeki son tarihler sayfadakilerle aynıysa
sorun bizde değildir (ABD'li yemek siteleri hafta sonu yazmıyor). Kullanıcı
eski bir translate.goog sekmesinden bakıyor olabilir (`tazele.js` 45 dk'dan
eski sayfayı yeniler). Sonra iş akışı loglarında o kaynağın satırına bak.

### Özet uzunluğu

Özet = temizlenmiş metnin ilk N cümlesi (`K`, kategoriye göre
`KATEGORI_OZET_CUMLE`). "Başlıkla en çok örtüşen cümleleri seç" yöntemi 55
gerçek yazıda denendi, çoğunda kötüleştirdi; geri alındı. Kullanıcı ilk
cümlelerin "metnin başlangıcı" olmasından memnun.

## Google çevirisi — dikkat

- Ücretsiz, resmi olmayan uç nokta; fazla istekte **429** verir. Her metin
  bir kez çevrilir, `ceviri.json`'da İngilizce metnin özetiyle (hash) saklanır.
- **Toplu yeniden çeviriye yol açan değişikliklerden kaçın**: İngilizce metni
  değiştiren her şey (özet cümle sayısı, yeni temizlik kuralı, başlık
  çevirisi yöntemi) o metinleri yeniden çevirtir. Yüzlerce metni etkiliyorsa
  sınırla ya da kullanıcıya söyle. 260 başlığın bir anda yeniden çevrilmesi
  canlı sitede de 429'a yol açmıştı.
- Marka/yayın adları (`markalar.py`): Google "Hugging Face"i "Sarılma
  Yüzü", "Anthropic"i "Antropik" yapabiliyor. Listedeki adlar çeviride "X1Q"
  yer tutucusuyla gider, ek adın okunuşuna göre yeniden çekimlenir. Yeni ad
  eklerken okunuşun sonunu doğru yaz ("Face" → "eys") ve sıradan kullanımı
  bozmayacak kalıp seç ("Surface" değil "Surface Mouse"). Liste değişip
  önbellekteki eski çevirilerin yenilenmesi gerekirse `ceviri.MARKA_SURUMU`
  artırılır (yalnız o adı içeren metinler yeniden çevrilir).
- Hata olunca: 5 ve 30 sn bekleyip yeniden dener; olmazsa o turda durur,
  metni değişmiş haberde önceki çeviri gösterilir. Hiç çevirisi olmayan yeni
  haberler o turda Claude'a çevirtilir (`haber_uret.claude_yedegi`, en fazla
  80 metin); Claude da yoksa o yayında gösterilmez. Kartların yarısından azı çevrilebildiyse sayfa
  İngilizce üretilir ve okur translate.goog'a yönlenir.

## Claude çevirisi (Yemek, Gezi, Sanat & Kültür)

- Google yemek yazılarını kelimesi kelimesine çeviriyordu ("scramble to
  make" → "yapmaya çabaladığımız", "apple butter" → "elma yağı").
  `ayarlar.CLAUDE_KATEGORILERI`'ndeki haberler `claude_ceviri.py` ile
  çevrilir: iş akışında Claude Code CLI (`claude -p`), kullanıcının Claude
  aboneliğiyle, `CLAUDE_CODE_OAUTH_TOKEN` gizli değişkeniyle. Anahtara
  dokunma, loga yazdırma.
- Çevirmen talimatı ortak kurallar + kategoriye özgü rol ve kurallardan
  oluşur (`claude_ceviri.ALANLAR`). Deneme dalında
  bütün karşılaştırmalar loga tam yazılır.
- Model Sonnet (`claude_ceviri.MODEL`). Sonnet/Haiku/Opus 8 gerçek metinde
  karşılaştırıldı: Opus biraz daha iyi ama abonelik limitini hızlı tüketir;
  Haiku Google'dan pek iyi değil.
- Çeviri önbellekte `"bk"/"ok": "c"` işaretiyle durur; Google çevirisi olan
  metin bir kez Claude'a gider. Çalıştırma başına en fazla
  `CALISTIRMA_BASINA_METIN`. Claude yoksa ya da hata verirse (limit, zaman
  aşımı) kalanlar Google'la çevrilir; bozuk JSON cevabında parça bölünüp
  yeniden denenir. Deneme dalında da çalışır (Google gibi kapalı değil);
  loglarda "EN / G / C" karşılaştırması görünür. Her kategori satırında o
  ana kadarki token kullanımı yazar (`claude_ceviri.kullanim`; haftada
  ~265 bin token tahmini, 30.09.2026).
- Kategori içinde Google'da kalan kaynaklar `ayarlar.CLAUDE_HARIC_KAYNAKLAR`
  (The Art Newspaper: düz haber dili, Google iyi; en çok yazan kaynak).
- Başka kategoriye açmak aboneliğin kullanım limitini tüketir; önce
  kullanıcıya sor.

## Paket sürümleri

`requirements.txt`'te bütün sürümler sabit. pip bir kez bağımlılık çakışması
yüzünden trafilatura'nın 2019 sürümüne gerileyip üretimi durdurmuştu.
Güncellerken sürümleri birlikte değiştir, geliştirme dalında kurulum + test +
bir üretim çalıştırması geçtiğini gör, sonra main'e al.

## Bilinçli kararlar (değiştirmeden önce kullanıcıya sor)

- Buton ve etiket metinleri `data-etiket` + CSS `::before` ile yazılır (DOM'da
  metin yok): Google Translate'in fareyle üzerine gelince açılan balonu
  çıkmasın diye. `tests/test_web.py` bunu denetler.
- Sayfada tam metin/tam çeviri yok: telif (yalnız kısa özet + kaynağa bağlantı).
- Arama tamamen tarayıcıda (`arama.js`); eski haberlerde yalnız başlık
  aranır, özetleri sayfaya eklemek ~1 MB büyütür. Kutu translate.goog'da
  kurulmaz.
- Sanat & Kültür magazinden arındırıldı (Variety çıkarıldı, Guardian'ın
  müzik/TV/yaşam bölümleri ve TV/müzikal etiketli yazıları, Euronews'ün
  "magazin dünyası" etiketlileri atlanıyor, BBC Culture kullanılıyor).
  30.09.2026: SCMP'nin sanat sayfası çıkarıldı (çoğu Hong Kong yereli);
  Aeon (denemeler) ve Literary Hub (edebiyat) eklendi. Euronews'ün
  "kültür ajandası" etiketi ayıklamada kullanılmaz (iyi yazıların çoğunda
  var).
- Yemek'e Lezzet eklenmedi (kullanıcı: tarifler Türk okura yeni değil).
- Gezi'den Condé Nast Traveler çıkarıldı: okur kaynağa gidince abonelik
  duvarına çarpıyordu. Yerine Guardian Travel ve BBC Travel. Aynı sebeple
  Yemek'ten Bon Appétit çıkarıldı, yerine kaynak konmadı (Serious Eats
  denendi: güncel yazıları çoğunlukla tarif derlemesi). Yeni kaynakta
  abonelik duvarına da bak (teşhiste sayfada "paywall" /
  `isAccessibleForFree`).
- Gündem (30.09.2026 incelemesi): bakış açısı çeşitliliği bilinçli (Batı
  kamu yayıncıları, CNN, Al Jazeera, SCMP, Moscow Times, AA). Türk okura
  boş gelenler ayıklanıyor: spor, magazin, TV programları, başka ülkenin
  yerel haberleri (SCMP Hong Kong yereli, MercoPress Falkland), AA'nın
  protokol haberleri ("… görüştü", "… kabul etti"). Türkiye'ye bağımsız
  dış göz için DW Türkçe ve BBC Türkçe; Afrika ve Latin Amerika için
  Africanews ve MercoPress eklendi. Elenenler: The Hindu (abonelik
  duvarı), Kyodo/NHK (besleme alınamadı).
- Site adı "Dünyadan Notlar", alt başlık "Dünya basınından kısa kısa".
- Yazı tipleri (bkz. `scripts/web/fontlar/BENIOKU.md`): site adı art deco
  Limelight (sayfaya gömülü alt küme, "DN Baslik"); alt başlık Caslon italik
  (gömülü alt küme, "DN Alt"); özet metni Libre Caslon Text 400, haber,
  ilgili haber ve arşiv başlıkları aynı yazı tipinin kalını (700; ikisi de
  "DN Ozet", `dist/fontlar/`). Düğmeler, sekmeler, etiketler bilerek
  cihazın düz yazı tipinde. Özet metninde saydamlık yok; açık temada .1px
  kontur (`--ozet-kontur`), koyu temada yok (.3px "fazla koyu" bulundu).
