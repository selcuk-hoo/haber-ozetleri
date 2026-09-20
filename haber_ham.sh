#!/bin/bash
# ============================================================
# haber_ham.sh — yapay zekasız haber özeti (çıkarımsal), HTML çıktı
#
# Haberin ilk k cümlesini alır. Gazetecilikteki ters piramit
# kuralı gereği bu cümleler zaten haberin özüdür.
# Model kullanmaz, saniyeler içinde biter.
#
# Sayfa lang="en" olarak işaretlenir; tarayıcı Türkçeye çevirmeyi önerir.
# Tarama başlar başlamaz sayfa Chromium'da açılır ve doldukça
# kendini yeniler; tarama bitince yenileme durur.
#
# Gereksinim: trafilatura   (pip install trafilatura --break-system-packages)
#
# Kullanım:
#   ./haber_ham.sh                 # tara, aç, doldur
#   ./haber_ham.sh -n 20 -k 2      # kaynak başına 20 haber, 2 cümle
#   ./haber_ham.sh -o /yol/sayfa.html
#   ./haber_ham.sh -f https://.../rss.xml
#   ./haber_ham.sh -s              # tarayıcıda açma
# ============================================================

set -u
export PATH="$HOME/.local/bin:$PATH"

KAYNAKLAR="
https://www.dailysabah.com/rss/turkiye
https://feeds.bbci.co.uk/news/world/rss.xml
https://www.aljazeera.com/xml/rss/all.xml
https://rss.dw.com/rdf/rss-en-world
https://www.france24.com/en/rss
https://www.themoscowtimes.com/
"

N=10
K=5
CIKTI="$HOME/taramalar/haber/haber_$(date +%F).html"
AC=1

while getopts "n:k:o:f:sh" opt; do
    case "$opt" in
        n) N="$OPTARG" ;;
        k) K="$OPTARG" ;;
        o) CIKTI="$OPTARG" ;;
        f) KAYNAKLAR="$OPTARG" ;;
        s) AC=0 ;;
        h) sed -n '2,26p' "$0"; exit 0 ;;
        *) exit 1 ;;
    esac
done

command -v trafilatura >/dev/null || {
    echo "trafilatura bulunamadı. Kurulum:" >&2
    echo "  pip install trafilatura --break-system-packages" >&2
    exit 1
}

bildir() { command -v notify-send >/dev/null && notify-send "Haber taraması" "$1"; }

tarayici_bul() {
    for b in chromium chromium-browser google-chrome-stable google-chrome brave-browser; do
        command -v "$b" >/dev/null && { echo "$b"; return; }
    done
    echo ""
}

kacir() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

# stdin'deki metnin ilk k cümlesini tek paragraf olarak basar.
# Cümle sınırı: [.!?] + boşluk + büyük harf/tırnak.
# Bilinen sınır: "U.S. Government", "Dr. Smith" gibi kısaltmalarda
# erken böler — cümle bir kelime kısa çıkar, anlam bozulmaz.
ilk_cumleler() {
    local k="$1"
    tr '\n' ' ' \
      | sed -e 's/  */ /g' \
            -e 's/\([.!?]\)[ ]\+\([A-Z"“(]\)/\1\n\2/g' \
      | grep -v '^[[:space:]]*$' \
      | head -"$k" \
      | awk '{ printf "%s ", $0 } END { print "" }'
}

# --- sayfa iskeleti -----------------------------------------

