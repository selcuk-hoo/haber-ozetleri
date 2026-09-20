import { KAYNAKLAR, besleyiAyristir, feedIcerigiGetir, ilkCumleler } from "./feeds";
import { baslikVeOzetCevir } from "./translate";
import { sayfayiOlustur, type Makale } from "./render";

export interface Env {
  HABER_KV: KVNamespace;
  AI: Ai;
  // wrangler secret put YENILE_ANAHTARI  ile ayarlanabilir (opsiyonel).
  YENILE_ANAHTARI?: string;
}

// N ve K, Cloudflare Workers'ın istek başına alt-istek sınırıyla (ücretsiz
// planda 50) dengelenmeli: her haber tek bir AI çağrısı kullanıyor, artı
// kaynak başına 1 besleme çağrısı. 6 kaynak × N haber + 6 ≤ 50 kalmalı.
const N = 6; // kaynak başına haber sayısı
const K = 5; // özet cümle sayısı
const KV_ANAHTARI = "digest:html";

const FETCH_BASLIKLARI = {
  "user-agent":
    "Mozilla/5.0 (compatible; HaberOzetleriBot/1.0; +https://workers.cloudflare.com)",
};

// Bir kaynaktaki haberler birbirinden bağımsız: hepsini paralel işler.
// Sırayla işlemek (36+ AI çağrısını art arda beklemek) Cloudflare'ın
// waitUntil() için verdiği süreyi aşıp arka plan üretimini iptal ettiriyordu.
async function kaynagiIsle(
  kaynak: { ad: string; url: string },
  env: Env
): Promise<Makale[]> {
  const xml = await feedIcerigiGetir(kaynak.url, FETCH_BASLIKLARI);
  const ogeler = besleyiAyristir(xml, N);

  const sonuclar = await Promise.all(
    ogeler.map(async (oge): Promise<Makale | null> => {
      const ozetIngilizce = ilkCumleler(oge.govde || oge.baslik, K);
      if (!ozetIngilizce) return null;

      const { baslik: baslikTr, ozet: ozetTr } = await baslikVeOzetCevir(
        env.AI,
        oge.baslik,
        ozetIngilizce
      );

      return { baslik: baslikTr, link: oge.link, ozet: ozetTr, kaynakAdi: kaynak.ad };
    })
  );

  return sonuclar.filter((m): m is Makale => m !== null);
}

async function ozetUret(env: Env): Promise<string> {
  // Kaynaklar da birbirinden bağımsız: hepsi paralel işlenir.
  const sonuclar = await Promise.all(
    KAYNAKLAR.map(async (kaynak) => {
      try {
        return { kaynak, makaleler: await kaynagiIsle(kaynak, env), hataliMi: false };
      } catch (hata) {
        console.error(`${kaynak.ad} işlenemedi:`, hata);
        return { kaynak, makaleler: [] as Makale[], hataliMi: true };
      }
    })
  );

  const makalelerByKaynak = new Map<string, Makale[]>();
  const hatalar = new Set<string>();
  for (const { kaynak, makaleler, hataliMi } of sonuclar) {
    makalelerByKaynak.set(kaynak.ad, makaleler);
    if (hataliMi) hatalar.add(kaynak.ad);
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

    const sayfaBasliklari = {
      "content-type": "text/html; charset=utf-8",
      // Tarayıcı/ara önbellekler eski sayfayı göstermesin — her istekte
      // Worker'a gelsin, güncel içerik KV'den anında dönsün.
      "cache-control": "no-store",
    };

    const onbellek = await env.HABER_KV.get(KV_ANAHTARI);
    if (onbellek) {
      return new Response(onbellek, { headers: sayfaBasliklari });
    }

    // Henüz hiç üretim yapılmamış: ilk isteği bekletip anında üret.
    const html = await ozetUret(env);
    return new Response(html, { headers: sayfaBasliklari });
  },

  async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(ozetUret(env));
  },
};
