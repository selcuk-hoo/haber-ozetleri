# Dünyadan Notlar — bakım rehberi

Dünya basınından haberleri toplayıp Türkçe özetleyen kişisel bir site:
https://selcuk-hoo.github.io/haber-ozetleri/ . Kullanıcıyla Türkçe konuşulur;
kod, yorum ve commit mesajları da Türkçedir. Genel tanıtım README.md'de; bu
dosya değişiklik yaparken izlenecek yolları anlatır.

## Nasıl çalışıyor

- `.github/workflows/haber.yml` saatte bir (harici zamanlayıcı cron-job.org
  tetikler, bkz. README) `scripts/haber_uret.py`'yi çalıştırır: beslemeler
  → makale metni (trafilatura) → özet (ilk N cümle + kaynağa özel temizlik)
  → çeviri (Yemek, Gezi ve Sanat & Kültür'de Claude, gerisinde Gemini;
  ikisi de olmazsa Google) → `dist/index.html`.
- Yalnız `main` dalındaki çalıştırmalar yayınlar: `dist/` her seferinde
  `gh-pages` dalına force-push edilir. `gh-pages`'e elle dokunulmaz.
- `gh-pages`'te üretimin kendi durumu da durur: `arsiv.json` (7 günlük eski
  haberler), `ceviri.json` (çeviri önbelleği), `takip.json` (haberlerin ilk
  görülme anı ve içerik imzaları, bkz. `takip.py`), `saglik.json` (süren
  sorun sayaçları), `olay_kararlari.json` (olay süzgecinin kararları),
  `manset_olaylari.json` ve `manset.json` (Manşet sekmesi).
  Her çalıştırma bunları okuyup yeniden yazar.
- Bir sorun (hiç haber getirmeyen kaynak; Google, Gemini ya da Claude
  çevirisi çalışmıyor) ~3 saat sürerse depoda "Site sağlık uyarısı" kaydı
  (issue) açılır, sahibine e-posta gider; sorun geçince kapanır (`saglik.py`).

Modüller: `ayarlar.py` (elle değiştirilen her şey: kaynaklar, sayılar,
yönlendirmeler), `besleme.py`, `ozet.py` (temizlik kuralları), `ceviri.py`,
`claude_ceviri.py`, `gemini_ceviri.py`, `markalar.py`, `olaylar.py` (aynı
olayı birleştirme), `olay_suzgeci.py` (gruplamanın Gemini süzgeci),
`manset.py` (Manşet sekmesi),
`arsiv.py`, `takip.py` (ilk görülme, güncellenen haberi öne alma),
`saglik.py` (süren sorunlarda uyarı kaydı), `tarih.py`, `sayfa.py` + `web/`
(HTML/CSS/JS), `model.py`.

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
     (TechCrunch "techcrunch disrupt", "fundraising"; The Verge "good-deals",
     "reviews", "pagetype:stream"; Phys.org "education", "economics &
     business").
     Reklam/indirim/etkinlik gibi yazı **türleri** için önce buna bak: başlık
     kelimeleri sonsuz çeşitli, etiket sabit. Etiketleri görmek için teşhiste
     `besleme.sayfa_etiketleri(bare_extraction(...).as_dict())` yazdır.
   - `metin_at`: temizlikten önce metin bu kalıpla başlıyorsa haber hiç
     alınmaz (T24 "T24 Dış Haberler", "T24 Spor" bölüm imzası; başlıkta ve
     etiketlerde bölüm görünmediğinde).
   - `ilk_satir_at`: metnin ilk satırları (en fazla 3) kalıba uydukça
     atılır (Africanews ülke satırı, Quanta "Introduction"); başlıkla aynı
     ilk satır da atlanır.
   - `ara_baslik_at`: metnin ortasında başlıkla aynı satır ve ardından gelen
     alt başlık satırı atılır (The Verge).
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
   İngilizcesi alınır). Beslemesi ve kullanışlı site haritası yoksa
   `ANASAYFA_KAYNAKLARI`'na bağlantı kalıbı ekle (T24): haberler anasayfadan
   alınır, tarih haberin kendi sayfasından okunur.
4. Gerekirse: bölüm atlamak için `ATLANAN_BOLUMLER` (adres kalıbı), bir
   kaynağın yazılarını başka sekmeye yönlendirmek için `HARIC_BESLEMELER`,
   özet uzunluğu için `KATEGORI_OZET_CUMLE`, haber sayısı için
   `KATEGORI_SAYISI` / `KAYNAK_SAYISI`.

### "Bir kategori güncellenmiyor"

