# Haber Özeti

`haber_ham.sh`'nin otomatik/barındırılan sürümü. Aynı mantık: RSS
kaynaklarından `trafilatura` ile gerçek makale metni çekilir, ilk K cümle
özet olarak alınır. Fark: yerel Chromium açma ve canlı yenileme yerine
GitHub Actions'ta periyodik çalışıp statik bir sayfa üretir, GitHub Pages'e
yayınlar.

- Üretim `trafilatura` CLI'ı ile tam makale metnine iner (RSS'in kısa
  açıklamasıyla sınırlı değil), bu yüzden K cümle gerçekten K cümle olur.
- GitHub Actions'ın istek sayısında Cloudflare Workers gibi bir sınır
  olmadığı için kaynak/haber sayısı rahatça artırılabilir.
- Sayfa `lang="en"` üretilir ama tarayıcı dili Türkçeyse ilk yüklemede
  otomatik olarak Türkçe çeviriye (`translate.goog`) yönlendirilir —
  elle "Read in Turkish"e tıklamaya gerek yok. Kullanıcı "Read in
  English"e tıklarsa bu tercih `localStorage`'a yazılır ve bir daha
  otomatik yönlendirme yapılmaz.
- Sayfada 6 kategori sekmesi var: Gündem, Teknoloji, Bilim, Sanat &
  Kültür, Gezi, Yemek (Bilim ve Teknoloji kitleleri farklı olduğu için
  ayrı sekmeler — biri araştırma/keşif, diğeri ürün/şirket haberleri).
  Her sekmenin altında o kategorinin kaynaklarını
  listeleyen tek bir "Kaynak" açılır menüsü bulunur (bilerek native
  `<select>` değil — bkz. Ayarlar). Ayrıca koyu tema ve liste/kutu
  görünüm arasında geçiş yapan iki düğme var; ikisi de tercih olarak
  tarayıcıda saklanır.

## Bir kerelik kurulum

1. Repo → **Settings → Pages** → "Build and deployment" → **Source**
   olarak **"Deploy from a branch"**, dal olarak **`gh-pages`**, klasör
   olarak **`/ (root)`** seçin. ("GitHub Actions" kaynağı bu depoda
   kullanılamıyor — nedeni aşağıda, "Neden Pages'in GitHub Actions
   kaynağı kullanılmıyor" bölümünde.)
2. Depo içinde ekstra token/secret gerekmiyor; workflow GitHub'ın kendi
   `GITHUB_TOKEN`'ını kullanıyor. Yalnızca otomatik yenilemeyi tetikleyen
   harici zamanlayıcı için bir token gerekiyor (aşağıya bakın).

İlk deploy'dan sonra sayfa şu adreste yayında olur:
```
https://selcuk-hoo.github.io/haber-ozetleri/
```

## Nasıl çalışır

`.github/workflows/haber.yml`:
- Harici bir zamanlayıcının yarım saatte bir attığı `workflow_dispatch`
  isteğiyle (aşağıya bakın), her push'ta (script/workflow değişince) ve
  elle (**Actions → Haber Üret ve Yayınla → Run workflow**) tetiklenir.
- `scripts/haber_uret.py` çalışır: her kaynaktan `trafilatura --feed` ile
  haber listesini alır, her haberi `trafilatura -u` ile indirip tam metne
  iner, ilk K cümleyi özet olarak `dist/index.html`'e yazar.
- `dist/` klasörü `gh-pages` dalına yazılır ve Pages onu yayınlar (neden
  doğrudan Pages'in "GitHub Actions" kaynağına değil de bir dala
  yazıldığı aşağıda anlatılıyor). Dal her çalıştırmada sıfırdan kurulup
  force-push edildiği için hep tek commit içerir; geçmişi birikmez ve
  içinde elle yazılmış hiçbir şey yoktur. Yayın adımı sadece `main`'de
  çalışır, böylece geliştirme dalına yapılan push'lar canlı siteyi
  değiştirmez (ama üretimi yine de çalıştırıp hataları yakalar).

Sayfanın altındaki `derleme <sha>#<çalıştırma>` etiketi hangi kopyaya
baktığınızı söyler: SHA commit'i, numara çalıştırmayı gösterir. Sayfanın
güncellenip güncellenmediğini tartışırken önce buraya bakın.

## Ayarlar

- `scripts/haber_uret.py` → `N`: kaynak başına haber sayısı (varsayılan
  10), `K`: özet cümle sayısı (varsayılan 5). `KATEGORI_SAYISI` bir
  kategorideki, `KAYNAK_SAYISI` tek bir kaynaktaki sayıyı değiştirir
  (ör. `{"cnn.com": 5}`); kaynak ayarı kategori ayarından önce gelir.
- Özet temizliği: video/ses sayfaları (`/video/`, iPlayer, Sounds) hiç
  alınmaz, yerlerine sonraki haberler gelir. Özetin başındaki başlık
  tekrarı ile reklam, abonelik, bülten, "ilgili haberler" gibi kaynağa
  özgü kalıntılar (`_SILINEN_KALIPLAR`, `_KESILEN_KALIPLAR`,
  `_ATILAN_CUMLE`) cümleler seçilmeden önce çıkarılır. Bir kaynak sayfa
  düzenini değiştirip yeni bir kalıntı çıkarsa bu listelere eklenir.
- `KAYNAKLAR`: `(kategori, kaynak adı, besleme/anasayfa adresi)` üçlülerinden
  oluşan liste. Yeni bir kategori eklemek için listeye o kategori adıyla
  yeni satırlar eklemek yeterli; sayfa üstteki kategori sekmelerini ve
  her sekmenin kaynak menüsünü buradan otomatik üretir.
- Kaynak menüsü bilerek native `<select>` değil, düz bir buton + gizli/
  görünür `<ul><li>` listesi: Google Çeviri (`translate.goog`) sayfadaki
  gerçek `<select>`/`<form>` elemanlarını "form" sayıp bir uyarıyla
  engelliyor.
- Yenileme sıklığı: workflow'daki `cron` ifadesi değil, harici
  zamanlayıcının aralığı (aşağıya bakın).
- `scripts/ilk_gorulme.json`: gerçek RSS'i olmayan kaynaklarda (CNN, Al
  Jazeera, CN Traveler, Lonely Planet gibi anasayfadan/site haritasından
  çekilenler) ne sayfada ne beslemede tarih bulunabiliyor. Bu dosya, öyle
  bir haberi ilk gördüğümüz anı url'e göre kalıcı tutar; sayfada bu an
  `~` işaretiyle gösterilir (gerçek yayın saati değil, sadece sıralama
  ve "bir saat göster" içindir). Sadece `main`'de commit'lenir; artık
  görünmeyen haberlerin kaydı bir sonraki çalıştırmada otomatik düşer,
  dosya sınırsız büyümez.

