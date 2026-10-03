"""dist/ çıktısının üretimi: HTML sayfası, robots.txt, sitemap.xml."""

import base64
import html
import json
import os
import re
import urllib.parse
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from ayarlar import KAYNAKLAR, SITE_URL, TR_SAATI, TURKCE_KAYNAKLAR
from arsiv import referans_zamani
from olaylar import olaylari_grupla
from model import ArsivKaydi, Ceviriler, KaynakBolumu, Makale
from manset import etiket as manset_etiketi
from tarih import AYLAR as _AYLAR, GUNLER as _GUNLER, gun_ay, sira_anahtari, sira_zamani, tarihi_ayristir, tarihi_bicimlendir

# html2canvas satır içi gömülü: translate.goog (otomatik Türkçe çeviri)
# üçüncü taraf bir CDN'den yüklenen <script src="..."> etiketini düzgün
# proxy'lemiyor, bu yüzden "Paylaş" butonu çeviri sürümünde hiç
# çalışmıyordu. Kütüphane depoda vendor'lanıp sayfanın kendi
# <script>'ine gömülerek bu proxy sorunu tamamen atlanıyor.
HTML2CANVAS_DOSYASI = Path(__file__).resolve().parent / "vendor" / "html2canvas.min.js"
# Sayfanın CSS'i ve JS'i scripts/web/ altında gerçek dosyalar; derlemede
# sayfanın içine gömülüyor (translate.goog ayrı yüklenen <script src>/
# <link> dosyalarını düzgün proxy'lemediği için dışarıdan yüklenemiyor).
# JS özellik başına ayrı dosyalarda, bu sırayla birleştiriliyor;
# filtre.js'teki __KATEGORI_VERISI__ derlemede kategori/kaynak verisiyle
# değiştiriliyor.
WEB_KLASORU = Path(__file__).resolve().parent / "web"
JS_DOSYALARI = [
    "tazele.js",  # eskimiş (tarayıcının bellekten gösterdiği) sayfayı yenile
    "ceviri.js",  # "Read in Turkish" bağlantısı, otomatik Türkçe yönlendirme
    "tema.js",  # karanlık tema düğmesi
    "duzen.js",  # döşeme/liste görünümü
    "yazi-boyutu.js",  # A− / A+
    "filtre.js",  # kategori sekmeleri + kaynak menüsü
    "arama.js",  # yeni ve eski haberlerde arama (filtre.js'ten sonra)
    "yeni.js",  # son ziyaretten beri gelen haberlere "yeni" işareti
    "manset.js",  # Manşet sekmesinde açılmamış yeni baskı noktası
    "dinle.js",  # sesli okuma
    "paylas-ozet.js",  # "Özeti paylaş" (kart görüntüsü)
    "paylas-orijinal.js",  # "Orijinal metni paylaş" (Türkçe + orijinal link)
]


# Sitenin adı ve alt başlığı (sayfa başlığı, sekme, paylaşım önizlemesi).
# İngilizce yedek sayfada da Google çevirmesin diye translate="no".
SITE_ADI = "Dünyadan Notlar"
ALT_BASLIK = "Dünya basınından kısa kısa"


def kacir(metin: str) -> str:
    return html.escape(metin, quote=False)


STIL = (WEB_KLASORU / "stil.css").read_text(encoding="utf-8")
# Site adının yazı tipi (Limelight alt kümesi, ~17 KB; bkz.
# web/fontlar/BENIOKU.md). Sayfaya gömülü: dışarıya istek yok, çevrimdışı
# ve translate.goog'da da çalışır.
BASLIK_YAZITIPI = (
    "@font-face{font-family:'DN Baslik';font-display:swap;src:url(data:font/woff2;base64,"
    + base64.b64encode((WEB_KLASORU / "fontlar" / "baslik.woff2").read_bytes()).decode("ascii")
    + ") format('woff2')}"
)
# Alt başlığın yazı tipi: Libre Caslon Text italik, yalnız Türkçe alfabe,
# rakamlar ve temel noktalama (~18 KB; bkz. web/fontlar/BENIOKU.md).
# Site adı gibi sayfaya gömülü.
ALT_BASLIK_YAZITIPI = (
    "@font-face{font-family:'DN Alt';font-style:italic;font-display:swap;src:url(data:font/woff2;base64,"
    + base64.b64encode((WEB_KLASORU / "fontlar" / "alt-baslik.woff2").read_bytes()).decode("ascii")
    + ") format('woff2')}"
)
# Özet metninin ve haber başlıklarının yazı tipi: Libre Caslon Text (New
# Yorker'ın metin yazı tipinin ücretsiz sürümü; bkz. web/fontlar/BENIOKU.md).
# Özet 400, başlık 700 ağırlığında. Her ağırlık ~40 KB olduğu için
# gömülmüyor, dist/fontlar/'a ayrı dosya olarak yazılıp önbellekte kalıyor.
LATIN = "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"
LATIN_EK = "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF"
OZET_YAZITIPLERI = {  # dosya: (ağırlık, unicode-range)
    "ozet-latin.woff2": (400, LATIN),
    "ozet-latin-ext.woff2": (400, LATIN_EK),
    "ozet-kalin-latin.woff2": (700, LATIN),
    "ozet-kalin-latin-ext.woff2": (700, LATIN_EK),
}
YAZITIPI_LISANSLARI = ["baslik-OFL.txt", "ozet-OFL.txt"]
OZET_YAZITIPI = "".join(
    f"@font-face{{font-family:'DN Ozet';font-weight:{agirlik};font-display:swap;"
    f"src:url(fontlar/{dosya}) format('woff2');unicode-range:{aralik}}}"
    for dosya, (agirlik, aralik) in OZET_YAZITIPLERI.items()
)


