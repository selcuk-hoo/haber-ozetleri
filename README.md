# Haber Özeti — Cloudflare Worker

`haber_ham.sh` scriptinin Cloudflare üzerinde yayınlanabilen sürümü. Aynı
mantığı kullanır (RSS kaynaklarından ilk K cümleyi özet olarak alır) ama:

- Yerel `trafilatura`/Chromium yerine RSS beslemesindeki başlık + özet
  metnini doğrudan kullanır (Workers'ta Python çalışmadığı için tam metin
  kazıma yapılmaz).
- Özetleri **Cloudflare Workers AI** (`@cf/meta/m2m100-1.2b`) ile otomatik
  olarak Türkçeye çevirir — tarayıcının çeviri önerisine güvenmez.
- Sonucu bir **Cron Trigger** ile periyodik üretip **KV**'de önbelleğe alır;
  siteyi açan herkes hazır sayfayı anında görür.

## Kurulum

```bash
npm install
npx wrangler login

# KV namespace oluştur, döndürdüğü id'yi wrangler.toml'a yaz
npx wrangler kv namespace create HABER_KV
```

`wrangler.toml` içindeki `REPLACE_WITH_KV_NAMESPACE_ID` değerini yukarıdaki
komutun çıktısıyla değiştirin.

Workers AI, hesabınızda otomatik olarak etkindir; ekstra kurulum gerekmez
(ücretsiz plan günlük nöron kotasıyla sınırlıdır).

İsteğe bağlı: `/yenile` uç noktasını herkese açık bırakmamak için bir anahtar
tanımlayın:

```bash
npx wrangler secret put YENILE_ANAHTARI
```

## Geliştirme ve yayınlama

```bash
npm run dev      # yerelde dene (wrangler dev)
npm run deploy   # workers.dev alt alanına yayınla
```

İlk yayından sonra Worker'a `https://haber-ozetleri.<hesabınız>.workers.dev`
adresinden ulaşabilirsiniz. Kendi alan adınızı bağlamak isterseniz Cloudflare
panelinde Workers & Pages → haber-ozetleri → Settings → Domains & Routes'tan
bir custom domain ekleyin.

## Ayarlar

- `wrangler.toml` → `[triggers].crons`: özetin ne sıklıkla yenileneceği
  (varsayılan 3 saatte bir).
- `src/index.ts` → `N`: kaynak başına haber sayısı, `K`: özet cümle sayısı.
- `src/feeds.ts` → `KAYNAKLAR`: RSS kaynak listesi.

## Manuel yenileme

```
GET /yenile?anahtar=<YENILE_ANAHTARI>
```

Arka planda yeni bir üretim başlatır (senkron beklemez), birkaç saniye sonra
sayfayı yeniden açtığınızda güncel içerik gelir.

## Bilinen sınırlamalar

- Özetler RSS beslemesindeki açıklama metnine dayanır; bazı kaynaklar kısa
  ya da boş açıklama döndürebilir (`haber_ham.sh`'deki gibi tam makale
  metnine `trafilatura` ile inmez).
- Çeviri modeli ara sıra hatalı/eksik çevirebilir; çeviri başarısız olursa
  sayfa orijinal İngilizce metne düşer.
- Çok sayıda haberi tek seferde çevirmek zaman alır; bu yüzden üretim
  cron job'da arka planda yapılır, kullanıcı isteği önbellekten anında
  cevap alır.