## Google'da bulunabilirlik (SEO)

Site tarafında gereken hazırlık yapıldı: `<head>`'te açıklayıcı `<title>`,
meta description, canonical link, Open Graph/Twitter etiketleri var;
her çalıştırmada `dist/robots.txt` (taramaya izin verir, sitemap'i
bildirir) ve `dist/sitemap.xml` (site tek sayfa olduğu için tek url,
güncel `lastmod` ile) yeniden üretiliyor.

Google'ın siteyi gerçekten tarayıp indekslemesi için elle yapılması
gereken adımlar (bir kerelik):

1. [Google Search Console](https://search.google.com/search-console)'a
   `https://selcuk-hoo.github.io/haber-ozetleri/` adresini **URL prefix**
   mülkü olarak ekleyin.
2. Sahiplik doğrulamasını **HTML tag** yöntemiyle yapın: Search
   Console'ın verdiği `<meta name="google-site-verification" ...>`
   etiketini `scripts/haber_uret.py`'deki `sayfa_olustur`'un `<head>`
   bloğuna ekleyip deploy edin, sonra Search Console'da "Verify"e basın.
3. Search Console → **Sitemaps** → `sitemap.xml` gönderin
   (`https://selcuk-hoo.github.io/haber-ozetleri/sitemap.xml`).

İndekslenme birkaç gün sürebilir; site tek bir sayfa olduğu ve içeriği
büyük ölçüde başka yayıncılardan otomatik çıkarılmış özetlerden oluştuğu
için (özgün, kalıcı-URL'li makaleler değil) rekabetli aramalarda üst
sıralarda çıkması beklenmemeli — asıl fayda, sitenin adıyla/markasıyla
aratıldığında Google'da bulunabilir olması.

## Manuel yenileme

`github.com/selcuk-hoo/haber-ozetleri/actions/workflows/haber.yml` →
**"Run workflow"**. ~1-2 dakika içinde sayfa güncellenir.

## Otomatik yenileme: harici zamanlayıcı

Yarım saatlik otomatik güncelleme **GitHub'ın kendi `cron`'uyla değil**,
harici bir zamanlayıcının (örn. cron-job.org) GitHub API'sine attığı
`workflow_dispatch` isteğiyle yapılıyor. Zamanlayıcı şu isteği atar:

```
POST https://api.github.com/repos/selcuk-hoo/haber-ozetleri/actions/workflows/haber.yml/dispatches
Content-Type: application/json

Authorization: Bearer <TOKEN>
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28

{"ref":"main"}
```

`<TOKEN>`, yalnızca bu depoya ve yalnızca **Actions: Read and write**
yetkisine sahip bir fine-grained personal access token'dır. Token depoda
saklanmaz, sadece zamanlayıcı servisinde durur. Başarılı istek `204`
döner. `Content-Type: application/json` başlığı zorunlu — eksikse GitHub
isteği reddeder.

### Neden GitHub'ın `cron`'u kullanılmıyor

İki ayrı bilinen tuzak var; ikincisi bu depoda hiç çözülemedi:

1. GitHub, `schedule` tetikleyicisini her zaman deponun **varsayılan
   dalındaki** (`main`) workflow dosyasına göre çalıştırır — üzerinde
   çalışılan dal ne olursa olsun. Bu yüzden `main`, geliştirme dalıyla
   senkron tutulmalı.
2. Bu koşul sağlandıktan sonra bile `schedule` olayı bu depoya hiç
   ulaşmadı: 2.5 saat boyunca, iki farklı aralıkla (`*/30` ve `*/5`) ve
   workflow'u yeniden adlandırarak zamanlama kaydını sıfırdan
   oluşturmayı denedikten sonra bile tek bir zamanlanmış çalıştırma
   olmadı (`event=schedule` filtresi hep 0). Depo public, fork değil,
   arşivlenmemiş, Actions açık ve push/elle tetikleme sorunsuz
   çalışıyordu — yani yapılandırma değil, GitHub'ın zamanlayıcı tarafı
   sorunluydu.

Dosyadaki `cron` ifadesi yedek olarak duruyor: GitHub'ın zamanlayıcısı
ileride çalışmaya başlarsa fazladan bir çalıştırma olur, `concurrency`
ayarı sayesinde bu zararsızdır.

### Neden Pages'in "GitHub Actions" kaynağı kullanılmıyor

Çünkü **Pages aynı commit'i ikinci kez yayınlamıyor.** Zamanlayıcı hep
`main`'in aynı ucunu tetiklediği için, kod değişmediği sürece her
çalıştırma aynı commit'e deploy ediyordu: `upload-pages-artifact` taze
içeriği yüklüyor, `deploy-pages` başarıyla bitiyor, deployment kaydı
`success` görünüyor — ama sunulan sayfa değişmiyordu.

Ölçülen davranış (hepsi `success`, hiçbiri hata vermedi):

| Tetikleyici | Commit | Sonuç |
| --- | --- | --- |
| `workflow_dispatch` | zaten deploy edilmiş commit | sayfa değişmedi |
| `push` | yeni commit | sayfa güncellendi |

Dört ardışık `workflow_dispatch` çalıştırması aynı commit üzerinde
sayfayı hiç değiştirmedi; araya bir push (yeni commit) girer girmez
sayfa güncellendi. Pages'in saatlik deploy limiti değil: etkisiz kalan
deploy'ların bir kısmında saatlik sayaç 8'deydi.

Çözüm, her çalıştırmanın yeni bir commit üretmesini sağlamak: çıktı
`gh-pages` dalına yazılıyor (bkz. "Nasıl çalışır") ve Pages o dalı
yayınlıyor — dal içeriği her seferinde değiştiği için deploy hep geçer.

## Bilinen sınırlamalar

- `trafilatura`, bazı sitelerde bot koruması/JS gerektiren sayfalarda tam
  metne inemeyebilir; o durumda o haber atlanır (log'da görünür,
  `Actions → ilgili çalıştırma → uret` adımının çıktısında).
- Kaynağın RSS besleme adresi değişirse (sitenin kendi feed URL'ini
  güncellemesi gibi) `KAYNAKLAR` listesinin elle güncellenmesi gerekir.
- Çeviri tamamen `translate.goog`'a bırakıldığı için (sunucu tarafında
  çeviri yok), Google Çeviri'nin o an verdiği hizmete bağımlıdır; ayrıca
  tarayıcı dili Türkçe değilse veya JavaScript kapalıysa sayfa İngilizce
  kalır.