# Paylaş butonlarının etiketi: metin, bir SVG'nin içinde CSS maskesi
# olarak çiziliyor — sayfada gerçek bir metin düğümü olmadığı için
# translate.goog butona dokunmayı yutamıyor, maske olduğu için de renk
# (currentColor) temayla birlikte değişiyor. textLength, farklı cihaz
# fontlarında metnin kutuya hep aynı genişlikte sığmasını sağlıyor.
def _etiket_maskesi(sinif: str, metin: str, metin_genisligi: int) -> str:
    genislik = 19 + metin_genisligi + 1
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {genislik} 16'>"
        "<g fill='none' stroke='black' stroke-width='2.2' stroke-linecap='round' "
        "stroke-linejoin='round' transform='translate(0 1) scale(.583)'>"
        "<path d='M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7'/>"
        "<polyline points='16 6 12 2 8 6'/><line x1='12' y1='2' x2='12' y2='15'/></g>"
        f"<text x='19' y='12.5' textLength='{metin_genisligi}' "
        "font-family='Helvetica,Arial,Roboto,sans-serif' font-size='12.5' "
        f"font-weight='600'>{metin}</text></svg>"
    )
    adres = "data:image/svg+xml," + urllib.parse.quote(svg)
    return (
        f".{sinif}{{width:{genislik}px;"
        f"-webkit-mask-image:url(\"{adres}\");mask-image:url(\"{adres}\")}}"
    )


# Kartlardaki kaynak linki ("bbc.co.uk →") da metin değil, kaynağa özel
# bir SVG maskesi, paylaş butonlarındaki gibi (bu linkte çeviri balonu
# görüldüğü bildirildi; maske yöntemi paylaş butonlarında çalışıyor). Genişlik Helvetica/Arial karakter
# genişliklerinden (1000 birimlik AFM değerleri) hesaplanıyor;
# textLength küçük font farklarını dengeliyor. Boyutlar em cinsinden,
# A−/A+ ile büyüyüp küçülüyor.
_HELVETICA = {
    **dict.fromkeys("abdeghnopqu0123456789", 556), **dict.fromkeys("cksvxyz", 500),
    **dict.fromkeys("fijlt.", 278), "i": 222, "j": 222, "l": 222, "m": 833, "r": 333, "w": 722, "-": 333,
}


def kaynak_sinifi(kaynak: str) -> str:
    return "src-" + re.sub(r"[^a-z0-9]+", "-", kaynak.lower()).strip("-")


def _kaynak_maskesi(kaynak: str) -> str:
    boyut = 12.5
    metin_genisligi = round(sum(_HELVETICA.get(h, 556) for h in kaynak.lower()) * boyut / 1000, 1)
    ok_x = metin_genisligi + 4
    genislik = round(ok_x + 10, 1)
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {genislik} 16'>"
        f"<text x='0' y='12' textLength='{metin_genisligi}' "
        f"font-family='Helvetica,Arial,Roboto,sans-serif' font-size='{boyut}'>{html.escape(kaynak)}</text>"
        f"<path d='M{ok_x} 8.5h8m-3-3 3 3-3 3' fill='none' stroke='black' stroke-width='1.2' "
        "stroke-linecap='round' stroke-linejoin='round'/></svg>"
    )
    adres = "data:image/svg+xml," + urllib.parse.quote(svg)
    return (
        f".{kaynak_sinifi(kaynak)}{{width:{round(genislik / boyut, 3)}em;"
        f"-webkit-mask-image:url(\"{adres}\");mask-image:url(\"{adres}\")}}"
    )


KAYNAK_LINKI_STIL = "".join(_kaynak_maskesi(ad) for ad in dict.fromkeys(ad for _, ad, _ in KAYNAKLAR))


PAYLAS_STIL = (
    ".paylas-satiri .paylas{margin-top:.5rem}"
    ".etiket-resmi{display:block;height:16px;background-color:currentColor;"
    "-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;"
    "-webkit-mask-size:100% 100%;mask-size:100% 100%}"
    + _etiket_maskesi("etiket-ozet", "Özeti paylaş", 72)
    + _etiket_maskesi("etiket-orijinal", "Orijinal metni paylaş", 120)
    + _etiket_maskesi("etiket-kopyalandi", "Bağlantı kopyalandı", 116)
)


