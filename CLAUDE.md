# Dünyadan Notlar — bakım rehberi

Dünya basınından haberleri toplayıp Türkçe özetleyen kişisel bir site:
https://selcuk-hoo.github.io/haber-ozetleri/ . Kullanıcıyla Türkçe konuşulur;
kod, yorum ve commit mesajları da Türkçedir. Genel tanıtım README.md'de; bu
dosya değişiklik yaparken izlenecek yolları anlatır.

## Nasıl çalışıyor

- `.github/workflows/haber.yml` yarım saatte bir `scripts/haber_uret.py`'yi
  çalıştırır: beslemeler → makale metni (trafilatura) → özet (ilk N cümle +
  kaynağa özel temizlik) → Google çevirisi → `dist/index.html`.
- Yalnız `main` dalındaki çalıştırmalar yayınlar: `dist/` her seferinde
  `gh-pages` dalına force-push edilir. `gh-pages`'e elle dokunulmaz.
- `gh-pages`'te üretimin kendi durumu da durur: `arsiv.json` (7 günlük eski
  haberler) ve `ceviri.json` (çeviri önbelleği). Her çalıştırma bunları okuyup
  yeniden yazar.
- `scripts/ilk_gorulme.json`'u iş akışı kendisi commit'ler (yalnız main).
  Merge'de bu dosyada çakışma çıkarsa **main'deki hali** alınır.

Modüller: `ayarlar.py` (elle değiştirilen her şey: kaynaklar, sayılar,
yönlendirmeler), `besleme.py`, `ozet.py` (temizlik kuralları), `ceviri.py`,
`olaylar.py` (aynı olayı birleştirme), `arsiv.py`, `tarih.py`, `sayfa.py` +
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
3. `tests/test_ozet.py`'ye **gerçek örnekle** test ekle (başlık dahil).
   Bir kuralın, sıradan metne dokunmadığını gösteren test de yaz.
4. Kural anahtarı `KAYNAKLAR`'daki kaynak adıyla aynı olmalı (test kontrol eder).

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
- Hata olunca: 5 ve 30 sn bekleyip yeniden dener; olmazsa o turda durur,
  metni değişmiş haberde önceki çeviri, hiç çevirisi olmayan yeni haber o
  yayında gösterilmez. Kartların yarısından azı çevrilebildiyse sayfa
  İngilizce üretilir ve okur translate.goog'a yönlenir.

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
- Sanat & Kültür magazinden arındırıldı (Variety çıkarıldı, Guardian'ın
  müzik/TV/yaşam bölümleri atlanıyor, BBC Culture kullanılıyor).
- Yemek'e Lezzet eklenmedi (kullanıcı: tarifler Türk okura yeni değil).
- Site adı "Dünyadan Notlar", alt başlık "Dünya basınından kısa kısa".
- Yazı tipleri (bkz. `scripts/web/fontlar/BENIOKU.md`): site adı art deco
  Limelight (sayfaya gömülü alt küme, "DN Baslik"); alt başlık Caslon italik
  (gömülü alt küme, "DN Alt"); özet metni Libre Caslon Text 400, haber,
  ilgili haber ve arşiv başlıkları aynı yazı tipinin kalını (700; ikisi de
  "DN Ozet", `dist/fontlar/`). Düğmeler, sekmeler, etiketler bilerek
  cihazın düz yazı tipinde. Özet metninde saydamlık yok; açık temada .1px
  kontur (`--ozet-kontur`), koyu temada yok (.3px "fazla koyu" bulundu).
