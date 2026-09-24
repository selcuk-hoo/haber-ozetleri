"""Elle değiştirilen ayarlar: kaynaklar, haber sayıları, eşikler."""

from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TR_SAATI = ZoneInfo("Europe/Istanbul")

# Her kayıt: (kategori, kaynak adı, besleme/anasayfa adresi). Sayfa
# kategoriye göre sekmelere ayrılır; her sekmenin kendi "All + kaynak"
# filtresi vardır (bkz. sayfa_olustur).
KAYNAKLAR = [
    # /rss/turkiye "Türkiye" etiketli dar bir alt besleme, günde 1-2
    # haber veriyordu; anasayfaya geçildi ki genel dailysabah.com akışı
    # (besleme_ogeleri anasayfadan duyurulan gerçek beslemeyi bulup
    # tarihe göre sıralıyor) kullanılsın.
    ("Gündem", "dailysabah.com", "https://www.dailysabah.com/"),
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
    # Bilim ve Teknoloji ayrı sekmelere bölündü: kitleleri farklı
    # (biri araştırma/keşif, diğeri ürün/şirket haberleri). TechCrunch,
    # Verge ile aynı büyük şirket duyurularını (ör. OpenAI, Apple)
    # işleyebildiği için haberlerin tekrar tekrar çıkma riski var —
    # bilinçli olarak kabul edildi.
    ("Teknoloji", "bbc.co.uk", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("Teknoloji", "theverge.com", "https://www.theverge.com/rss/index.xml"),
    ("Teknoloji", "techcrunch.com", "https://techcrunch.com/feed/"),
    # ScienceDaily ve Science News'ün doğrudan besleme adresleri web
    # aramasıyla bulundu, gerçek çalıştırmada ikisi de 10'ar haber verdi.
    # Bilim Teknik (TÜBİTAK) denendi ama besleme bulunamadı (0 sonuç),
    # kaldırıldı.
    ("Bilim", "sciencedaily.com", "https://www.sciencedaily.com/rss/all.xml"),
    ("Bilim", "sciencenews.org", "https://www.sciencenews.org/feed"),
    ("Sanat & Kültür", "bbc.co.uk", "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"),
    ("Sanat & Kültür", "theguardian.com", "https://www.theguardian.com/culture/rss"),
    # Japan Times'ın görselleri translate.goog üzerinden açılan çeviri
    # sürümünde yüklenmiyordu (görsel adresinin kendisi doğru ve
    # ulaşılabilir, ama Google'ın çeviri proxy'si üçüncü taraf CDN'sinden
    # görseli aktaramıyor) — kullanıcı görselleri kaybetmek yerine
    # kaynağı değiştirmeyi tercih etti. SCMP zaten Gündem'de kullanılıyor
    # ve sorunsuz çalışıyor; aynı domain'in kültür/yaşam tarzı sayfası
    # kullanıldı.
    ("Sanat & Kültür", "scmp.com", "https://www.scmp.com/lifestyle/arts-culture"),
    ("Gezi", "cntraveler.com", "https://www.cntraveler.com/"),
    ("Gezi", "lonelyplanet.com", "https://www.lonelyplanet.com/"),
    ("Yemek", "bonappetit.com", "https://www.bonappetit.com/feed/rss"),
    ("Yemek", "eater.com", "https://www.eater.com/"),
    # Bon Appétit ve Eater çoğunlukla Amerikan restoran sahnesi/tarif
    # geliştirme odaklı; Saveur dünya mutfaklarına ve yemek kültürüne
    # daha geniş bakan bir dergi olduğu için eklendi.
    ("Yemek", "saveur.com", "https://www.saveur.com/feed/"),
]

N = 10  # kaynak başına haber sayısı
# Teknoloji'de sadece 2 kaynak var (BBC + The Verge), bu yüzden N=10 ile
# sekme çok hızlı tazeleniyor/tükeniyor gibi görünüyordu; o kategoride
# kaynak başına daha fazla haber tutulur.
KATEGORI_SAYISI = {"Teknoloji": 15}
# Kaynağa özel sayı; kategori ayarından (KATEGORI_SAYISI) önce gelir.
# Burada, sayfada daha az yer kaplaması istenen kaynaklar kısılıyor.
KAYNAK_SAYISI = {"cnn.com": 5}
K = 5  # özet cümle sayısı
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