# Aynı olayı haberleştiren diğer kaynaklar (bkz. olaylar.py): öncü kartın
# altında kapalı bir liste. Başlıklar içerik olduğu için metin (Google
# çeviriyor); kaynak adı ve saat data-etiket ile çiziliyor.
def _ilgili_html(ilgili: list[Makale], ceviri: Ceviriler) -> str:
    if not ilgili:
        return ""
    satirlar = []
    for r in ilgili:
        bilgi = r.kaynak
        if r.tarih:
            bilgi += " · " + ("~" if r.tahmini else "") + tarihi_bicimlendir(r.tarih)
        satirlar.append(
            f'<li><a href="{html.escape(r.url)}" target="_blank" rel="noopener">{kacir(ceviri.baslik(r.url, r.baslik))}</a>'
            f'<span class="ilgili-bilgi" data-etiket="{html.escape(bilgi)}"></span></li>'
        )
    etiket = f"Bu olayı {len(ilgili)} kaynak daha haberleştirdi"
    return (
        f'<details class="ilgili">\n    <summary data-etiket="{etiket}"></summary>\n    <ul>'
        + "".join(satirlar) + "</ul>\n  </details>\n  "
    )


# " · güncellendi 17:30" (başka gündeyse "29.09 17:30"): içerik
# değiştiği için haber öne alındıysa (bkz. takip.py) ve bu an yayın
# tarihinden sonraysa.
def _guncelleme_notu(m: Makale, turkce: bool) -> str:
    if not m.guncellendi or sira_anahtari(m.guncellendi) <= sira_anahtari(m.tarih):
        return ""
    guncel = sira_anahtari(m.guncellendi).astimezone(TR_SAATI)
    yayin = tarihi_ayristir(m.tarih)
    ayni_gun = yayin is not None and yayin.tzinfo is not None and yayin.astimezone(TR_SAATI).date() == guncel.date()
    zaman = guncel.strftime("%H:%M") if ayni_gun else f"{gun_ay(guncel)} {guncel:%H:%M}"
    return f" · {'güncellendi' if turkce else 'updated'} {zaman}"


def _kart_html(
    kategori: str, m: Makale, ceviri: Ceviriler, turkce: bool,
    ilgili: list[Makale] | None = None, grupta: bool = False,
) -> str:
    gorsel_html = (
        f'<img src="{kacir(m.gorsel)}" alt="" loading="lazy" referrerpolicy="no-referrer">'
        if m.gorsel
        else ""
    )
    # Kaynak adı başlığın hemen altında da görünsün diye tarih satırında
    # (kartın altındaki "kaynak →" linki hâlâ duruyor).
    if m.tarih:
        # tahmini: gerçek yayın saati bulunamadı, gösterilen bizim bu
        # haberi ilk gördüğümüz an (bkz. tarih.py). "~" ve title ile gerçek
        # yayın saatiyle karışmasın diye işaretleniyor.
        on_ek = "~" if m.tahmini else ""
        baslik_ozniteligi = (
            ' title="İlk görüldüğü an; kaynağın gerçek yayın saati bulunamadı"' if m.tahmini else ""
        )
        tarih_metni = f"{on_ek}{tarihi_bicimlendir(m.tarih)}{_guncelleme_notu(m, turkce)} · {m.kaynak}"
        tarih_html = (
            f'<p class="tarih{" tahmini" if m.tahmini else ""}"{baslik_ozniteligi}'
            f' data-etiket="{html.escape(tarih_metni)}"></p>'
        )
    else:
        tarih_html = f'<p class="tarih" data-etiket="{html.escape(m.kaynak)}"></p>'
    # Paylaş butonlarında gerçek metin yok, etiket CSS maskesiyle çizilen
    # bir görsel (bkz. PAYLAS_STIL): translate.goog metin içeren butonlara
    # dokunulduğunda tıklamayı geçirmek yerine kendi çeviri balonunu
    # gösterip tıklamayı yutuyordu. data-url: translate.goog sayfadaki
    # <a href>'leri kendi adreslerine çeviriyor, "Orijinal metni paylaş"
    # haberin gerçek adresine ihtiyaç duyduğu için dokunulmayan bir
    # öznitelikte saklanıyor.
    # grupta: bu haber başka bir kaynağın kartında "aynı olay" olarak
    # listeleniyor; "Tüm kaynaklar"da gizli, kendi kaynağı seçilince görünür.
    grup_ozniteligi = ' data-grupta="1"' if grupta else ""
    # Sıralama anı (yayın ya da güncellenme; tahmini tarihte ilk görülme),
    # "yeni" işareti için (bkz. yeni.js).
    zaman = sira_zamani(m).timestamp()
    zaman_ozniteligi = f' data-zaman="{int(zaman)}"' if zaman > 0 else ""
    # Türkçe sayfada çevirisi alınamamış haber İngilizce kalır; lang="en"
    # ile işaretleniyor (sesli okuma İngilizce sesi seçsin diye).
    if turkce and not ceviri.cevrildi_mi(m.url):
        grup_ozniteligi += ' lang="en"'
    # Türkçe kaynak: "Orijinal metni paylaş" çeviri bağlantısı eklemesin,
    # sesli okuma Türkçe okusun. İngilizce (yedek) sayfada translate.goog
    # bu kartı İngilizce sanıp bozmasın diye çeviri dışı bırakılıyor.
    if m.kaynak in TURKCE_KAYNAKLAR:
        grup_ozniteligi += ' data-dil="tr"' + ("" if turkce else ' lang="tr" translate="no"')
    return f"""<article{zaman_ozniteligi} data-kategori="{kacir(kategori)}" data-kaynak="{kacir(m.kaynak)}" data-url="{kacir(m.url)}"{grup_ozniteligi}>
  <h3><a href="{kacir(m.url)}" target="_blank" rel="noopener">{kacir(ceviri.baslik(m.url, m.baslik))}</a></h3>
  {tarih_html}
  {gorsel_html}
  <details>
    <summary data-etiket="Devamını oku"></summary>
    <p>{kacir(ceviri.ozet(m.url, m.ozet))}</p>
  </details>
  {_ilgili_html(ilgili or [], ceviri)}<button type="button" class="dinle" data-etiket="&#128266; Dinle"></button>
  <a class="src {kaynak_sinifi(m.kaynak)}" href="{kacir(m.url)}" target="_blank" rel="noopener" aria-label="{html.escape(m.kaynak)}"></a>
  <div class="paylas-satiri">
    <button type="button" class="paylas paylas-ozet" title="Özeti paylaş" aria-label="Özeti paylaş"><span class="etiket-resmi etiket-ozet"></span></button>
    <button type="button" class="paylas paylas-orijinal" title="Orijinal metni paylaş" aria-label="Orijinal metni paylaş"><span class="etiket-resmi etiket-orijinal"></span></button>
  </div>
</article>"""