bas_yaz() {                       # $1 = 1 ise otomatik yenileme açık
    local yenile=""
    [ "$1" = "1" ] && yenile='<meta http-equiv="refresh" content="6">'
cat <<HTML
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
$yenile
<title>News digest</title>
<style>
  :root{
    --bg:#fbfaf8; --card:#fff; --ink:#1c1b19; --soft:#6f6b66;
    --line:#e6e2dc; --accent:#8a5a2b; --warn:#9a5b2a; --warnbg:#fdf3e7;
    --shadow:0 1px 2px rgba(28,27,25,.05);
  }
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]){
      --bg:#15151a; --card:#1d1d23; --ink:#e9e7e3; --soft:#a29e98;
      --line:#2d2d35; --accent:#d69a5e; --warn:#d69a5e; --warnbg:#26201a;
      --shadow:none;
    }
  }
  :root[data-theme="dark"]{
    --bg:#15151a; --card:#1d1d23; --ink:#e9e7e3; --soft:#a29e98;
    --line:#2d2d35; --accent:#d69a5e; --warn:#d69a5e; --warnbg:#26201a;
    --shadow:none;
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth; scroll-padding-top:4.5rem}
  body{
    margin:0; background:var(--bg); color:var(--ink);
    font:16px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    padding:0 16px; -webkit-font-smoothing:antialiased;
  }
  .wrap{max-width:46rem; margin:0 auto; padding:2.4rem 0 5rem}
  h1{font-size:1.65rem; margin:0 0 .35rem; letter-spacing:-.015em}
  .meta{color:var(--soft); font-size:.88rem; margin:0 0 1.6rem}
  .live{
    display:inline-flex; align-items:center; gap:.4rem;
    color:var(--accent); font-weight:500;
  }
  .live::before{
    content:""; width:7px; height:7px; border-radius:50%;
    background:var(--accent); animation:puls 1.4s ease-in-out infinite;
  }
  @keyframes puls{0%,100%{opacity:1}50%{opacity:.25}}
  nav{
    position:sticky; top:0; z-index:5;
    background:color-mix(in srgb, var(--bg) 88%, transparent);
    backdrop-filter:saturate(1.4) blur(8px);
    padding:.75rem 0; border-bottom:1px solid var(--line);
    margin-bottom:1.6rem; display:flex; flex-wrap:wrap; gap:.35rem .85rem;
  }
  nav a{
    color:var(--soft); text-decoration:none; font-size:.83rem;
    white-space:nowrap; transition:color .15s;
  }
  nav a:hover{color:var(--accent)}
  h2{
    font-size:.78rem; text-transform:uppercase; letter-spacing:.1em;
    color:var(--soft); font-weight:600;
    margin:2.5rem 0 .9rem; padding-bottom:.4rem;
    border-bottom:1px solid var(--line);
    display:flex; justify-content:space-between; align-items:baseline; gap:1rem;
  }
  h2 .adet{text-transform:none; letter-spacing:0; font-weight:400; opacity:.8}
  article{
    background:var(--card); border:1px solid var(--line);
    border-radius:11px; padding:1.05rem 1.2rem 1.1rem; margin-bottom:.75rem;
    box-shadow:var(--shadow); transition:border-color .15s, transform .15s;
  }
  article:hover{border-color:var(--accent); transform:translateY(-1px)}
  article h3{font-size:1.05rem; line-height:1.38; margin:0 0 .5rem; font-weight:600}
  article h3 a{color:var(--ink); text-decoration:none}
  article h3 a:hover{color:var(--accent)}
  article p{margin:0; color:var(--ink); opacity:.85; font-size:.97rem}
  .src{
    display:inline-block; margin-top:.75rem; font-size:.77rem;
    color:var(--soft); text-decoration:none; letter-spacing:.01em;
  }
  .src:hover{color:var(--accent)}
  .bos{
    background:var(--warnbg); border:1px solid var(--line);
    border-left:3px solid var(--warn);
    border-radius:8px; padding:.85rem 1rem; font-size:.9rem; color:var(--warn);
  }
  .bos code{
    font:.85em/1 ui-monospace,SFMono-Regular,Menlo,monospace;
    background:rgba(127,127,127,.14); padding:.15em .4em; border-radius:4px;
  }
  footer{
    margin-top:3rem; padding-top:1.2rem; border-top:1px solid var(--line);
    color:var(--soft); font-size:.8rem;
  }
  @media (max-width:520px){
    .wrap{padding-top:1.4rem} h1{font-size:1.35rem}
    article{padding:.9rem 1rem}
  }
</style>
</head>
<body>
<div class="wrap">
HTML
}

son_yaz() {                        # $1 = 1 ise hâlâ sürüyor
    if [ "$1" = "1" ]; then
        printf '<footer>Tarama sürüyor…</footer>\n'
    else
        printf '<footer>Tamamlandı · %s</footer>\n' "$(date +%H:%M:%S)"
    fi
    printf '</div>\n</body>\n</html>\n'
}

