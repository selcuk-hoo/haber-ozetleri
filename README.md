# Haber Özeti

`haber_ham.sh`'nin otomatik/barındırılan sürümü. Aynı mantık: RSS
kaynaklarından `trafilatura` ile gerçek makale metni çekilir, ilk K cümle
özet olarak alınır. Fark: yerel Chromium açma ve canlı yenileme yerine
GitHub Actions'ta periyodik çalışıp statik bir sayfa üretir, GitHub Pages'e
yayınlar.

- Sayfa `lang="en"` işaretlenir; tarayıcı açılışta Türkçeye çevirmeyi
  önerir (haber_ham.sh ile aynı fikir — sunucu tarafında çeviri yok).
- Üretim `trafilatura` CLI'ı ile tam makale metnine iner (RSS'in kısa
  açıklamasıyla sınırlı değil), bu yüzden K cümle gerçekten K cümle olur.
- GitHub Actions'ın istek sayısında Cloudflare Workers gibi bir sınır
  olmadığı için kaynak/haber sayısı rahatça artırılabilir.

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
- `scripts/haber_uret.py` çalışır: her kaynaktan `trafilatura --feed` ile
  haber listesini alır, her haberi `trafilatura -u` ile indirip tam metne
  iner, ilk K cümleyi özet olarak `dist/index.html`'e yazar.
- `dist/` klasörü GitHub Pages'e yayınlanır.

## Ayarlar

- `scripts/haber_uret.py` → `N`: kaynak başına haber sayısı (varsayılan
  10), `K`: özet cümle sayısı (varsayılan 5).
- `KAYNAKLAR`: `(kategori, kaynak adı, besleme/anasayfa adresi)` üçlülerinden
  oluşan liste. Sayfa üstte kategori sekmelerine (Gündem, Bilim &
  Teknoloji, Sanat & Kültür) ayrılır; her sekmenin kendi "All + kaynak"
  filtresi vardır. Yeni bir kategori eklemek için listeye o kategori adıyla
  yeni satırlar eklemek yeterli.
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
- Çeviri tamamen tarayıcıya bırakıldığı için, tarayıcı dilini Türkçe
  olmayan bir cihazda/otomatik çeviri kapalıyken sayfa İngilizce görünür.
