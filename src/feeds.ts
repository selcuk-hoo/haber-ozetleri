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

function belgeBeslemeMi(metin: string): boolean {
  return /<rss[\s>]|<feed[\s>]|<rdf:rdf[\s>]/i.test(metin) && /<item[\s>]|<entry[\s>]/i.test(metin);
}

// Verilen adresten besleme içeriğini getirir. Adres zaten bir RSS/Atom
// belgesiyse doğrudan onu döner; bir HTML sayfasıysa (ör. site anasayfası)
// <link rel="alternate" type="application/rss+xml|atom+xml"> etiketinden
// gerçek besleme adresini keşfeder — trafilatura'nın `--feed` bayrağının
// yaptığı otomatik keşfin sadeleştirilmiş karşılığı.
export async function feedIcerigiGetir(url: string, basliklar: HeadersInit): Promise<string> {
  const ilkYanit = await fetch(url, { headers: basliklar, redirect: "follow" });
  if (!ilkYanit.ok) throw new Error(`HTTP ${ilkYanit.status}`);
  const ilkGovde = await ilkYanit.text();

  if (belgeBeslemeMi(ilkGovde)) return ilkGovde;

  const linkEtiketleri = ilkGovde.match(/<link\b[^>]*>/gi) || [];
  for (const etiket of linkEtiketleri) {
    const relUyar = /rel=["']alternate["']/i.test(etiket);
    const tipUyar = /type=["']application\/(rss|atom)\+xml["']/i.test(etiket);
    const hrefM = etiket.match(/href=["']([^"']+)["']/i);
    if (!relUyar || !tipUyar || !hrefM) continue;

    const feedUrl = new URL(hrefM[1], url).toString();
    try {
      const feedYanit = await fetch(feedUrl, { headers: basliklar });
      if (!feedYanit.ok) continue;
      const feedGovde = await feedYanit.text();
      if (belgeBeslemeMi(feedGovde)) return feedGovde;
    } catch {
      // bu aday adres başarısız oldu, diğer <link> etiketlerini dene
    }
  }

  throw new Error("besleme adresi bulunamadı (otomatik keşif başarısız)");
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
