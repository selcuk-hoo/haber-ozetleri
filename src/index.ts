import { KAYNAKLAR, besleyiAyristir, ilkCumleler } from "./feeds";
import { turkceyeCevir } from "./translate";
import { sayfayiOlustur, type Makale } from "./render";

export interface Env {
  HABER_KV: KVNamespace;
  AI: Ai;
  // wrangler secret put YENILE_ANAHTARI  ile ayarlanabilir (opsiyonel).
  YENILE_ANAHTARI?: string;
}

const N = 8; // kaynak başına haber sayısı
const K = 3; // özet cümle sayısı
const KV_ANAHTARI = "digest:html";

const FETCH_BASLIKLARI = {
  "user-agent":
    "Mozilla/5.0 (compatible; HaberOzetleriBot/1.0; +https://workers.cloudflare.com)",
};

async function kaynagiIsle(
  kaynak: { ad: string; url: string },
  env: Env
): Promise<Makale[]> {
  const yanit = await fetch(kaynak.url, { headers: FETCH_BASLIKLARI });
  if (!yanit.ok) throw new Error(`HTTP ${yanit.status}`);
  const xml = await yanit.text();

  const ogeler = besleyiAyristir(xml, N);
  const makaleler: Makale[] = [];

  for (const oge of ogeler) {
    const ozetIngilizce = ilkCumleler(oge.govde || oge.baslik, K);
    if (!ozetIngilizce) continue;

    const [baslikTr, ozetTr] = await Promise.all([
      turkceyeCevir(env.AI, oge.baslik),
      turkceyeCevir(env.AI, ozetIngilizce),
    ]);

    makaleler.push({
      baslik: baslikTr,
      link: oge.link,
      ozet: ozetTr,
      kaynakAdi: kaynak.ad,
    });
  }

  return makaleler;
}

async function ozetUret(env: Env): Promise<string> {
  const makalelerByKaynak = new Map<string, Makale[]>();
  const hatalar = new Set<string>();

  for (const kaynak of KAYNAKLAR) {
    try {
      const makaleler = await kaynagiIsle(kaynak, env);
      makalelerByKaynak.set(kaynak.ad, makaleler);
    } catch (hata) {
      console.error(`${kaynak.ad} işlenemedi:`, hata);
      makalelerByKaynak.set(kaynak.ad, []);
      hatalar.add(kaynak.ad);
    }
  }

  const html = sayfayiOlustur(KAYNAKLAR, makalelerByKaynak, hatalar, K, new Date());
  await env.HABER_KV.put(KV_ANAHTARI, html);
  return html;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/yenile") {
      const anahtar = url.searchParams.get("anahtar");
      if (env.YENILE_ANAHTARI && anahtar !== env.YENILE_ANAHTARI) {
        return new Response("Yetkisiz.\n", { status: 401 });
      }
      ctx.waitUntil(ozetUret(env));
      return new Response("Yenileme başlatıldı, birazdan hazır olacak.\n", {
        status: 202,
      });
    }

    const onbellek = await env.HABER_KV.get(KV_ANAHTARI);
    if (onbellek) {
      return new Response(onbellek, {
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }

    // Henüz hiç üretim yapılmamış: ilk isteği bekletip anında üret.
    const html = await ozetUret(env);
    return new Response(html, {
      headers: { "content-type": "text/html; charset=utf-8" },
    });
  },

  async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(ozetUret(env));
  },
};
