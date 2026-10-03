"""Elle değiştirilen ayarlar: kaynaklar, haber sayıları, eşikler."""

from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TR_SAATI = ZoneInfo("Europe/Istanbul")

# Her kayıt: (kategori, kaynak adı, besleme/anasayfa adresi). Sayfa
# kategoriye göre sekmelere ayrılır; her sekmenin kendi "All + kaynak"
# filtresi vardır (bkz. sayfa_olustur).
KAYNAKLAR = [
    # Anadolu Ajansı İngilizce, Türkiye beslemesi (günde ~12 haber).
    # "cat=guncel" (son dakika) saatte ~12 haber veriyor ve çoğu diğer
    # kaynaklarla çakışan dünya haberi; bu yüzden Türkiye beslemesi.
    ("Gündem", "aa.com.tr", "https://www.aa.com.tr/en/rss/default?cat=turkiye"),
    ("Gündem", "cnn.com", "https://www.cnn.com/"),
    ("Gündem", "bbc.co.uk", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Gündem", "aljazeera.com", "https://www.aljazeera.com/"),
    ("Gündem", "dw.com", "https://rss.dw.com/rdf/rss-en-world"),
    ("Gündem", "france24.com", "https://www.france24.com/en/rss"),
    ("Gündem", "themoscowtimes.com", "https://www.themoscowtimes.com/rss/news"),
    # Uzakdoğu bakış açısı için: SCMP'nin tam besleme adresi bilinmediği
    # için (diğer anasayfa kaynakları gibi) anasayfadan duyurulan gerçek
    # besleme besleme_ogeleri tarafından otomatik keşfedilip kullanılıyor.
    ("Gündem", "scmp.com", "https://www.scmp.com/"),
    # Euronews'un Türkçe servisi: metni zaten Türkçe olduğu için çevrilmez
    # (bkz. TURKCE_KAYNAKLAR). Besleme dünya, ekonomi, kültür ve gezi
    # haberlerini karışık veriyor (saatte birkaç haber); video sayfaları
    # besleme.ATLANAN_ADRES ile atlanıyor, gezi ve kültür yazıları kendi
    # sekmelerine gidiyor (bkz. HARIC_BESLEMELER).
    ("Gündem", "tr.euronews.com", "https://tr.euronews.com/rss"),
    # Türkiye'yi bağımsız bir dış gözle anlatan Türkçe servisler (AA'nın
    # protokol ağırlıklı Türkiye haberlerine denge; 30.09.2026). Türkçe
    # oldukları için çevrilmezler (TURKCE_KAYNAKLAR).
    ("Gündem", "dw.com/tr", "https://rss.dw.com/rdf/rss-tur-all"),
    ("Gündem", "bbc.com/turkce", "https://feeds.bbci.co.uk/turkce/rss.xml"),
    # T24 (02.10.2026): Türkiye içinden bağımsız çevrimiçi gazete; muhalif-
    # liberal çizgi, spor ve magazin ağırlığı az, abonelik duvarı yok. Besleme
    # YOK (/rss 404) ve site haritası bir gün geriden geliyor; haberler
    # anasayfadaki bağlantılardan alınır (bkz. ANASAYFA_KAYNAKLARI). Köşe
    # yazıları ve videolar alınmaz (ATLANAN_BOLUMLER). Türkçe olduğu için
    # çevrilmez (TURKCE_KAYNAKLAR). Denenip bekletilen: ANKA Haber (besleme
    # yok; güncel haberlerinin sitede olup olmadığı doğrulanamadı).
    ("Gündem", "t24.com.tr", "https://t24.com.tr/"),
    # Az kapsanan bölgeler: Afrika (Euronews'un Afrika kanalı) ve Latin
    # Amerika (Güney Amerika haber ajansı; Falkland haberleri ağırlıklı ama
    # Brezilya, Arjantin, Şili siyasetini de izliyor). Denenip elenenler:
    # The Hindu (abonelik duvarı), Kyodo ve NHK World (besleme alınamadı),
    # Buenos Aires Times (Arjantin iç siyaseti ağırlıklı).
    ("Gündem", "africanews.com", "https://www.africanews.com/feed/rss"),
    ("Gündem", "mercopress.com", "https://en.mercopress.com/rss/"),
    # Bilim ve Teknoloji ayrı sekmelere bölündü: kitleleri farklı
    # (biri araştırma/keşif, diğeri ürün/şirket haberleri). TechCrunch,
    # Verge ile aynı büyük şirket duyurularını (ör. OpenAI, Apple)
    # işleyebildiği için haberlerin tekrar tekrar çıkma riski var —
    # bilinçli olarak kabul edildi.
    ("Teknoloji", "bbc.co.uk", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("Teknoloji", "theverge.com", "https://www.theverge.com/rss/index.xml"),
    ("Teknoloji", "techcrunch.com", "https://techcrunch.com/feed/"),
    # Amerika dışındaki teknoloji hayatı (Çin, Hindistan, Körfez, Afrika…);
    # hafta içi günde bir yazı.
    ("Teknoloji", "restofworld.org", "https://restofworld.org/feed/latest/"),
    # Ars Technica (30.09.2026): bilimle teknolojinin kesiştiği yerde
    # derinlikli yazılar (uzay, enerji, güvenlik, sağlık); günde ~10 yazı,
    # abonelik duvarı yok.
    ("Teknoloji", "arstechnica.com", "https://feeds.arstechnica.com/arstechnica/index"),
    # ScienceDaily ve Science News'ün doğrudan besleme adresleri web
    # aramasıyla bulundu, gerçek çalıştırmada ikisi de 10'ar haber verdi.
    # Bilim Teknik (TÜBİTAK) denendi ama besleme bulunamadı (0 sonuç),
    # kaldırıldı.
    ("Bilim", "sciencedaily.com", "https://www.sciencedaily.com/rss/all.xml"),
    ("Bilim", "sciencenews.org", "https://www.sciencenews.org/feed"),
    # Science News günde 2-3 haber veriyor; Bilim sekmesi yavaş kalıyordu.
    # Phys.org günde onlarca haber (fizik, biyoloji, uzay, yer bilimleri).
    ("Bilim", "phys.org", "https://phys.org/rss-feed/"),
    # Quanta Magazine (30.09.2026): matematik, fizik, biyoloji üzerine uzun
    # açıklayıcı yazılar; haftada birkaç yazı, abonelik duvarı yok.
    # Phys.org basın bülteni ağırlıklı olduğu için sayısı 6'ya indirildi.
    ("Bilim", "quantamagazine.org", "https://www.quantamagazine.org/feed/"),
    # Sanat & Kültür magazinden arındırıldı (kullanıcı isteği): BBC'nin
    # "Entertainment & Arts" beslemesi yerine derinlikli yazıların
    # yayınlandığı BBC Culture (günde ~1 yazı); Guardian'ın müzik/TV/yaşam
    # bölümleri atlanıyor (bkz. ATLANAN_BOLUMLER); Variety (film/TV/müzik
    # sektörü, kırmızı halı) çıkarılıp yerine The Art Newspaper kondu.
    ("Sanat & Kültür", "bbc.com", "https://www.bbc.com/culture/feed.rss"),
    ("Sanat & Kültür", "theguardian.com", "https://www.theguardian.com/culture/rss"),
    # SCMP'nin sanat sayfası 30.09.2026'da çıkarıldı: yazılarının çoğu Hong
    # Kong yereli (konser eleştirileri, sanat mekânları). Japan Times
    # (daha önce görselleri translate.goog'da açılmadığı için çıkarılmıştı)
    # yeniden denendi: metin abonelik duvarında kesiliyor.
    # Düşünce denemeleri (felsefe, tarih, kültür; günde ~1) ve edebiyat
    # dünyası (yazar denemeleri, kitaplardan bölümler; liste yazıları
    # ayıklanıyor). İkisi de ücretsiz.
    ("Sanat & Kültür", "aeon.co", "https://aeon.co/feed.rss"),
    ("Sanat & Kültür", "lithub.com", "https://lithub.com/feed/"),
    # Sanat dünyası haberleri (sergiler, bienaller, müzeler; günde birkaç yazı).
    ("Sanat & Kültür", "theartnewspaper.com", "https://www.theartnewspaper.com/rss.xml"),
    # Euronews Türkçe'nin kültür bölümü (günde 2-3 yazı).
    ("Sanat & Kültür", "tr.euronews.com", "https://tr.euronews.com/rss?level=vertical&name=culture"),
    # Condé Nast Traveler 30.09.2026'da çıkarıldı: kaynağa gidince yazının
    # ancak başı gösterilip abonelik isteniyordu. Yerine Guardian ve BBC'nin
    # gezi bölümleri (ikisi de ücretsiz, günde ~1 yazı).
    ("Gezi", "theguardian.com", "https://www.theguardian.com/travel/rss"),
    ("Gezi", "bbc.com", "https://www.bbc.com/travel/feed.rss"),
    ("Gezi", "lonelyplanet.com", "https://www.lonelyplanet.com/"),
    # Euronews Türkçe'nin gezi bölümü (günde ~1 yazı).
    ("Gezi", "tr.euronews.com", "https://tr.euronews.com/rss?level=vertical&name=travel"),
    # Bon Appétit 30.09.2026'da çıkarıldı (CN Traveler gibi Condé Nast:
    # kaynağa gidince abonelik isteniyordu); yerine kaynak konmadı.
    # Denenen Serious Eats'in güncel yazıları çoğunlukla tarif derlemesi.
    ("Yemek", "eater.com", "https://www.eater.com/"),
    # Eater çoğunlukla Amerikan restoran sahnesi odaklı; Saveur dünya
    # mutfaklarına ve yemek kültürüne daha geniş bakan bir dergi.
    ("Yemek", "saveur.com", "https://www.saveur.com/feed/"),
    # Diğerleri ABD'li ve hafta sonu neredeyse hiç yazmıyor; Guardian'ın
    # yemek bölümü hafta sonu da yayında (tarif, restoran eleştirisi).
    ("Yemek", "theguardian.com", "https://www.theguardian.com/food/rss"),
]

# Metni zaten Türkçe olan kaynaklar: çevrilmeden sayfaya girer (bkz.
# ceviri.py, Cevirmen.turkce_kaynak).
TURKCE_KAYNAKLAR = {"tr.euronews.com", "dw.com/tr", "bbc.com/turkce", "t24.com.tr"}

# Beslemesi olmayan kaynaklar: haber adresleri anasayfadaki bağlantılardan
# alınır (kaynak adı → bağlantı kalıbı; bkz. besleme.anasayfa_baglantilari).
# Tarih her haberin kendi sayfasından okunur. T24: aynı haber hem /haber/
# hem bölüm adresinde duruyor; yalnız Türkiye bölümleri (gündem, politika,
# ekonomi, medya) alınır, /dunya/, /spor/, /foto-haber/ ve köşe yazıları
# alınmaz (kullanıcı: "sadece Türkiye haberleri").
ANASAYFA_KAYNAKLARI = {
    "t24.com.tr": r"(?:https://t24\.com\.tr)?/(?:gundem|politika|ekonomi|medya)/[^\"'#?\s<>]+,\d+",
}

N = 10  # kaynak başına haber sayısı
# Teknoloji'de az kaynak olduğu için N=10 ile sekme çok hızlı
# tazeleniyor/tükeniyor gibi görünüyordu; o kategoride kaynak başına daha
# fazla haber tutulur.
KATEGORI_SAYISI = {"Teknoloji": 15}
# Kaynağa özel sayı; kategori ayarından (KATEGORI_SAYISI) önce gelir.
# Burada, sayfada daha az yer kaplaması istenen kaynaklar kısılıyor.
# TechCrunch günde 20-30 haber yazıyor, çoğu girişimcilik dünyasının iç
# haberi; Teknoloji sekmesini doldurmasın diye 8.
# Rest of World günde bir yazdığı için 6 yazı yaklaşık bir haftayı kapsar.
# AA'nın Türkiye haberleri çoğunlukla protokol; Türkçe servisler ve bölge
# kaynakları Gündem'i fazla uzatmasın diye 5-6.
# (kategori, kaynak) anahtarı yalnız o kategoride geçerli ve kaynak adından
# önce gelir. Gündem'de çok hızlı yazan kaynaklar (SCMP günde ~88, Al
# Jazeera ~54, Euronews ~43 haber) kısıldı: aynı sayıda yerle sayfanın
# üstünü dolduruyor, DW ve Moscow Times gibi az yazanları aşağı itiyorlardı.
KAYNAK_SAYISI = {
    "cnn.com": 5, "techcrunch.com": 8, "restofworld.org": 6,
    "aa.com.tr": 5, "dw.com/tr": 5, "t24.com.tr": 6, "bbc.com/turkce": 5, "africanews.com": 6, "mercopress.com": 5,
    "aeon.co": 5, "lithub.com": 5,
    "phys.org": 6, "quantamagazine.org": 5, "arstechnica.com": 8,
    ("Gündem", "scmp.com"): 6, ("Gündem", "aljazeera.com"): 8, ("Gündem", "tr.euronews.com"): 8,
}
# (kategori, kaynak) -> beslemeler: bu beslemelerdeki yazılar o kategoride
# atlanır. Euronews'un genel beslemesindeki gezi ve kültür yazıları
# Gündem'e değil, yalnız Gezi ve Sanat & Kültür sekmelerine (kendi
# bölüm beslemelerinden) girsin diye.
# (kategori, kaynak) -> adres kalıbı: eşleşen yazılar o kategoride atlanır.
# Guardian'ın kültür beslemesindeki pop müzik, TV ve yaşam tarzı yazıları
# (klasik müzik de /music/ altında olduğu için o da gidiyor; bilinçli).
ATLANAN_BOLUMLER = {
    ("Sanat & Kültür", "theguardian.com"): r"theguardian\.com/(?:music|tv-and-radio|lifeandstyle|thefilter)/",
    # Gündem'de spor, magazin, gezi, TV programı ve başka ülkelerin yerel
    # haberleri (7 günlük arşivde Gündem'in kabaca beşte biri): Al Jazeera
    # spor (%18), CNN spor/magazin/gezi, SCMP Hong Kong yereli (siyaset
    # hariç), yaşam, moda, spor ve sponsorlu "native" yazılar, France 24
    # TV programları (%25).
    ("Gündem", "aljazeera.com"): r"aljazeera\.com/sports/",
    ("Gündem", "cnn.com"): r"cnn\.com/(?:\d{4}/\d\d/\d\d/)?(?:sport|entertainment|style|travel)/",
    ("Gündem", "scmp.com"): r"scmp\.com/(?:news/hong-kong/(?!politics/)|lifestyle/|magazines/|sport/|native/|podcasts/)",
    ("Gündem", "france24.com"): r"france24\.com/en/(?:tv-shows|video|sport)/",
    ("Gündem", "bbc.co.uk"): r"bbc\.co\.uk/sport/",
    # T24'ün köşe yazıları (görüş, haber değil), videoları, dünya ve spor
    # haberleri, fotoğraf galerileri, basın özeti ve kitap sitesi.
    ("Gündem", "t24.com.tr"): r"t24\.com\.tr/(?:yazarlar|video|k24|dunya|spor|foto-haber|basinda-bugun|magazin)/",
    # Saveur'ın ücretli tanıtım yazıları ("Gerçek Prosciutto di Parma
    # PDO'nun Yapımında Neler Var?").
    ("Yemek", "saveur.com"): r"saveur\.com/sponsored-post/",
}
HARIC_BESLEMELER = {
    ("Gündem", "tr.euronews.com"): [
        "https://tr.euronews.com/rss?level=vertical&name=travel",
        "https://tr.euronews.com/rss?level=vertical&name=culture",
    ],
}
K = 5  # özet cümle sayısı
# Deneme/tarif/gezi yazıları bir anı ya da hikâyeyle açılıyor; ilk 5 cümle
# çoğu zaman asıl konuya (tarif, mekân, eser) varmadan bitiyordu. 8 cümle
# örnek yazılarda konuya ulaşıyor; 10'da tarif sitelerinde malzeme
# listesi ve hazırlık adımları başlıyordu. Özet kartta kapalı durduğu için
# sayfa uzamıyor.
KATEGORI_OZET_CUMLE = {"Yemek": 8, "Gezi": 8, "Sanat & Kültür": 8}
# Başlık ve özetleri Google yerine Claude'a çevirtilen kategoriler (bkz.
# claude_ceviri.py; CLAUDE_CODE_OAUTH_TOKEN yoksa Google). Yemek yazıları
# deyim ve mutfak terimiyle dolu; Google kelimesi kelimesine çeviriyordu.
# Gezi'de 40 metinlik karşılaştırmada Google 6,5, Sonnet 8,4 aldı ("less is
# more" → "daha azın gezgin versiyonu daha fazladır", "Italian hot spots"
# → "İtalyan sıcak noktaları"). Her kategorinin talimatı
# claude_ceviri.ALANLAR'da. Sanat & Kültür: Aeon ve Literary Hub'ın
# denemeleriyle Google zorlanıyordu ("Habermas's theory of truth meant he
# changed his mind" → "… fikrini değiştirmesi anlamına geliyordu").
CLAUDE_KATEGORILERI = {"Yemek", "Gezi", "Sanat & Kültür"}
# Claude kategorilerinde Google'la kalan kaynaklar: düz haber dili, Google
# iyi çeviriyor ("Whitney Müzesi'ndeki işçiler grev kararı aldı"); The Art
# Newspaper Sanat & Kültür'ün en çok yazan kaynağı (günde ~11), Claude
# kullanımını ~%40 azaltıyor.
CLAUDE_HARIC_KAYNAKLAR = {("Sanat & Kültür", "theartnewspaper.com")}
# Eater/Saveur gibi kaynakların beslemeleri arada 2021-2024'ten kalma
# "evergreen" tarif/rehber içerikleri de karıştırıyor; bunlar tarihe göre
# doğru sıralanıyor ama bir haber sitesinde yıllar öncesine ait içerik
# görünmesi istenmiyor, bu yüzden bu eşikten eski haberler hiç sayfaya
# eklenmiyor.
ESKI_HABER_ESIGI = timedelta(days=30)
SITE_URL = "https://selcuk-hoo.github.io/haber-ozetleri/"
CIKTI = Path(__file__).resolve().parent.parent / "dist" / "index.html"
# "Older news" görünümü: sayfadan düşen haberlerin başlıkları, yayın
# tarihinden bu kadar süre sonrasına kadar listelenir.
ARSIV_SURESI = timedelta(days=7)
# Arşiv listesi yayınlanan sitenin yanında (gh-pages) duruyor; workflow
# bir önceki yayındaki dosyayı üretimden önce buraya koyuyor.
ARSIV_DOSYASI = CIKTI.parent / "arsiv.json"
# Başlık/özet çevirilerinin önbelleği; arşiv gibi gh-pages'te duruyor.
CEVIRI_DOSYASI = CIKTI.parent / "ceviri.json"
# Haberlerin ilk görülme anı ve içerik imzaları (bkz. takip.py); gh-pages'te.
TAKIP_DOSYASI = CIKTI.parent / "takip.json"
# Süren sorunların sayaçları (bkz. saglik.py); gh-pages'te. Uyarı metni
# yayına girmez, iş akışı onu depoda bir kayıt (issue) olarak açar.
SAGLIK_DOSYASI = CIKTI.parent / "saglik.json"
# Olay süzgecinin kararları (bkz. olay_suzgeci.py); arşiv gibi gh-pages'te.
OLAY_KARARLARI_DOSYASI = CIKTI.parent / "olay_kararlari.json"
# Manşet (bkz. manset.py): son 24 saatin önemli olaylarının derlemesi,
# günde iki baskı.
MANSET_OLAYLARI_DOSYASI = CIKTI.parent / "manset_olaylari.json"
MANSET_DOSYASI = CIKTI.parent / "manset.json"
MANSET_KATEGORI = "Gündem"  # olayların alındığı kategori
MANSET_SAATLERI = (8, 17)  # Türkiye saatiyle baskı saatleri
# Olaylar Claude'a kıstas kıstas (0-10) puanlatılır; puan = kıstasların
# ağırlıklı ortalaması (ağırlıkların toplamı 1). Eşiği geçenler (en çok
# EN_FAZLA) manşete girer; hiçbiri geçmezse o baskıda manşet yok.
MANSET_AGIRLIKLAR = {
    "etki": 0.32,  # etkinin genişliği: kaç ülke, kaç kişi
    "kalicilik": 0.27,  # sonucu haftalar, aylar sürecek mi
    "donum": 0.18,  # süren bir hikâyede yeni aşama mı
    "eylem": 0.13,  # karar/anlaşma mı, açıklama/tehdit mi
    "turkiye": 0.10,  # Türkiye'ye yakınlık
}
MANSET_ESIK = 6.0
MANSET_EN_FAZLA = 3
MANSET_ADAY = 12  # puanlatılan en çok olay (en çok kaynaklılar)
# Türkiye manşeti: Türkçe kaynakların ve AA'nın haberlerinden (tek kaynaklı
# da olabilir) kendi kıstaslarıyla puanlanan en çok MANSET_TR_EN_FAZLA olay.
MANSET_TR_KAYNAKLAR = TURKCE_KAYNAKLAR | {"aa.com.tr"}
MANSET_TR_AGIRLIKLAR = {
    "kapsam": 0.25,  # Türkiye'de kaç kişiyi etkiliyor
    "kalicilik": 0.20,  # sonucu haftalar, aylar sürecek mi
    "kurumsal": 0.20,  # devlet, yargı, demokrasi, ekonomi politikasına etkisi
    "kamuoyu": 0.20,  # toplumda tartışma, sembolik önem
    "dis_iliskiler": 0.15,  # Türkiye'nin dış ilişkilerine, konumuna etkisi
}
# Türkiye puanları daha sıkışık (03.10.2026 denemesi: en yüksek 5,4; T24'e
# erişim engeli, fon soruşturması); 6,0'da hiçbiri geçmiyordu.
MANSET_TR_ESIK = 5.0
MANSET_TR_EN_FAZLA = 1
MANSET_TR_ADAY = 30
MANSET_ARSIV_DOSYASI = CIKTI.parent / "manset_arsiv.json"  # önceki baskılar
MANSET_ARSIV_GUN = 7
SAGLIK_UYARI_DOSYASI = CIKTI.parent.parent / "saglik_uyari.md"
