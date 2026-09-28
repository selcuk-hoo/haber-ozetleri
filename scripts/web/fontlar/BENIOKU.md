# Yazı tipleri

## Başlık

`baslik.woff2`: Limelight (Sorkin Type Co, SIL Open Font License 1.1,
lisans metni `baslik-OFL.txt`) yazı tipinin yalnız Türkçe alfabe, rakamlar
ve temel noktalama işaretlerini içeren alt kümesi (Google Fonts `text=`
parametresiyle alındı). Lisanstaki "Reserved Font Name" maddesi gereği
değiştirilmiş (alt küme) sürüm sayfada "Limelight" adıyla değil,
`DN Baslik` adıyla kullanılıyor (bkz. `scripts/sayfa.py`, `stil.css`).
Yalnız site adında (`<h1>`) kullanılır; sayfanın içine gömülür, dışarıya
istek atılmaz.

## Özet metni

`ozet-latin.woff2`, `ozet-latin-ext.woff2`: Libre Caslon Text 400;
`ozet-kalin-latin.woff2`, `ozet-kalin-latin-ext.woff2`: aynı yazı tipinin 700
ağırlığı, haber başlıkları için (The Libre Caslon Text Project Authors, SIL
Open Font License 1.1, lisans metni `ozet-OFL.txt`; ayrılmış font adı yok).
Google Fonts'un latin ve latin-ext dilimleri, değiştirilmeden. Sayfaya gömülmüyor: `sayfa.yan_dosyalari_yaz`
bunları `dist/fontlar/`a kopyalıyor, CSS'te `DN Ozet` adıyla `unicode-range`
ile tanımlı (bkz. `sayfa.OZET_YAZITIPI`).
