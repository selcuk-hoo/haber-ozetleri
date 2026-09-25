// Eskimiş sayfayı yenileme: telefon tarayıcıları bir sekmeye dönüldüğünde
// sayfayı yeniden indirmeden bellekten gösterebiliyor; okur saatlerce
// eski haberlere bakıyordu. Sayfa yarım saatte bir üretiliyor; açıldığında
// ya da sekmeye dönüldüğünde 45 dakikadan eskiyse kendini bir kez yeniler.
// Kaynakta bir aksaklık olup sayfa gerçekten eskiyse döngüye girmesin diye
// en fazla 10 dakikada bir yenilenir.
(function(){
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