# Gün başlıkları data-etiket ile çiziliyor (Google çevirmiyor), bu yüzden
# doğrudan Türkçe (adlar tarih.py'de).


# "Older news" görünümü: günlere ayrılmış başlık listesi. Her satır
# kategori/kaynak menüsüyle süzülebilsin diye kartlarla aynı data-
# öznitelikleri taşıyor. Başlık linki orijinal habere gidiyor; çeviri
# sayfasında translate.goog bu linki kendisi Türkçe sürüme çeviriyor.
def _arsiv_html(eski: list[ArsivKaydi], ceviri: Ceviriler, turkce: bool,
                kaynak: str = "") -> tuple[str, str]:
    """(sayfadaki kısım, ayrı dosyanın içeriği). kaynak verilirse günlerin
    listesi ayrı dosyaya gider (eski.html; ~1 MB, sayfanın yarısı) ve
    tarayıcı onu "Eski haberler"e ya da aramaya ilk başvuruda indirir
    (filtre.js arsiviYukle); verilmezse liste sayfada."""
    gunler: dict = {}
    for k in eski:
        zaman = tarihi_ayristir(k.tarih)
        if zaman is not None and zaman.tzinfo is not None:
            yerel = zaman.astimezone(TR_SAATI)
            gun, saat = yerel.date(), ("~" if k.tahmini else "") + yerel.strftime("%H:%M")
        else:
            gun, saat = referans_zamani(k).astimezone(TR_SAATI).date(), ""
        gunler.setdefault(gun, []).append((saat, k))

    bolumler = []
    for gun in sorted(gunler, reverse=True):
        satirlar = []
        for saat, k in gunler[gun]:
            bilgi = f"{saat} · {k.kaynak}" if saat else k.kaynak
            satirlar.append(
                f'<li data-kategori="{html.escape(k.kategori)}" data-kaynak="{html.escape(k.kaynak)}">'
                f'<a href="{html.escape(k.url)}" target="_blank" rel="noopener">{kacir(ceviri.baslik(k.url, k.baslik))}</a>'
                f' <span class="arsiv-bilgi" data-etiket="{html.escape(bilgi)}"></span></li>'
            )
        baslik = f"{_GUNLER[gun.weekday()]}, {gun.day} {_AYLAR[gun.month - 1]}"
        bolumler.append(
            f'<section class="arsiv-gun"><h2 lang="tr" data-etiket="{baslik}"></h2><ul>\n' + "\n".join(satirlar) + "\n</ul></section>"
        )
    bos = (
        "Bu seçim için henüz eski haber yok. Güncel listeden düşen haberler burada 7 gün görünür."
        if turkce
        else "No older stories for this selection yet. Stories that drop off the latest list appear here for 7 days."
    )
    liste = "\n".join(bolumler)
    oznitelik = f' data-kaynak="{html.escape(kaynak)}"' if kaynak else ""
    return (
        f'<div class="arsiv" id="arsiv"{oznitelik} hidden>\n'
        + ("" if kaynak else liste)
        + f'\n<p class="arsiv-bos" hidden>{bos}</p>\n</div>'
    ), (liste if kaynak else "")


