// "Yeni" işareti: okurun bir önceki ziyaretinden sonra yayımlanan ya da
// güncellenen haberlerin başlığının önüne küçük bir işaret konur. Ziyaret
// zamanları yalnız bu tarayıcıda (localStorage) tutulur. 30 dakikadan uzun
// aradan sonraki açılış yeni ziyaret sayılır; aynı ziyaretteki yenilemeler
// (tazele.js dahil) işaretleri silmez. İlk ziyarette işaret konmaz (her şey
// yeni görünürdü).
(function(){
  var ARA = 30 * 60 * 1000;
  var simdi = Date.now();
  var son = 0, onceki = 0;
  try {
    son = parseInt(localStorage.getItem('sonGoruldu'), 10) || 0;
    onceki = parseInt(localStorage.getItem('oncekiZiyaret'), 10) || 0;
  } catch (e) { return; }
  if (son && simdi - son > ARA) {
    onceki = son;
    try { localStorage.setItem('oncekiZiyaret', String(onceki)); } catch (e) {}
  }
  function goruldu() {
    try { localStorage.setItem('sonGoruldu', String(Date.now())); } catch (e) {}
  }
  goruldu();
  document.addEventListener('visibilitychange', function(){
    if (document.visibilityState === 'hidden') goruldu();
  });
  if (!onceki) return;
  var kartlar = document.querySelectorAll('article[data-zaman]');
  for (var i = 0; i < kartlar.length; i++) {
    var zaman = parseInt(kartlar[i].getAttribute('data-zaman'), 10) * 1000;
    if (zaman > onceki) kartlar[i].classList.add('yeni');
  }
})();
