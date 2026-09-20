# Haber Özeti

`haber_ham.sh`'nin otomatik/barındırılan sürümü. Aynı mantık: RSS
kaynaklarından `trafilatura` ile gerçek makale metni çekilir, ilk K cümle
özet olarak alınır. Fark: yerel Chromium açma ve canlı yenileme yerine
GitHub Actions'ta periyodik çalışıp statik bir sayfa üretir, GitHub Pages'e
yayınlar.

- Her haberin başlık+özeti **üretim anında** (`deep-translator` ile,
  Google Translate'in ücretsiz/anahtarsız uç noktası) Türkçeye çevrilip
  sayfaya doğrudan Türkçe olarak gömülür — tarayıcı proxy'sine/yönlendirmeye
  gerek yok, tek dilli normal bir sayfa (`lang="tr"`).
- Üretim `trafilatura`'nın Python API'siyle tam makale metnine iner (RSS'in
  kısa açıklamasıyla sınırlı değil), bu yüzden K cümle gerçekten K cümle
  olur.
- GitHub Actions'ın istek sayısında Cloudflare Workers gibi bir sınır
  olmadığı için kaynak/haber sayısı rahatça artırılabilir.
- Her karttaki "Dinle" butonu, tarayıcının yerleşik Web Speech API'siyle
  başlık+özeti Türkçe sesle okur (sunucu/API yok; cihazda Türkçe TTS
  sesi kurulu değilse çalışmayabilir — bu bir cihaz kısıtı).

## Bir kerelik kurulum

1. Repo → **Settings → Pages** → "Build and deployment" → **Source**
   olarak **"GitHub Actions"** seçin (varsayılan "Deploy from a branch"
   değil).
2. Bu kadar — ekstra token, secret, hesap bağlama gerekmiyor. Workflow
   GitHub'ın kendi `GITHUB_TOKEN`'ını kullanıyor.

İlk deploy'dan sonra sayfa şu adreste yayında olur:
```
https://selcuk-hoo.github.io/haber-ozetleri/
```

## Nasıl çalışır

`.github/workflows/haber-uret.yml`:
- 3 saatte bir (`cron`), her push'ta (script/workflow değişince) ve elle
  (**Actions → Haber Üret ve Yayınla → Run workflow**) tetiklenir.
- `scripts/haber_uret.py` çalışır: her kaynaktan `find_feed_urls` ile
  haber listesini alır, her haberi `trafilatura.fetch_url`/`bare_extraction`
  ile indirip tam metne iner, ilk K cümleyi özetler, başlık+özeti Türkçeye
  çevirir ve `dist/index.html`'e yazar.
- `dist/` klasörü GitHub Pages'e yayınlanır.

## Ayarlar

- `scripts/haber_uret.py` → `N`: kaynak başına haber sayısı (varsayılan
  10), `K`: özet cümle sayısı (varsayılan 5).
- `KAYNAKLAR`: RSS kaynak listesi.
- Yenileme sıklığı: workflow dosyasındaki `cron` ifadesi.

## Manuel yenileme

`github.com/selcuk-hoo/haber-ozetleri/actions/workflows/haber-uret.yml` →
**"Run workflow"**. ~1-2 dakika içinde sayfa güncellenir.

## Bilinen sınırlamalar

- `trafilatura`, bazı sitelerde bot koruması/JS gerektiren sayfalarda tam
  metne inemeyebilir; o durumda o haber atlanır (log'da görünür,
  `Actions → ilgili çalıştırma → uret` adımının çıktısında).
- Kaynağın RSS besleme adresi değişirse (sitenin kendi feed URL'ini
  güncellemesi gibi) `KAYNAKLAR` listesinin elle güncellenmesi gerekir.
- Çeviri resmi bir API olmayan ücretsiz bir uç noktayı kullanıyor; nadiren
  geçici hata verebilir — o durumda ilgili haber İngilizce kalır (sayfa
  kırılmaz), bir sonraki üretimde tekrar denenir.