# Kartların en az bu oranı Türkçeye çevrildiyse sayfa Türkçe üretilir;
# değilse (Google çevirisi uzun süre alınamadıysa) eskisi gibi İngilizce
# üretilip okura translate.goog üzerinden çevrilir. Çevrilemeyen yeni
# haberler zaten gizlendiği için eşik düşük: Google'ın birkaç saatlik
# kesintisinde (429) site Türkçe kalır, yalnız yeni haberler gecikir
# (kullanıcı tercihi). 0.9 iken bir saatlik kesinti sayfayı İngilizceye
# düşürmeye yetiyordu.
TURKCE_ESIGI = 0.5


# "Eski haberler" listesinin ayrı dosyası (bkz. _arsiv_html).
ARSIV_PARCASI = "eski.html"


# Manşet sekmesinin adı (kategorilerin en solunda; sayfa yine ilk
# kategoriyle açılır).
MANSET_SEKMESI = "Manşet"


def _manset_kaynaklari(o: dict) -> str:
    return " · ".join(
        f'<a href="{kacir(k["url"])}" target="_blank" rel="noopener">{kacir(k["ad"])}</a>' for k in o["kaynaklar"]
    )


def _manset_ust(o: dict) -> str:
    """"Manşet · 3 kaynak" ya da "Manşet · Türkiye · 1 kaynak"."""
    tur = " · Türkiye" if o.get("tur") == "turkiye" else ""
    return f"Manşet{tur} · {len(o['kaynaklar'])} kaynak"


def _manset_html(ozet: dict | None, onceki: list[dict]) -> str:
    """Manşet (bkz. manset.py): son baskının derlemeleri ve önceki
    baskılar, kendi sekmesinde. Kutular <article>: Dinle ve Özeti paylaş
    kartlardaki gibi çalışır (data-dil="tr": Türkçe okunur). Etiketler
    data-etiket ile çiziliyor (Google çevirmiyor); metin Türkçe sayfada
    zaten Türkçe olduğundan yalnız Türkçe üretimde konur."""
    kutular = []
    for o in (ozet or {}).get("olaylar", []):
        gorsel = (
            f'<img src="{kacir(o["gorsel"])}" alt="" loading="lazy" referrerpolicy="no-referrer">'
            if o.get("gorsel") else ""
        )
        turkiye = " manset-turkiye" if o.get("tur") == "turkiye" else ""
        kutular.append(
            f'<article class="manset-kutu{turkiye}" data-dil="tr">{gorsel}'
            f'<p class="manset-ust" data-etiket="{html.escape(_manset_ust(o))}"></p>'
            f'<h3>{kacir(o["baslik"])}</h3><p class="ozet-metni">{kacir(o["ozet"])}</p>'
            f'<p class="manset-kaynaklar">{_manset_kaynaklari(o)}</p>'
            '<button type="button" class="dinle" data-etiket="&#128266; Dinle"></button>'
            '<div class="paylas-satiri"><button type="button" class="paylas paylas-ozet" title="Özeti paylaş"'
            ' aria-label="Özeti paylaş"><span class="etiket-resmi etiket-ozet"></span></button></div></article>'
        )
    baslik = manset_etiketi(ozet) if ozet else "Son baskıda manşete giren olay yok"
    gecmis = ""
    if onceki:
        bolumler = []
        for b in onceki:
            satirlar = "".join(
                f'<details class="manset-eski"><summary>{kacir(o["baslik"])}</summary>'
                f'<p class="manset-ust" data-etiket="{html.escape(_manset_ust(o))}"></p>'
                f'<p>{kacir(o["ozet"])}</p><p class="manset-kaynaklar">{_manset_kaynaklari(o)}</p></details>'
                for o in b["olaylar"]
            )
            bolumler.append(f'<h4 data-etiket="{html.escape(manset_etiketi(b))}"></h4>{satirlar}')
        gecmis = (
            f'<details class="manset-gecmis"><summary data-etiket="Önceki baskılar ({len(onceki)})"></summary>'
            + "".join(bolumler) + "</details>\n"
        )
    return (
        f'<section class="manset" id="manset" data-kategori="{MANSET_SEKMESI}" hidden>\n'
        f'<h2 data-etiket="{html.escape(baslik)}"></h2>\n'
        + "\n".join(kutular) + "\n" + gecmis + "</section>\n"
    )