# Baş + biriken parçalar + son  →  çıktı dosyası
sayfayi_bas() {                    # $1 = 1 ise sürüyor (yenileme açık)
    {
        bas_yaz "$1"
        printf '<h1>News digest</h1>\n'
        if [ "$1" = "1" ]; then
            printf '<p class="meta"><span class="live">tarama sürüyor</span> · ilk %s cümle · modelsiz</p>\n' "$K"
        else
            printf '<p class="meta">%s · ilk %s cümle · modelsiz · %s haber</p>\n' \
                   "$(date '+%d.%m.%Y %H:%M')" "$K" "$TOPLAM"
        fi
        printf '<nav>'
        for f in $KAYNAKLAR; do
            s=$(echo "$f" | awk -F/ '{print $3}')
            printf '<a href="#%s">%s</a>' "$s" "$s"
        done
        printf '</nav>\n'
        cat "$FRAG"
        son_yaz "$1"
    } > "$CIKTI"
}

# --- tarama -------------------------------------------------

FRAG=$(mktemp)
TOPLAM=0
trap 'rm -f "$FRAG"' EXIT

mkdir -p "$(dirname "$CIKTI")"
bildir "Haber taraması başlatılıyor"
sayfayi_bas 1

if [ "$AC" -eq 1 ]; then
    TARAYICI=$(tarayici_bul)
    if [ -n "$TARAYICI" ]; then
        "$TARAYICI" --new-window "file://$CIKTI" >/dev/null 2>&1 &
    else
        xdg-open "$CIKTI" >/dev/null 2>&1 &
    fi
fi

for feed in $KAYNAKLAR; do
    site=$(echo "$feed" | awk -F/ '{print $3}')
    printf '<h2 id="%s">%s<span class="adet" id="c-%s"></span></h2>\n' \
           "$site" "$site" "$site" >> "$FRAG"
    sayfayi_bas 1

    sayac=0
    while read -r url; do
        [ -z "$url" ] && continue

        raw=$(trafilatura -u "$url" 2>/dev/null)
        [ -z "$raw" ] && continue

        baslik=$(printf '%s' "$raw" | head -1)
        govde=$(printf '%s' "$raw" | tail -n +2 \
                  | sed '/^- Published/d
                         /^- Attribution/d
                         /^Related topics/,$d')
        [ -z "$govde" ] && continue
        [ -z "$baslik" ] && baslik="$url"

        ozet=$(printf '%s' "$govde" | ilk_cumleler "$K")
        [ -z "${ozet// /}" ] && continue

        sayac=$((sayac+1)); TOPLAM=$((TOPLAM+1))
        {
          printf '<article>\n'
          printf '  <h3><a href="%s" target="_blank" rel="noopener">%s</a></h3>\n' \
                 "$(printf '%s' "$url" | kacir)" "$(printf '%s' "$baslik" | kacir)"
          printf '  <p>%s</p>\n' "$(printf '%s' "$ozet" | kacir)"
          printf '  <a class="src" href="%s" target="_blank" rel="noopener">%s &rarr;</a>\n' \
                 "$(printf '%s' "$url" | kacir)" "$site"
          printf '</article>\n'
        } >> "$FRAG"

        sayfayi_bas 1            # sayfa doldukça yenilensin
    done < <(trafilatura --feed "$feed" --list 2>/dev/null | head -"$N")

    if [ "$sayac" -eq 0 ]; then
        printf '<p class="bos">Besleme bulunamadı. <code>%s</code> bir RSS adresi olmayabilir — sitenin RSS bağlantısını bulup <code>KAYNAKLAR</code> listesinde bu satırın yerine yazın.</p>\n' \
               "$(printf '%s' "$feed" | kacir)" >> "$FRAG"
    fi

    # bu kaynağın başlığındaki sayaç yerini doldur
    sed -i "s|<span class=\"adet\" id=\"c-${site}\"></span>|<span class=\"adet\">${sayac} haber</span>|" "$FRAG"
    sayfayi_bas 1
done

sayfayi_bas 0                     # son hâl: yenileme kapalı
bildir "Haber taraması bitti — $TOPLAM haber"
printf 'Bitti: %s  (%d haber)\n' "$CIKTI" "$TOPLAM"
