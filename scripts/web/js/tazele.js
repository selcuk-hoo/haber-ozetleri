// Eskimiş sayfayı yenileme: telefon tarayıcıları bir sekmeye dönüldüğünde
// sayfayı yeniden indirmeden bellekten gösterebiliyor; okur saatlerce
// eski haberlere bakıyordu. Sayfa yarım saatte bir üretiliyor; açıldığında
// ya da sekmeye dönüldüğünde 45 dakikadan eskiyse kendini bir kez yeniler.
// Kaynakta bir aksaklık olup sayfa gerçekten eskiyse döngüye girmesin diye
// en fazla 10 dakikada bir yenilenir.
(function(){
  // Başlığa ("Dünyadan Notlar") tıklanınca sayfa yenilenir ve en üstten
  // açılır. Bağlantının kendisi de aynı sayfaya gider (JS yoksa yedek);
  // ama bazı tarayıcılar aynı adrese gidişte önbellekteki kopyayı
  // gösterebildiği için açıkça reload() çağrılıyor.
  var baslik = document.querySelector('.ana-sayfa');
  if (baslik) {
    baslik.addEventListener('click', function(olay){
      if (olay.ctrlKey || olay.metaKey || olay.shiftKey || olay.button !== 0) return;
      olay.preventDefault();
      try { history.scrollRestoration = 'manual'; } catch (e) {}
      location.reload();
    });
  }

  var uretim = parseInt(document.documentElement.getAttribute('data-uretim'), 10) * 1000;
  if (!uretim) return;
  var ESKI = 45 * 60 * 1000;
  var ARALIK = 10 * 60 * 1000;

  function kontrol() {
    if (document.visibilityState !== 'visible') return;
    if (Date.now() - uretim < ESKI) return;
    var son = 0;
    try { son = parseInt(sessionStorage.getItem('tazelendi'), 10) || 0; } catch (e) {}
    if (Date.now() - son < ARALIK) return;
    try { sessionStorage.setItem('tazelendi', String(Date.now())); } catch (e) {}
    location.reload();
  }

  document.addEventListener('visibilitychange', kontrol);
  window.addEventListener('pageshow', kontrol);
  kontrol();
})();
