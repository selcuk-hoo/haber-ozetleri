// Yazı boyutu düğmeleri: tüm sayfa rem birimiyle ölçeklendiği için
// <html>'in kök font-size'ını değiştirmek yeter, her şey orantılı
// büyür/küçülür. Tercih tarayıcıda (localStorage) hatırlanır.
(function(){
  var kucultDugme = document.getElementById('yazi-kucult-buton');
  var buyutDugme = document.getElementById('yazi-buyut-buton');
  if (!kucultDugme || !buyutDugme) return;

  var ADIMLAR = [80, 90, 100, 110, 120, 130, 140, 150]; // yüzde
  var VARSAYILAN_INDEKS = ADIMLAR.indexOf(100);

  function indeksiBul(yuzde) {
    var i = ADIMLAR.indexOf(yuzde);
    return i === -1 ? VARSAYILAN_INDEKS : i;
  }

  function uygula(indeks) {
    var yuzde = ADIMLAR[indeks];
    document.documentElement.style.fontSize = yuzde === 100 ? '' : yuzde + '%';
    kucultDugme.disabled = indeks === 0;
    buyutDugme.disabled = indeks === ADIMLAR.length - 1;
    try { localStorage.setItem('yaziOlcek', String(yuzde)); } catch (e) {}
  }

  var kayitliYuzde = null;
  try { kayitliYuzde = parseInt(localStorage.getItem('yaziOlcek'), 10); } catch (e) {}
  var mevcutIndeks = indeksiBul(kayitliYuzde || 100);
  uygula(mevcutIndeks);

  kucultDugme.addEventListener('click', function(){
    mevcutIndeks = Math.max(0, mevcutIndeks - 1);
    uygula(mevcutIndeks);
  });
  buyutDugme.addEventListener('click', function(){
    mevcutIndeks = Math.min(ADIMLAR.length - 1, mevcutIndeks + 1);
    uygula(mevcutIndeks);
  });
})();
