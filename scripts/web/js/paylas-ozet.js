// Kart paylaşımı: başlık/görsel/özet/kaynağı tek bir PNG'ye çevirip
// (mümkünse) yerel paylaşım penceresini açar, değilse indirir. Kartın
// görseli çoğu kaynakta CORS izni olmayan üçüncü taraf bir sunucudan
// geldiği için doğrudan html2canvas ile çizilemiyor; bu yüzden SADECE
// bu ekran görüntüsü için images.weserv.nl üzerinden CORS izinli bir
// kopyası isteniyor — sayfanın normal gösterdiği görsel bundan
// etkilenmiyor, sadece bu tek seferlik render için kullanılıyor.
(function(){
  if (typeof html2canvas === 'undefined') {
    document.querySelectorAll('.paylas-ozet').forEach(function(b){ b.style.display = 'none'; });
    return;
  }

  function corsGorseli(url) {
    return 'https://images.weserv.nl/?url=' + encodeURIComponent(url.replace(/^https?:\/\//, ''));
  }

  document.addEventListener('click', function(olay){
    var buton = olay.target.closest('.paylas-ozet');
    if (!buton || buton.disabled) return;

    var kart = buton.closest('article');
    var orijinalGorsel = kart.querySelector('img');
    var kopya = kart.cloneNode(true);
    kopya.querySelectorAll('.dinle, .paylas-satiri, .ilgili').forEach(function(b){ b.remove(); });
    // Kaynak linki bir CSS maskesi; html2canvas maskeleri çizemiyor, bu
    // yüzden görüntü alınacak kopyada düz metinle değiştiriliyor.
    kopya.querySelectorAll('a.src').forEach(function(a){
      var metin = document.createElement('span');
      metin.className = 'src-metin';
      metin.textContent = a.getAttribute('aria-label') + ' \u2192';
      a.replaceWith(metin);
    });
    var detay = kopya.querySelector('details');
    if (detay) detay.open = true;

    // Kart ekrandaki genişliğiyle (geniş masaüstü pencerelerinde 700px'i
    // geçebiliyor) yakalanınca metin, paylaşılan görsel telefonda
    // büyütülüp bakıldığında bir satıra çok fazla karakter sığdığı için
    // ufak/okunaksız kalıyordu. Kart burada sabit, telefon ekranı
    // genişliğine yakın bir genişliğe (satır başına ~37 karakter hedefi,
    // ilk denemedeki ~40'tan kullanıcı isteğiyle %10 azaltıldı) zorlanıyor;
    // yazı tipi rem cinsinden sabit olduğundan metin bu dar kutuda daha
    // az karaktere sığıp daha büyük/okunur görünüyor.
    var PAYLASIM_GENISLIGI = 346;

    var sarici = document.createElement('div');
    sarici.style.cssText = 'position:fixed; left:-9999px; top:0; width:' + PAYLASIM_GENISLIGI + 'px;';
    sarici.appendChild(kopya);
    document.body.appendChild(sarici);

    var gorselHazir = Promise.resolve();
    var kopyaGorsel = kopya.querySelector('img');
    if (kopyaGorsel && orijinalGorsel) {
      // html2canvas ne CSS aspect-ratio'yu ne de object-fit:cover'ı
      // destekliyor; sadece kutu boyutunu zorlamak (bir önceki deneme)
      // görseli kırpmadan olduğu gibi ya da kendi doğal boyutunda
      // çiziyor, bu yüzden hâlâ ince-uzun çıkıyordu. Kırpma/ölçekleme
      // burada elle bir canvas'a "cover" mantığıyla çizilip html2canvas'a
      // ZATEN doğru piksel oranında bir görsel veriliyor — html2canvas'ın
      // sadece düz bir resmi olduğu gibi çizmesi yetiyor. Hedef kutu,
      // kopyanın YENİ (sabit genişlikli) haldeki kendi boyutundan
      // okunuyor ki 16/9 oranı PAYLASIM_GENISLIGI'ne göre doğru çıksın.
      var hedefGenislik = kopyaGorsel.offsetWidth;
      var hedefYukseklik = kopyaGorsel.offsetHeight;
      kopyaGorsel.style.width = hedefGenislik + 'px';
      kopyaGorsel.style.height = hedefYukseklik + 'px';
      gorselHazir = new Promise(function(tamam){
        var zamanAsimi = setTimeout(function(){ kopyaGorsel.remove(); tamam(); }, 6000);
        var yukleyici = new Image();
        yukleyici.crossOrigin = 'anonymous';
        yukleyici.onload = function(){
          clearTimeout(zamanAsimi);
          try {
            var canvas = document.createElement('canvas');
            canvas.width = hedefGenislik;
            canvas.height = hedefYukseklik;
            var olcek = Math.max(hedefGenislik / yukleyici.naturalWidth, hedefYukseklik / yukleyici.naturalHeight);
            var cizilenGenislik = yukleyici.naturalWidth * olcek;
            var cizilenYukseklik = yukleyici.naturalHeight * olcek;
            canvas.getContext('2d').drawImage(
              yukleyici,
              (hedefGenislik - cizilenGenislik) / 2,
              (hedefYukseklik - cizilenYukseklik) / 2,
              cizilenGenislik, cizilenYukseklik
            );
            // .decode() burada bazı tarayıcılarda hiç sonuçlanmıyor
            // (muhtemelen ekran dışına taşınmış/henüz yerleşimi
            // tamamlanmamış bir öğe için); data: URI zaten senkron
            // olarak hazır olduğundan beklemeye gerek yok.
            kopyaGorsel.src = canvas.toDataURL('image/jpeg', 0.92);
            tamam();
            return;
          } catch (e) {
            kopyaGorsel.remove();
          }
          tamam();
        };
        yukleyici.onerror = function(){
          clearTimeout(zamanAsimi);
          kopyaGorsel.remove();
          tamam();
        };
        yukleyici.src = corsGorseli(orijinalGorsel.currentSrc || orijinalGorsel.src);
      });
    }

    // Bekleme sırasında buton sadece soluklaşıyor (.paylas:disabled);
    // etikete metin yazılmıyor ki translate.goog'a çevirecek bir şey
    // verilmesin.
    buton.disabled = true;

    function birak() {
      sarici.remove();
      buton.disabled = false;
    }

    gorselHazir.then(function(){
      return html2canvas(kopya, {
        backgroundColor: getComputedStyle(document.body).backgroundColor,
        useCORS: true,
        scale: 2,
      });
    }).then(function(canvas){
      return new Promise(function(tamam){ canvas.toBlob(tamam, 'image/png'); });
    }).then(function(blob){
      birak();
      if (!blob) return;

      var baslikEl = kart.querySelector('h3');
      var dosya = new File([blob], 'dunyadan-notlar.png', { type: 'image/png' });

      if (navigator.canShare && navigator.canShare({ files: [dosya] })) {
        navigator.share({ files: [dosya], title: baslikEl ? baslikEl.textContent : 'Dünyadan Notlar' }).catch(function(){});
        return;
      }

      var indirmeLinki = document.createElement('a');
      indirmeLinki.href = URL.createObjectURL(blob);
      indirmeLinki.download = 'dunyadan-notlar.png';
      document.body.appendChild(indirmeLinki);
      indirmeLinki.click();
      indirmeLinki.remove();
      setTimeout(function(){ URL.revokeObjectURL(indirmeLinki.href); }, 30000);
    }).catch(function(hata){
      birak();
      console.error('Paylaşım görseli oluşturulamadı:', hata);
    });
  });
})();
