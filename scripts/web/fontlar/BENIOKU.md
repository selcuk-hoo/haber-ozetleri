# Yazı tipleri

## Başlık

`baslik.woff2`: Limelight (Sorkin Type Co, SIL Open Font License 1.1,
lisans metni `baslik-OFL.txt`) yazı tipinin yalnız Türkçe alfabe, rakamlar
ve temel noktalama işaretlerini içeren alt kümesi (Google Fonts `text=`
parametresiyle alındı). Lisanstaki "Reserved Font Name" maddesi gereği
değiştirilmiş (alt küme) sürüm "Limelight" adıyla değil, `DN Baslik`
adıyla kullanılıyor: hem CSS'te (bkz. `scripts/sayfa.py`, `stil.css`) hem
dosyanın kendi ad tablosunda (fontTools ile name 1/3/4/6 değiştirildi;
telif satırı olduğu gibi duruyor).
Yalnız site adında (`<h1>`) kullanılır; sayfanın içine gömülür, dışarıya
istek atılmaz.

## Alt başlık

`alt-baslik.woff2`: Libre Caslon Text italik (lisans `ozet-OFL.txt`), yalnız
Türkçe alfabe, rakamlar ve temel noktalama işaretleri (fontTools
`pyftsubset` ile). Sayfaya `DN Alt` adıyla gömülü (bkz.
`sayfa.ALT_BASLIK_YAZITIPI`). Alt başlık bu harflerin dışına çıkarsa eksik
harf Charter italikle görünür; o zaman alt küme yeniden üretilmeli.

## Özet metni

`ozet-latin.woff2`, `ozet-latin-ext.woff2`: Libre Caslon Text 400;
`ozet-kalin-latin.woff2`, `ozet-kalin-latin-ext.woff2`: aynı yazı tipinin 700
ağırlığı, haber başlıkları için (The Libre Caslon Text Project Authors, SIL
Open Font License 1.1, lisans metni `ozet-OFL.txt`; ayrılmış font adı yok).
Google Fonts'un latin ve latin-ext dilimleri, değiştirilmeden. Sayfaya gömülmüyor: `sayfa.yan_dosyalari_yaz`
bunları `dist/fontlar/`a kopyalıyor, CSS'te `DN Ozet` adıyla `unicode-range`
ile tanımlı (bkz. `sayfa.OZET_YAZITIPI`).

## Lisans metinleri

`sayfa.yan_dosyalari_yaz` iki lisans metnini de font dosyalarıyla birlikte
`dist/fontlar/`a kopyalıyor (OFL, lisansın fontla birlikte dağıtılmasını
istiyor). Yeni bir yazı tipi eklenirse lisansı `YAZITIPI_LISANSLARI`'na da
eklenmeli.