Önce kaynağın kendisine bak: beslemedeki son tarihler sayfadakilerle aynıysa
sorun bizde değildir (ABD'li yemek siteleri hafta sonu yazmıyor). Kullanıcı
eski bir translate.goog sekmesinden bakıyor olabilir (`tazele.js` 75 dk'dan
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
  80 metin); Claude da yoksa o yayında gösterilmez. Kartların yarısından
  azı çevrilebildiyse sayfa İngilizce üretilir ve okur translate.goog'a
  yönlenir.

## Gemini çevirisi (Gündem, Teknoloji, Bilim)

- 02.10.2026'dan beri. 48 gerçek metinde puanlar: Google ~6,5, Gemini 2.5
  Flash ~7,5, Flash-Lite ~7,5 (bir paket bozuk JSON), Sonnet ~8,5. Bu
  hacmi (günde ~500 haber) Claude'a vermek aboneliğin haftalık limitinin
  yarısını yerdi; Gemini'nin ücretsiz katmanı yetiyor.
- `gemini_ceviri.py`: Google AI Studio anahtarı `GEMINI_API_KEY` gizli
  değişkeninde, istekte başlıkla gider. Anahtara dokunma, loga yazdırma.
  Projede ödeme (billing) açılmamalı: ücretsiz katmanda kalsın, kota
  dolunca ücret değil hata çıksın.
- Talimat Claude'unkiyle aynı (`claude_ceviri.ALANLAR`'da Gündem, Teknoloji,
  Bilim de var; Google durunca Claude yedeği de bunları kullanır). Haberin
  kesinlik derecesini koruma kuralı ("reportedly" → "bildirildi") bilerek
  var: Gemini ilk denemede iki başlıkta bunu atıp söylentiyi kesin haber
  gibi yazmıştı.
- **Ücretsiz hak model başına**: 3.5 ve 3.1 Flash-Lite günde 500 istek,
  2.5 / 3.5 / 3.8 Flash yalnız 20 (AI Studio rate-limit sayfası,
  02.10.2026). `MODELLER`: 3.5 Flash-Lite (`gemini-flash-lite-latest`) →
  2.5 Flash → 3.5 Flash → 3.1 Flash-Lite. Paketler büyük (`PARCA_BOYU` 40;
  saatlik çalıştırma çoğunlukla tek istek).
  503'te (yoğunluk) aynı model bir kez daha denenir, 429'da (kota)
  sıradakine geçilir; hepsi başarısız olursa kalanlar Google'a. Teşhis ve
  denemeler de aynı hakkı yer: deneme dalında Gemini'ye az istek at.
  Güncel sınırlar: ai.dev/rate-limit (kullanıcının hesabında).
- Yalnız hiç çevirisi olmayan metinler gider (`Cevirmen.ceviri_gerekli_mi`);
  önbellekte `"bk"/"ok": "g"`. Çalıştırma başına en fazla
  `CALISTIRMA_BASINA_METIN`. Deneme dalında kapalı (anahtar yalnız main'e
  verilir; aynı kotayı yemesin). Gemini'yi denemek için teşhiste zincirde
  olmayan bir model kullan, az istek at.
- Güncelleme saatte bir (harici zamanlayıcı): 2 saatte Phys.org ve CNN'in
  haberleri sayfaya girmeden geçiyordu; 1 saatte kayıp yok.

## Olay süzgeci (aynı olayı anlatan haberler)

- `olaylar.py`'nin kelime benzerliği tek başına "aynı konu, farklı olay"
  birleştiriyordu (02.10.2026: 14 grubun 3'ü yanlış, "Tek günlük korolar"
  + "Anthropic'in VPN kısıtlaması"). `olay_suzgeci.py`: algoritma gevşek
  eşikle (0.12, 1 ortak isim) ADAY gruplar üretir; Gemini 3.5 Flash-Lite
  her adayda aynı somut olayı anlatanları seçer (yalnız başlık + ilk cümle
  gider). Gemini sıfırdan grup kuramaz.
- Kararlar `olay_kararlari.json`'da (3 gün): aynı aday yeniden sorulmaz,
  üyesi azalan aday eski karardan türetilir; yalnız yeni/yeni üye almış
  adaylar çalıştırma başına tek istekte gider. Gemini yoksa ya da cevap
  vermezse o haberler için bugünkü temkinli eşikler (olaylar.ESIK).
- Model karşılaştırması (canlı adaylar): 3.5 Flash-Lite ve 3.5 Flash 10/10
  doğru (Lite 1 sn, Flash 21 sn); 3.1 Flash-Lite 2 yanlış; Haiku 4 yanlış
  ve uzun açıklama yazdı; Sonnet doğru ama abonelikten yer.
- Derleme (gruptaki haberlerden tek özet) denendi: Sonnet iyi yazıyor ama
  haftalık limitin ~%7'si daha; kullanıcı "fazla" dedi. Gemini Flash-Lite'ın
  günde 500 hakkıyla yeniden denenebilir.

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

