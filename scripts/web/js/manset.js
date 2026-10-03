// Manşet sekmesi: okurun henüz açmadığı yeni bir baskı varsa sekmede küçük
// bir nokta görünür (bkz. stil.css .yeni-baski). Görülen son baskı yalnız
// bu tarayıcıda (localStorage) tutulur; erişilemezse nokta hiç konmaz.
(function(){
  var buton = document.querySelector('.manset-buton');
  if (!buton) return;
  var baski = buton.getAttribute('data-baski');
  var gorulen;
  try { gorulen = localStorage.getItem('mansetGoruldu'); } catch (e) { return; }
  if (baski && gorulen !== baski) buton.classList.add('yeni-baski');
  buton.addEventListener('click', function(){
    buton.classList.remove('yeni-baski');
    try { localStorage.setItem('mansetGoruldu', baski); } catch (e) {}
  });
})();
