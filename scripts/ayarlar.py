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
    # ScienceDaily ve Science News'ün doğrudan besleme adresleri web
    # aramasıyla bulundu, gerçek çalıştırmada ikisi de 10'ar haber verdi.
    # Bilim Teknik (TÜBİTAK) denendi ama besleme bulunamadı (0 sonuç),
    # kaldırıldı.
    ("Bilim", "sciencedaily.com", "https://www.sciencedaily.com/rss/all.xml"),
    ("Bilim", "sciencenews.org", "https://www.sciencenews.org/feed"),
    # Science News günde 2-3 haber veriyor; Bilim sekmesi yavaş kalıyordu.
    # Phys.org günde onlarca haber (fizik, biyoloji, uzay, yer bilimleri).
    ("Bilim", "phys.org", "https://phys.org/rss-feed/"),
    # Sanat & Kültür magazinden arındırıldı (kullanıcı isteği): BBC'nin
    # "Entertainment & Arts" beslemesi yerine derinlikli yazıların
    # yayınlandığı BBC Culture (günde ~1 yazı); Guardian'ın müzik/TV/yaşam
    # bölümleri atlanıyor (bkz. ATLANAN_BOLUMLER); Variety (film/TV/müzik
    # sektörü, kırmızı halı) çıkarılıp yerine The Art Newspaper kondu.
    ("Sanat & Kültür", "bbc.com", "https://www.bbc.com/culture/feed.rss"),
    ("Sanat & Kültür", "theguardian.com", "https://www.theguardian.com/culture/rss"),
    # Japan Times'ın görselleri translate.goog üzerinden açılan çeviri
    # sürümünde yüklenmiyordu (görsel adresinin kendisi doğru ve
    # ulaşılabilir, ama Google'ın çeviri proxy'si üçüncü taraf CDN'sinden
    # görseli aktaramıyor) — kullanıcı görselleri kaybetmek yerine
    # kaynağı değiştirmeyi tercih etti. SCMP zaten Gündem'de kullanılıyor
    # ve sorunsuz çalışıyor; aynı domain'in kültür/yaşam tarzı sayfası
    # kullanıldı.
    ("Sanat & Kültür", "scmp.com", "https://www.scmp.com/lifestyle/arts-culture"),
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
TURKCE_KAYNAKLAR = {"tr.euronews.com", "dw.com/tr", "bbc.com/turkce"}

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
KAYNAK_SAYISI = {
    "cnn.com": 5, "techcrunch.com": 8, "restofworld.org": 6,
    "aa.com.tr": 5, "dw.com/tr": 5, "bbc.com/turkce": 5, "africanews.com": 6, "mercopress.com": 5,
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
# claude_ceviri.ALANLAR'da.
CLAUDE_KATEGORILERI = {"Yemek", "Gezi"}
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