## Manşet (03.10.2026)

- Kategorilerin en solunda "Manşet" sekmesi (sayfa yine Gündem'le açılır):
  son 24 saatin önemli olaylarının Türkçe derlemesi (`manset.py`). Önce
  Gündem'in tepesinde "Dünün özetleri" kutusuydu; kullanıcı "sürekli
  tepede olması iyi değil" dedi, adı da tek kelime istedi.
- Günde iki baskı: Türkiye saatiyle 08:00 ve 17:00 (`MANSET_SAATLERI`; gece
  okunmuyor). Her saatlik çalıştırma olay süzgecinin Gündem gruplarını
  `manset_olaylari.json`'a ekler (ortak haberi olan gruplar birleşir, ilk
  görülme anı tutulur). Baskı saatinden sonraki ilk çalıştırmada son 24
  saatte ortaya çıkan, en az 2 kaynaklı olaylar (en çok `MANSET_ADAY`) iki
  Sonnet çağrısıyla işlenir:
  1. **Puanlama** (başlık + ilk cümleler): her kıstas 0-10; etki
     (genişlik) %32, kalıcılık %27, dönüm (gidişatı değiştiriyor mu) %18,
     eylem (karar mı, söz mü) %13, Türkiye'ye yakınlık %10. Puan = ağırlıklı
     ortalama (`MANSET_AGIRLIKLAR`); hesabı Python yapar.
  2. **Derleme**: `MANSET_ESIK`'i (6,0) geçenler, en çok 3. Geçen yoksa o
     baskıda manşet ve sekme yok, ikinci çağrı yapılmaz.
  Sonuç (puanlar ve gerekçeler dahil) `manset.json`'da; öteki
  çalıştırmalar yalnız okur. Loga puan tablosu yazılır.
