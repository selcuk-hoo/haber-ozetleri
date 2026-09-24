// "Orijinal metni paylaş": haberin iki bağlantısını birlikte paylaşır —
// translate.goog üzerinden Türkçe çevirisi ve kaynaktaki orijinali.
// Yalnız orijinal gönderildiğinde bazı sayfalar alıcının Chrome'unda
// Türkçeye çevrilemedi; yalnız çeviri gönderilse translate.goog'u
// engelleyen ağlarda (ör. kullanıcının iş yeri) hiç açılmaz. Çeviri
// adresi sayfanın kendi "Read in Turkish" bağlantısındaki
// (cevrilmisAdres) kuralla kuruluyor. Paylaşım penceresi yoksa metin
// panoya kopyalanıyor.
(function(){
  function ceviriAdresi(url) {
    var u = new URL(url);
    var host = u.hostname.replace(/-/g, '--').replace(/\./g, '-') + '.translate.goog';
    var ayrac = u.search ? '&' : '?';
    return u.protocol + '//' + host + u.pathname + u.search + ayrac +
      '_x_tr_sl=en&_x_tr_tl=tr&_x_tr_hl=tr&_x_tr_pto=wapp' + u.hash;
  }

  function kopyalandiGoster(buton) {
    var etiket = buton.querySelector('.etiket-resmi');
    etiket.classList.add('etiket-kopyalandi');
    clearTimeout(buton._zamanlayici);
    buton._zamanlayici = setTimeout(function(){ etiket.classList.remove('etiket-kopyalandi'); }, 2000);
  }

  function panoyaKopyala(buton, metin) {
    var kopya = (navigator.clipboard && navigator.clipboard.writeText)
      ? navigator.clipboard.writeText(metin)
      : Promise.reject(new Error('pano yok'));
    kopya.then(function(){ kopyalandiGoster(buton); }, function(){
      window.prompt('Bağlantıyı kopyalayın:', metin);
    });
  }

  document.addEventListener('click', function(olay){
    var buton = olay.target.closest('.paylas-orijinal');
    if (!buton) return;
    var kart = buton.closest('article');
    var adres = kart.dataset.url;
    if (!adres) return;
    var baslikEl = kart.querySelector('h3');
    var baslik = baslikEl ? baslikEl.textContent.trim() : '';
    var turkce;
    try { turkce = ceviriAdresi(adres); } catch (e) { turkce = null; }
    // Bağlantılar ayrı bir url alanı yerine metnin içinde: url verilince
    // bazı uygulamalar onu metnin başına ya da sonuna kendisi ekliyor,
    // hangisinin Türkçe hangisinin orijinal olduğu karışıyor.
    var metin = baslik + '\n\n' +
      (turkce ? 'Türkçe: ' + turkce + '\n\n' : '') +
      'Orijinal: ' + adres;

    if (navigator.share) {
      navigator.share({ title: baslik, text: metin }).catch(function(hata){
        if (hata && hata.name === 'AbortError') return;
        panoyaKopyala(buton, metin);
      });
      return;
    }
    panoyaKopyala(buton, metin);
  });
})();