def sayfa_olustur(
    kategoriler: dict[str, list[KaynakBolumu]],
    eski: list[ArsivKaydi] | None = None,
    ceviri: Ceviriler | None = None,
    gruplar: dict[tuple[str, str], list[Makale]] | None = None,
    manset: dict | None = None,
    onceki_baskilar: list[dict] | None = None,
    arsiv_klasoru: Path | None = None,
) -> str:
    eski = eski or []
    makaleler = [m for bolumler in kategoriler.values() for b in bolumler for m in b.makaleler]
    turkce = bool(
        ceviri and makaleler
        and sum(ceviri.cevrildi_mi(m.url) for m in makaleler) >= TURKCE_ESIGI * len(makaleler)
    )
    ingilizceler = ceviri.ingilizceler if ceviri else {}
    if turkce:
        # Çevirisi alınamamış (Google o çalıştırmada hata verdiği için
        # çevrilemeyen yeni) haberler bu yayında gösterilmez: Türkçe
        # sayfanın en üstünde İngilizce kartlar çıkıyordu. Kaybolmazlar,
        # bir sonraki çalıştırmada çevrilip gelirler.
        kategoriler = {
            kat: [replace(b, makaleler=[m for m in b.makaleler if ceviri.cevrildi_mi(m.url)]) for b in bolumler]
            for kat, bolumler in kategoriler.items()
        }
    else:
        ceviri = Ceviriler()
    kategori_adlari = list(kategoriler.keys())
    ilk_kategori = kategori_adlari[0] if kategori_adlari else ""

    # Kategori sekmeleri: hangisine tıklanırsa JS o kategorinin kartlarını
    # gösterip kaynak filtre düğmelerini (aşağıdaki KATEGORI_VERISI'nden)
    # yeniden kurar.
    kategori_nav_dugmeleri = []
    for i, kat in enumerate(kategori_adlari):
        aktif = " aktif" if i == 0 else ""
        kategori_nav_dugmeleri.append(
            f'<button type="button" class="kategori-buton{aktif}" data-kategori="{kacir(kat)}" data-etiket="{html.escape(kat)}"></button>'
        )
    manset_html = _manset_html(manset, onceki_baskilar or []) if (turkce and (manset or onceki_baskilar)) else ""
    if manset_html:
        kategori_nav_dugmeleri.insert(0, (
            f'<button type="button" class="kategori-buton manset-buton" data-kategori="{MANSET_SEKMESI}"'
            f' data-baski="{html.escape((manset or {}).get("baski", ""))}" data-etiket="{MANSET_SEKMESI}"></button>'
        ))
    kategori_nav = "".join(kategori_nav_dugmeleri)

    # (kategori adı) -> [[kaynak adı, haber sayısı, eski haber sayısı,
    # başka kartta gruplanan haber sayısı], ...] — JS'nin aktif kategoriye
    # ve görünüme (son/eski) göre kaynak menüsünü kurması için.
    eski_sayilari: dict[tuple[str, str], int] = {}
    for k in eski:
        eski_sayilari[(k.kategori, k.kaynak)] = eski_sayilari.get((k.kategori, k.kaynak), 0) + 1
    # Üretimde gruplar olay süzgecinden gelir (bkz. olay_suzgeci.py).
    if gruplar is None:
        gruplar = olaylari_grupla(kategoriler, ingilizceler, TURKCE_KAYNAKLAR)
    gruplananlar = {(kat, r.url) for (kat, _), ilgili in gruplar.items() for r in ilgili}
    grupta_sayilari: dict[tuple[str, str], int] = {}
    for (kat, _), ilgili in gruplar.items():
        for r in ilgili:
            grupta_sayilari[(kat, r.kaynak)] = grupta_sayilari.get((kat, r.kaynak), 0) + 1
    kategori_kaynak_verisi = {
        kat: [
            [b.ad, len(b.makaleler), eski_sayilari.get((kat, b.ad), 0), grupta_sayilari.get((kat, b.ad), 0)]
            for b in bolumler
        ]
        for kat, bolumler in kategoriler.items()
    }

    toplam = 0
    kartlar = []
    bos_mesajlari = []
    for kat, bolumler in kategoriler.items():
        # Bir kategori içindeki tüm kaynakların haberleri tek listede,
        # zamana göre (kaynaktan bağımsız) sıralı.
        tum_makaleler: list[Makale] = []
        for b in bolumler:
            toplam += len(b.makaleler)
            if not b.makaleler:
                # Hiç haberi olmayan kaynak için: o kaynak filtrelendiğinde
                # gösterilecek gizli bir mesaj (JS ile açılır).
                mesaj = (
                    f"{kacir(b.ad)} kaynağından haber alınamadı. <code>{kacir(b.adres)}</code> geçerli bir"
                    " besleme olmayabilir ya da kaynağa geçici olarak erişilemiyor."
                    if turkce
                    else f"No stories could be retrieved from {kacir(b.ad)}. <code>{kacir(b.adres)}</code> "
                    "may not be a valid RSS feed, or the source is temporarily unreachable."
                )
                bos_mesajlari.append(
                    f'<p class="bos" data-kategori="{kacir(kat)}" data-kaynak="{kacir(b.ad)}" hidden>{mesaj}</p>'
                )
            tum_makaleler.extend(b.makaleler)
        tum_makaleler.sort(key=sira_zamani, reverse=True)
        kartlar.extend(
            _kart_html(kat, m, ceviri, turkce, gruplar.get((kat, m.url)), (kat, m.url) in gruplananlar)
            for m in tum_makaleler
        )

    # Eski haberler listesi Türkçe sayfada ayrı dosyada (eski.html); sürüm
    # parametresi tarayıcının eski kopyayı göstermesini önler. İngilizce
    # (yedek) sayfada translate.goog'un çevirmesi için sayfada kalır.
    surum = os.environ.get("GITHUB_RUN_NUMBER") or datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    ayri = arsiv_klasoru is not None and turkce
    arsiv_html, arsiv_listesi = _arsiv_html(eski, ceviri, turkce, f"{ARSIV_PARCASI}?v={surum}" if ayri else "")
    if ayri:
        arsiv_klasoru.mkdir(parents=True, exist_ok=True)
        (arsiv_klasoru / ARSIV_PARCASI).write_text(arsiv_listesi + "\n", encoding="utf-8")
    icerik = (
        manset_html + '<div class="izgara" id="izgara">\n' + "\n".join(kartlar) + "\n</div>\n" + "\n".join(bos_mesajlari)
        + "\n" + arsiv_html
    )

    # Sayfa ilk yüklendiğinde (JS çalışmadan önceki an) sadece ilk kategori
    # görünsün diye — JS zaten aynısını yapıyor ama bu, kısa bir "tüm
    # kategoriler bir anda görünür" titremesini önler.
    ekstra_stil = (
        ".izgara article[data-kategori]{display:none}"
        '.izgara article[data-kategori="' + kacir(ilk_kategori) + '"]{display:block}'
    )

    # Üst ve alt satırlar data-etiket ile çiziliyor (Google çevirmiyor,
    # balon açmıyor), bu yüzden doğrudan Türkçe.
    simdi = datetime.now(timezone.utc).astimezone(TR_SAATI)
    zaman_metni = f"{simdi.day} {_AYLAR[simdi.month - 1]} {simdi.year}, {simdi:%H:%M}"
    # Deploy'un gerçekten güncellendiğini görmek için. SHA tek başına yetmiyor:
    # zamanlayıcı aynı commit'i tekrar tekrar çalıştırdığı için commit
    # değişmeden de yeni deploy oluyor. Çalıştırma numarası her seferinde
    # arttığı için eski/yeni kopya ayrımı footer'dan tek bakışta anlaşılır.
    build = os.environ.get("GITHUB_SHA", "local")[:7]
    calistirma = os.environ.get("GITHUB_RUN_NUMBER")
    if calistirma:
        build = f"{build}#{calistirma}"

    # Türkçe sayfa: lang="tr" ve translate="no" (tarayıcı/Google yeniden
    # çevirmeye kalkmasın); "Read in Turkish" bağlantısı yok. İngilizce
    # (yedek) sayfa: eskisi gibi lang="en", okur translate.goog'a
    # yönlendirilir (bkz. ceviri.js).
    # data-dil: JS'nin baktığı işaret (lang'e bakılmıyor: translate.goog
    # çevirdiği İngilizce sayfanın lang'ini de "tr" yapabiliyor).
    html_ozniteligi = 'lang="tr" translate="no" data-dil="tr"' if turkce else 'lang="en"'
    ust_bilgi = f"{zaman_metni} · {toplam} haber" + ("" if turkce else " ·")
    cevir_linki = "" if turkce else (
        '<a id="cevir-linki" class="cevir" href="https://translate.google.com/translate?sl=en&amp;tl=tr"'
        ' target="_blank" rel="noopener" data-etiket="&#127481;&#127479; Read in Turkish"></a> '
    )
    baslik = f"{SITE_ADI} — {ALT_BASLIK}"
    # Arama sonucundaki açıklama: bilinen kaynak adları ve "Türkçe" aramada
    # eşleşsin diye başta; her çalıştırmada değişen haber sayısı yok.
    aciklama = (
        f"BBC, Al Jazeera, DW, AA ve daha fazlası: {len(KAYNAKLAR)} kaynaktan dünya, bilim, teknoloji, "
        "sanat, gezi ve yemek haberleri Türkçe özetlenip saatte bir güncellenir."
    )
    # Google'ın arama sonucunda site adını doğru göstermesi için (WebSite
    # yapısal verisi). Eski ad alternatif olarak duruyor.
    yapisal_veri = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": SITE_ADI,
            "alternateName": ["World Brief", ALT_BASLIK],
            "url": SITE_URL,
            "inLanguage": "tr",
            "description": aciklama,
        },
        ensure_ascii=False,
    )
    try:
        html2canvas_js = HTML2CANVAS_DOSYASI.read_text(encoding="utf-8")
    except FileNotFoundError:
        html2canvas_js = ""
    html2canvas_etiketi = f"<script>{html2canvas_js}</script>" if html2canvas_js else ""
    uygulama_js = "\n".join((WEB_KLASORU / "js" / ad).read_text(encoding="utf-8") for ad in JS_DOSYALARI)
    uygulama_js = uygulama_js.replace(
        "__KATEGORI_VERISI__", json.dumps(kategori_kaynak_verisi, ensure_ascii=False)
    )
    return f"""<!DOCTYPE html>
<html {html_ozniteligi} data-uretim="{int(simdi.timestamp())}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="google-site-verification" content="2fw9kal9TSUlQlGZdebXp3fpQ4v1C5x5MSbxnbxlv2E">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%93%B0%3C/text%3E%3C/svg%3E">
<title>{kacir(baslik)}</title>
<meta name="description" content="{kacir(aciklama)}">
<link rel="canonical" href="{SITE_URL}">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="simge/simge-180.png">
<meta name="theme-color" content="#fbfaf8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#15151a" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_ADI}">
<meta property="og:locale" content="tr_TR">
<meta property="og:title" content="{kacir(baslik)}">
<meta property="og:description" content="{kacir(aciklama)}">
<meta property="og:url" content="{SITE_URL}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{kacir(baslik)}">
<meta name="twitter:description" content="{kacir(aciklama)}">
<script type="application/ld+json">{yapisal_veri}</script>
{html2canvas_etiketi}
<style>
{BASLIK_YAZITIPI}{ALT_BASLIK_YAZITIPI}{OZET_YAZITIPI}{STIL}</style>
<style>{PAYLAS_STIL}{KAYNAK_LINKI_STIL}</style>
<style>{ekstra_stil}</style>
</head>
<body>
<div class="wrap" id="top">
<div class="kunye" translate="no">
<span class="kunye-simge" aria-hidden="true">&#128240;</span>
<div><h1><a href="./" class="ana-sayfa">{SITE_ADI}</a></h1>
<p class="alt-baslik">{ALT_BASLIK}</p></div>
</div>
<p class="meta"><span data-etiket="{ust_bilgi}"></span> {cevir_linki}<button type="button" id="tema-buton" class="tema-buton" data-etiket="&#127769; Koyu tema"></button> <button type="button" id="duzen-buton" class="tema-buton" data-etiket="&#9776; Liste görünümü"></button> <button type="button" id="yazi-kucult-buton" class="tema-buton" title="Yazıyı küçült" aria-label="Yazıyı küçült" data-etiket="A&minus;"></button> <button type="button" id="yazi-buyut-buton" class="tema-buton" title="Yazıyı büyüt" aria-label="Yazıyı büyüt" data-etiket="A+"></button></p>
<div class="kategori-nav">{kategori_nav}</div>
<div class="gorunum-anahtari">
<button type="button" class="gorunum-buton aktif" data-gorunum="son" aria-pressed="true" data-etiket="Son haberler"></button>
<button type="button" class="gorunum-buton" data-gorunum="eski" aria-pressed="false" data-etiket="Eski haberler"></button>
</div>
<div class="kaynak-cubugu">
<button type="button" class="top-buton" id="top-buton" data-etiket="&#8593; Yukarı"></button>
<div class="kaynak-sarici">
<button type="button" id="kaynak-secici-buton" class="kaynak-secici-buton" aria-haspopup="listbox" aria-expanded="false"><span class="kaynak-secici-etiket" data-etiket="Tüm kaynaklar"></span><span class="ok" data-etiket="&#9662;"></span></button>
<ul id="kaynak-secici-liste" class="kaynak-secici-liste" role="listbox" hidden></ul>
</div>
</div>
{icerik}
<footer data-etiket="Otomatik oluşturuldu · {zaman_metni} · derleme {build}"></footer>
</div>
<script>
{uygulama_js}</script>
</body>
</html>
"""