- **Türkiye manşeti** (kullanıcının isteği; örnek: Erdoğan'ın BM ziyareti):
  Türkçe kaynakların ve AA'nın haberleri (`MANSET_TR_KAYNAKLAR`; gruba
  girmemiş tek kaynaklılar da kayda alınır) ayrı bir çağrıyla kendi
  kıstaslarıyla puanlanır: kapsam %25, kalıcılık %20, kurumsal (devlet,
  yargı, demokrasi, basın, ekonomi politikası) %20, kamuoyu %20, dış
  ilişkiler %15. Sonnet "Türkiye haberi değil" derse (Türkçe yazılmış dünya
  haberi) elenir; dünya manşetine girenler aday olmaz. Eşik 5,0 (Türkiye
  puanları sıkışık: ilk denemede en yüksek 5,4), en çok 1 kutu; kırmızı
  çizgili, "MANŞET · TÜRKİYE" etiketli. Aynı kaynağın aynı olay hakkındaki
  birkaç haberi ayrı ayrı puanlanır (T24'ün kendi erişim engeli: 4 haber).
- Maliyet Türkiye manşetiyle baskı başına 3 çağrı, ~13 bin girdi + 5 bin
  çıktı token (API karşılığı ~$0,09).
- Kutular `<article>`: Dinle ve Özeti paylaş kartlardaki gibi (`dinle.js`
  `.ozet-metni`'ni de okur). Önceki baskılar `manset_arsiv.json`'da 7 gün;
  sekmenin altında açılır liste (son baskı boşsa da sekme kalır).
- Kullanıcının ayarları: Türkiye önce +1 ek puandı, sonra %15, sonra %10
  (öteki ağırlıklar oranları korunarak yeniden dağıtıldı); eşik 6,5'ten
  6,0'a indi. Sonnet'in puanı aynı olayda ±1 oynayabiliyor (G7: 8,1 / 7,2).
- Neden puan: kaynak sayısı "ne kadar konuşuldu"yu ölçüyor. İlk sürümde
  4 kaynağın yazdığı Christa Pike'ın başarısız infazı (yerel, insani ilgi)
  girmişti; kullanıcı "fazla lokal" dedi. Puanlamada ~3 aldı, G7'nin petrol
  kararı 7-8. Kaynak sayısı yalnız aday seçer.
- Maliyet: baskı başına 2 çağrı, ~5 bin girdi + 1,5 bin çıktı token (API
  karşılığı ~$0,035); günde iki baskı. Başarısızsa baskı başına en çok 3
  deneme; olmazsa önceki baskı 36 saate kadar kalır, sonra sekme kalkar
  (yanlış bilgi yerine boşluk).
- Talimat ya da yöntem değişince `manset.SURUM` artırılır: son baskı
  yeniden hazırlanır.
- Neden Sonnet: Flash-Lite ~6 puan (olayı ters anlattı, uydurma sözcük);
  3.8 / 3.5 Flash gece de 503 ve zaman aşımı verdi (03.10.2026).
- Deneme dalında kapalı (Claude'a boşuna gitmesin; durum gh-pages'e
  yazılmadığı için her seferinde hazırlanırdı). Denemek için geçici olarak
  `MANSET_ZORLA=1` ver; loga puanlar ve `[MANSET]` satırları yazılır.
- Sekme ötekilerden ayrılır: vurgu renginde çerçeve ve yazı; okurun
  açmadığı yeni baskıda kırmızı nokta (`manset.js`, localStorage
  `mansetGoruldu`). Manşet kutusu: üstte görsel (olayı yazan kaynakların
  haber görsellerinden ilki), "MANŞET · 3 KAYNAK" üst etiketi, hafif
  vurgu tonu.
- Sekme yalnız Türkçe sayfada; Manşet seçiliyken görünüm anahtarı ve kaynak
  menüsü gizlenir (`filtre.js`, `:root[data-manset]`), aramada manşet
  gizlenir. Kullanıcı birkaç gün izleyip karar verecek; kaldırmak için
  `sayfa_olustur`'a manşet vermemek ve `haber_uret.uret`'teki bloğu silmek
  yeter.
- Sınır: dünya manşetine yalnız en az 2 kaynağın yazdığı (olay süzgecinin
  grupladığı) olaylar aday olur.

## Sayfa ağırlığı ve ana ekran (03.10.2026)

- "Eski haberler" listesi (~2.800 başlık, ~1 MB, sayfanın yarısı) Türkçe
  sayfada ayrı dosyada (`eski.html?v=<çalıştırma>`; `sayfa._arsiv_html`).
  `filtre.js` `arsiviYukle` onu "Eski haberler"e ya da aramaya ilk
  başvuruda bir kez indirir. İngilizce (yedek) sayfada liste sayfada kalır
  (translate.goog çevirsin).
- `manifest.webmanifest` + `web/simge/` (kahve zeminde Limelight "DN"):
  telefonda ana ekrana eklenip uygulama gibi açılır.

## Açık işler (03.10.2026)

- cron-job.org hâlâ yarım saatte bir tetikliyor olabilir; kullanıcıdan
  saatte bire çekmesi istendi (site saatlik düzene göre ayarlı).
- Maliyet: uzun bir Claude Code oturumu kullanıcının kredisini hızlı
  harcadı (02.10.2026, ~64 dolar). Oturumları kısa tut, büyük logları
  dosyaya alıp yalnız gereken satırları oku, gereksiz bekleme/deneme yapma.

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
- Bilim ve Teknoloji (30.09.2026): basın bülteni ağırlıklı Phys.org 6
  habere indirildi, eğitim/ekonomi etiketlileri atlanıyor; Bilim'e Quanta
  Magazine (uzun açıklayıcı yazılar), Teknoloji'ye Ars Technica eklendi.
  The Verge'ün ürün incelemeleri ("reviews") ve konu akışı sayfaları
  ("All the latest news on …") atlanıyor.
- T24 (02.10.2026, kullanıcı: "sadece Türkiye haberleri"): Gündem'e Türkçe
  bağımsız bir iç ses. Besleme yok, site haritası bir gün geride; haberler
  anasayfadaki bölüm bağlantılarından (`ANASAYFA_KAYNAKLARI`: yalnız
  gündem, politika, ekonomi, medya) alınır. Dünya, spor, foto-haber, köşe
  yazıları ve videolar alınmaz (`ATLANAN_BOLUMLER`, `metin_at`). Çizgisi
  muhalif-liberal; abonelik çağrıları özetlerden temizlenir. Bakılıp
  bırakılan: ANKA Haber (besleme yok, haritasındaki haberler 2020; güncel
  haberlerinin olup olmadığı doğrulanamadı).
- Site adı "Dünyadan Notlar", alt başlık "Dünya basınından kısa kısa".
- Yazı tipleri (bkz. `scripts/web/fontlar/BENIOKU.md`): site adı art deco
  Limelight (sayfaya gömülü alt küme, "DN Baslik"); alt başlık Caslon italik
  (gömülü alt küme, "DN Alt"); özet metni Libre Caslon Text 400, haber,
  ilgili haber ve arşiv başlıkları aynı yazı tipinin kalını (700; ikisi de
  "DN Ozet", `dist/fontlar/`). Düğmeler, sekmeler, etiketler bilerek
  cihazın düz yazı tipinde. Özet metninde saydamlık yok; açık temada .1px
  kontur (`--ozet-kontur`), koyu temada yok (.3px "fazla koyu" bulundu).
