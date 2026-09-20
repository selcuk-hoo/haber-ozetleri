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
   olarak **"Deploy from a branch"**, dal olarak **`gh-pages`**, klasör
   olarak **`/ (root)`** seçin. ("GitHub Actions" kaynağı bu depoda
   kullanılamıyor — nedeni aşağıda.)
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
  Dosyadaki `cron` ifadesi de duruyor ama GitHub'ın zamanlayıcısı bu
  depoda çalışmıyor (aşağıya bakın).
- `scripts/haber_uret.py` çalışır: her kaynaktan `trafilatura --feed` ile
  haber listesini alır, her haberi `trafilatura -u` ile indirip tam metne
  iner, ilk K cümleyi özet olarak `dist/index.html`'e yazar.
- `dist/` klasörü `gh-pages` dalına yazılır ve Pages onu yayınlar. Dal her
  çalıştırmada sıfırdan kurulup force-push edildiği için hep tek commit
  içerir; geçmişi birikmez ve içinde elle yazılmış hiçbir şey yoktur.
  Yayın adımı sadece `main`'de çalışır, böylece geliştirme dalına yapılan
  push'lar canlı siteyi değiştirmez (ama üretimi yine de çalıştırıp
  hataları yakalar).

Sayfanın altındaki `derleme <sha>#<çalıştırma>` etiketi hangi kopyaya
baktığınızı söyler: SHA commit'i, numara çalıştırmayı gösterir. Sayfanın
güncellenip güncellenmediğini tartışırken önce buraya bakın.

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

`github.com/selcuk-hoo/haber-ozetleri/actions/workflows/haber.yml` →
**"Run workflow"**. ~1-2 dakika içinde sayfa güncellenir.

## Otomatik yenileme: harici zamanlayıcı

Yarım saatlik otomatik güncelleme **GitHub'ın kendi `cron`'uyla değil**,
harici bir zamanlayıcının GitHub API'sine attığı `workflow_dispatch`
isteğiyle yapılıyor. Zamanlayıcı şu isteği atar:

```
POST https://api.github.com/repos/selcuk-hoo/haber-ozetleri/actions/workflows/haber.yml/dispatches

Authorization: Bearer <TOKEN>
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28

{"ref":"main"}
```

`<TOKEN>`, yalnızca bu depoya ve yalnızca **Actions: Read and write**
yetkisine sahip bir fine-grained personal access token'dır. Token depoda
saklanmaz, sadece zamanlayıcı servisinde durur. Başarılı istek `204`
döner.

### Neden GitHub'ın `cron`'u kullanılmıyor

İki ayrı bilinen tuzak var; ikincisi bu depoda çözülemedi:

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
sayfa güncellendi. Pages'in saatlik deploy limiti değil: etkisiz
kalan deploy'ların bir kısmında saatlik sayaç 8'deydi.

Çözüm, her çalıştırmanın yeni bir commit üretmesini sağlamak: çıktı
`gh-pages` dalına yazılıyor ve Pages o dalı yayınlıyor.

## Bilinen sınırlamalar

- `trafilatura`, bazı sitelerde bot koruması/JS gerektiren sayfalarda tam
  metne inemeyebilir; o durumda o haber atlanır (log'da görünür,
  `Actions → ilgili çalıştırma → uret` adımının çıktısında).
- Kaynağın RSS besleme adresi değişirse (sitenin kendi feed URL'ini
  güncellemesi gibi) `KAYNAKLAR` listesinin elle güncellenmesi gerekir.
- Çeviri tamamen tarayıcıya bırakıldığı için, tarayıcı dilini Türkçe
  olmayan bir cihazda/otomatik çeviri kapalıyken sayfa İngilizce görünür.
