(function(){
  var a = document.getElementById('cevir-linki');
  // Zaten translate.goog aynasındaysak (kendi yönlendirmemizden ya da
  // kullanıcının kendi tıklamasından) bunu adres/dilden anlıyoruz.
  var suankiGoog = location.hostname.indexOf('.translate.goog') !== -1;

  // Chrome'un kendi "Sayfayı çevir" özelliğinin kullandığı translate.goog
  // ayna adresi — eski translate.google.com/translate?...&u= proxy'sinden
  // farklı olarak hâlâ güvenilir çalışıyor.
  function cevrilmisAdres() {
    var host = location.hostname.replace(/-/g, '--').replace(/\./g, '-') + '.translate.goog';
    var ayrac = location.search ? '&' : '?';
    return location.protocol + '//' + host + location.pathname + location.search +
      ayrac + '_x_tr_sl=en&_x_tr_tl=tr&_x_tr_hl=tr&_x_tr_pto=wapp';
  }

  // translate.goog'un anasayfa adını gerçek adrese çevirir (kodlama:
  // önce her "-" harfi "--" olarak ikizlenir, sonra her "." "-" olur;
  // burada tam tersi uygulanıyor).
  function orijinalAdres() {
    var kodlanmis = location.hostname.replace(/\.translate\.goog$/, '');
    var host = kodlanmis.split('--').map(function(parca){ return parca.replace(/-/g, '.'); }).join('-');
    return location.protocol + '//' + host + location.pathname;
  }

  if (a) {
    if (suankiGoog) {
      a.href = orijinalAdres();
      a.setAttribute('data-etiket', '🇬🇧 İngilizce oku');
      // Kullanıcı elle İngilizce'ye dönerse bir daha otomatik Türkçeye
      // sürüklenmesin diye tercihi hatırla.
      a.addEventListener('click', function(){
        try { localStorage.setItem('dilTercihi', 'en'); } catch (e) {}
      });
    } else {
      a.href = cevrilmisAdres();
    }
  }

  // ?en=1 ile açılırsa otomatik Türkçe yönlendirmesi kalıcı olarak
  // kapatılır. Bazı kurumsal ağlar translate.goog'u "Anonymizer"
  // (proxy) kategorisine sokup engelliyor; bu durumda otomatik
  // yönlendirme kullanıcıyı "Read in English"e tıklamaya fırsat
  // bulamadan doğrudan engellenen sayfaya götürüyordu. Bu adresi bir
  // kez açmak yeterli, tercih localStorage'da kalıcı.
  try {
    if (new URLSearchParams(location.search).get('en') === '1') {
      localStorage.setItem('dilTercihi', 'en');
    }
  } catch (e) {}

  // Tarayıcı dili Türkçeyse (ve kullanıcı elle İngilizce'yi seçmediyse)
  // sayfa ilk yüklenirken otomatik olarak Türkçe çeviriye yönlendir —
  // "Read in Turkish"e tıklamaya gerek kalmadan.
  if (!suankiGoog) {
    var tercih = null;
    try { tercih = localStorage.getItem('dilTercihi'); } catch (e) {}
    if (tercih !== 'en') {
      var dil = (navigator.language || (navigator.languages && navigator.languages[0]) || '').toLowerCase();
      if (dil.indexOf('tr') === 0) {
        location.replace(cevrilmisAdres());
      }
    }
  }
})();
