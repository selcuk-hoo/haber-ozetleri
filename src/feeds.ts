export interface Kaynak {
  ad: string;
  url: string;
}

export const KAYNAKLAR: Kaynak[] = [
  { ad: "dailysabah.com", url: "https://www.dailysabah.com/rss/turkiye" },
  { ad: "bbc.co.uk", url: "https://feeds.bbci.co.uk/news/world/rss.xml" },
  { ad: "aljazeera.com", url: "https://www.aljazeera.com/xml/rss/all.xml" },
  { ad: "dw.com", url: "https://rss.dw.com/rdf/rss-en-world" },
  { ad: "france24.com", url: "https://www.france24.com/en/rss" },
  { ad: "themoscowtimes.com", url: "https://www.themoscowtimes.com/rss/news" },
];

export interface HaberOgesi {
  baslik: string;
  link: string;
  govde: string;
}

function etiketAl(blok: string, etiket: string): string {
  const re = new RegExp(`<${etiket}[^>]*>([\\s\\S]*?)</${etiket}>`, "i");
  const m = blok.match(re);
  return m ? m[1] : "";
}

function temizle(html: string): string {
  return html
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/<(script|style)[\s\S]*?<\/\1>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#0?39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function linkAl(blok: string): string {
  const atomHref = blok.match(/<link[^>]*href="([^"]+)"[^>]*\/?>/i);
  const rssLink = blok.match(/<link[^>]*>([\s\S]*?)<\/link>/i);
  const ham = (rssLink && rssLink[1]) || (atomHref && atomHref[1]) || "";
  return temizle(ham);
}

// RSS 2.0 / RDF / Atom beslemesini ayrıştırır, ilk `limit` ögeyi döner.
export function besleyiAyristir(xml: string, limit: number): HaberOgesi[] {
  const ogeler: HaberOgesi[] = [];
  const blokRe = /<item[\s\S]*?<\/item>|<entry[\s\S]*?<\/entry>/gi;
  const bloklar = xml.match(blokRe) || [];

  for (const blok of bloklar.slice(0, limit)) {
    const baslik = temizle(etiketAl(blok, "title"));
    const link = linkAl(blok);
    const govdeHam =
      etiketAl(blok, "content:encoded") ||
      etiketAl(blok, "description") ||
      etiketAl(blok, "summary") ||
      etiketAl(blok, "content");
    const govde = temizle(govdeHam);

    if (baslik && link) ogeler.push({ baslik, link, govde });
  }
  return ogeler;
}

// Metnin ilk k cümlesini tek paragraf olarak döner.
// Cümle sınırı: [.!?] + boşluk + büyük harf/tırnak — haber_ham.sh'deki
// ilk_cumleler() mantığının aynısı. "U.S. Government" gibi kısaltmalarda
// erken bölebilir; anlam bozulmaz, cümle sadece bir kelime kısa çıkar.
export function ilkCumleler(metin: string, k: number): string {
  const duz = metin.replace(/\s+/g, " ").trim();
  if (!duz) return "";
  const parcalar = duz.split(/(?<=[.!?])\s+(?=[A-Z0-9"“(])/).filter(Boolean);
  return parcalar.slice(0, k).join(" ").trim();
}