# Google'ın siteyi taraması ve indekslemesi için: robots.txt taramaya
# izin verip sitemap'in yerini bildiriyor, sitemap.xml de (site tek sayfa
# olduğu için) o tek url'i lastmod'uyla listeliyor. dist/ her çalıştırmada
# sıfırdan üretilip gh-pages'e yazıldığından (bkz. workflow) bu dosyalar
# da her seferinde tazeleniyor.
# Ana ekrana ekleme (telefonda uygulama gibi tam ekran açılır): simgeler
# site adının yazı tipiyle "DN" (web/simge/, bkz. fontlar/BENIOKU.md).
SIMGELER = ("simge-180.png", "simge-192.png", "simge-512.png")
MANIFEST = {
    "name": SITE_ADI,
    "short_name": SITE_ADI,
    "description": ALT_BASLIK,
    "lang": "tr",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "background_color": "#fbfaf8",
    "theme_color": "#8a5a2b",
    "icons": [
        {"src": "simge/simge-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
        {"src": "simge/simge-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
    ],
}


def yan_dosyalari_yaz(klasor: Path) -> None:
    (klasor / "simge").mkdir(parents=True, exist_ok=True)
    for dosya in SIMGELER:
        (klasor / "simge" / dosya).write_bytes((WEB_KLASORU / "simge" / dosya).read_bytes())
    (klasor / "manifest.webmanifest").write_text(json.dumps(MANIFEST, ensure_ascii=False, indent=1), encoding="utf-8")
    (klasor / "fontlar").mkdir(parents=True, exist_ok=True)
    # Lisans metinleri de font dosyalarının yanında yayımlanıyor (OFL şartı).
    for dosya in [*OZET_YAZITIPLERI, *YAZITIPI_LISANSLARI]:
        (klasor / "fontlar" / dosya).write_bytes((WEB_KLASORU / "fontlar" / dosya).read_bytes())
    simdi_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (klasor / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n", encoding="utf-8"
    )
    (klasor / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        f"    <loc>{SITE_URL}</loc>\n"
        f"    <lastmod>{simdi_iso}</lastmod>\n"
        "    <changefreq>hourly</changefreq>\n"
        "  </url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )
