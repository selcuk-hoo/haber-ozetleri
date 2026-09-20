import type { Kaynak } from "./feeds";

export interface Makale {
  baslik: string;
  link: string;
  ozet: string;
  kaynakAdi: string;
}

function kacir(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

const STIL = `
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
  footer{
    margin-top:3rem; padding-top:1.2rem; border-top:1px solid var(--line);
    color:var(--soft); font-size:.8rem;
  }
  @media (max-width:520px){
    .wrap{padding-top:1.4rem} h1{font-size:1.35rem}
    article{padding:.9rem 1rem}
  }
`;

export function sayfayiOlustur(
  kaynaklar: Kaynak[],
  makalelerByKaynak: Map<string, Makale[]>,
  hatalar: Set<string>,
  k: number,
  uretimZamani: Date
): string {
  const toplam = [...makalelerByKaynak.values()].reduce((n, l) => n + l.length, 0);

  const nav = kaynaklar
    .map((k2) => `<a href="#${kacir(k2.ad)}">${kacir(k2.ad)}</a>`)
    .join("");

  const bolumler = kaynaklar
    .map((kaynak) => {
      const makaleler = makalelerByKaynak.get(kaynak.ad) || [];
      const baslik = `<h2 id="${kacir(kaynak.ad)}">${kacir(kaynak.ad)}<span class="adet">${makaleler.length} haber</span></h2>`;

      if (makaleler.length === 0) {
        const neden = hatalar.has(kaynak.ad)
          ? "kaynağa erişilemedi (geçici bir ağ/HTTP hatası olabilir)"
          : "besleme boş döndü ya da geçerli bir RSS adresi değil";
        return (
          baslik +
          `\n<p class="bos">Bu kaynaktan haber alınamadı — ${neden}. <code>${kacir(
            kaynak.url
          )}</code></p>\n`
        );
      }

      const kartlar = makaleler
        .map(
          (m) => `<article>
  <h3><a href="${kacir(m.link)}" target="_blank" rel="noopener">${kacir(m.baslik)}</a></h3>
  <p>${kacir(m.ozet)}</p>
  <a class="src" href="${kacir(m.link)}" target="_blank" rel="noopener">${kacir(kaynak.ad)} &rarr;</a>
</article>`
        )
        .join("\n");

      return baslik + "\n" + kartlar + "\n";
    })
    .join("\n");

  const zamanMetni = uretimZamani.toLocaleString("tr-TR", {
    timeZone: "Europe/Istanbul",
    dateStyle: "short",
    timeStyle: "short",
  });

  return `<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Haber Özeti</title>
<style>${STIL}</style>
</head>
<body>
<div class="wrap">
<h1>Haber Özeti</h1>
<p class="meta">${zamanMetni} · ilk ${k} cümle · Cloudflare Workers AI ile Türkçeye çevrildi · ${toplam} haber</p>
<nav>${nav}</nav>
${bolumler}
<footer>Otomatik üretildi · ${zamanMetni}</footer>
</div>
</body>
</html>
`;
}
