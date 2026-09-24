// Sesli okuma: tarayıcının yerleşik Web Speech API'si, sunucu/API yok.
(function(){
  if (!('speechSynthesis' in window)) {
    document.querySelectorAll('.dinle').forEach(function(b){ b.style.display = 'none'; });
    return;
  }

  function sifirla(buton) {
    buton.dataset.playing = '0';
    buton.setAttribute('data-etiket', '\uD83D\uDD0A Dinle');
  }

  // Google'ın translate.goog aynasında sayfanın görünen metni zaten
  // Türkçeye çevrilmiş olarak geliyor; bu durumda ekrandaki metni okuyup
  // Türkçe sesle seslendiriyoruz. Normal sayfada İngilizce okunuyor.
  var turkceMi = location.hostname.indexOf('translate.goog') !== -1;

  // Sadece .lang ayarlamak yetmiyor — bazı tarayıcılar yine de varsayılan
  // (genelde İngilizce) sesi kullanıp metni yanlış telaffuzla okuyor.
  // Uygun dildeki gerçek sesi (voice) elle seçmek gerekiyor. Ses listesi
  // bazı tarayıcılarda asenkron yükleniyor, bu yüzden voiceschanged de
  // dinleniyor.
  var sesListesi = speechSynthesis.getVoices();
  speechSynthesis.onvoiceschanged = function(){ sesListesi = speechSynthesis.getVoices(); };

  function sesSec(dilOneki) {
    for (var i = 0; i < sesListesi.length; i++) {
      if (sesListesi[i].lang && sesListesi[i].lang.toLowerCase().indexOf(dilOneki) === 0) {
        return sesListesi[i];
      }
    }
    return null;
  }

  document.addEventListener('click', function(olay){
    var buton = olay.target.closest('.dinle');
    if (!buton) return;

    var calaniydi = buton.dataset.playing === '1';
    speechSynthesis.cancel();
    document.querySelectorAll('.dinle').forEach(sifirla);
    if (calaniydi) return;

    var kart = buton.closest('article');
    var baslikEl = kart.querySelector('h3');
    var ozetEl = kart.querySelector('details p');
    var metin = (baslikEl ? baslikEl.textContent : '') + '. ' + (ozetEl ? ozetEl.textContent : '');

    var konusma = new SpeechSynthesisUtterance(metin);
    var ses = sesSec(turkceMi ? 'tr' : 'en');
    if (ses) konusma.voice = ses;
    konusma.lang = turkceMi ? 'tr-TR' : 'en-US';
    konusma.onend = function(){ sifirla(buton); };
    konusma.onerror = function(){ sifirla(buton); };
    buton.dataset.playing = '1';
    buton.setAttribute('data-etiket', '\u23F9 Durdur');
    speechSynthesis.speak(konusma);
  });
})();
