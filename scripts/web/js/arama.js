// Arama: yeni haberlerde (başlık + özet + kaynak adı) ve eski haberler
// listesinde (başlık + kaynak adı) bütün kategorilerde arar. Sunucu yok;
// aranan her şey zaten sayfada. En az 2 harf yazılınca kategori/kaynak
// seçimi bir kenara bırakılır, kutu boşalınca (ya da ×, Esc, bir kategori
// veya görünüm düğmesi) filtre.js'in görünümüne dönülür.
//
// Kutu HTML'de değil, burada kuruluyor ve translate.goog'da hiç
// kurulmuyor: Google Çeviri sayfadaki form öğelerini "form" sayıp uyarı
// gösterebiliyor (bkz. filtre.js'teki <select> notu).
(function(){
  if (/\.translate\.goog$/.test(location.hostname)) return;
  var cubuk = document.querySelector('.kaynak-cubugu');
  var izgara = document.getElementById('izgara');
  var arsiv = document.getElementById('arsiv');
  if (!cubuk || !izgara) return;

  var kutu = document.createElement('div');
  kutu.className = 'arama';
  kutu.setAttribute('translate', 'no');
  kutu.innerHTML =
    '<input type="search" id="arama-kutusu" class="arama-kutusu notranslate" placeholder="Haberlerde ara"' +
    ' aria-label="Haberlerde ara" autocomplete="off" autocorrect="off" spellcheck="false" enterkeyhint="search">' +
    '<button type="button" class="arama-temizle" aria-label="Aramayı temizle" data-etiket="&#215;" hidden></button>';
  cubuk.appendChild(kutu);
  var girdi = kutu.querySelector('input');
  var temizle = kutu.querySelector('.arama-temizle');

  var sonuc = document.createElement('p');
  sonuc.className = 'arama-sonuc';
  sonuc.hidden = true;
  cubuk.parentNode.insertBefore(sonuc, cubuk.nextSibling);

  // Türkçe harfleri ve aksanları katlar ("İstanbul", "ISTANBUL",
  // "istanbul" aynı; "cin" → "Çin", "gumruk" → "gümrük"), harf ve rakam
  // dışındakileri boşluk yapar. Aranan kelime bir kelimenin BAŞINDA
  // aranır: "cin" → "Çin", "Çin'in", "Çinli"; ama katlanmış "için" değil.
  function sade(metin) {
    return ' ' + metin.replace(/[İIı]/g, 'i').toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, ' ');
  }

  function metni(el, secici) {
    var parca = el.querySelector(secici);
    return parca ? parca.textContent : '';
  }

  var aktif = false;

  function kapat() {
    if (!aktif) return;
    aktif = false;
    document.documentElement.removeAttribute('data-arama');
    sonuc.hidden = true;
    if (arsiv) arsiv.classList.remove('arama-sonuclari');
    if (window.filtreYenile) window.filtreYenile();
  }

  function ara() {
    // Kesme işaretinden sonraki ek atılır: "Trump'ın" → "trump".
    var sorgu = sade(girdi.value.replace(/['’][^\s'’]*/g, '')).trim();
    temizle.hidden = !girdi.value;
    if (sorgu.length < 2) { kapat(); return; }
    var kelimeler = sorgu.split(' ').map(function(k){ return ' ' + k; });
    function uyar(metin) {
      var s = sade(metin);
      for (var i = 0; i < kelimeler.length; i++) {
        if (s.indexOf(kelimeler[i]) === -1) return false;
      }
      return true;
    }
    var yeniBasladi = !aktif;
    aktif = true;
    document.documentElement.setAttribute('data-arama', '1');

    var yeni = 0;
    izgara.style.display = '';
    izgara.querySelectorAll('article[data-kategori]').forEach(function(kart){
      var metin = metni(kart, 'h3') + ' ' + metni(kart, 'details p') + ' ' + (kart.dataset.kaynak || '');
      var var_ = uyar(metin);
      // 'block': sayfanın "yalnız ilk kategori" CSS kuralını ezmek için
      // (bkz. filtre.js uygula()).
      kart.style.display = var_ ? 'block' : 'none';
      if (var_) yeni++;
    });

    var eski = 0;
    if (arsiv) {
      arsiv.hidden = false;
      arsiv.classList.add('arama-sonuclari');
      arsiv.querySelectorAll('.arsiv-gun').forEach(function(gun){
        var gunde = 0;
        gun.querySelectorAll('li[data-kategori]').forEach(function(li){
          var var_ = uyar(metni(li, 'a') + ' ' + (li.dataset.kaynak || ''));
          li.hidden = !var_;
          if (var_) gunde++;
        });
        gun.hidden = gunde === 0;
        eski += gunde;
      });
      var bos = arsiv.querySelector('.arsiv-bos');
      if (bos) bos.hidden = true;
    }

    var ozet = (yeni || eski)
      ? '“' + girdi.value.trim() + '”: ' + yeni + ' yeni, ' + eski + ' eski haber'
      : '“' + girdi.value.trim() + '” için sonuç yok';
    sonuc.setAttribute('data-etiket', ozet);
    sonuc.hidden = false;
    // Sayfanın aşağısındayken aranırsa sonuçların başına çık (çubuk
    // yapışkan olduğu için kutu hep görünür).
    if (yeniBasladi && sonuc.getBoundingClientRect().top < 0) {
      window.scrollTo(0, sonuc.getBoundingClientRect().top + window.pageYOffset - cubuk.offsetHeight - 8);
    }
  }

  var zamanlayici;
  girdi.addEventListener('input', function(){
    clearTimeout(zamanlayici);
    zamanlayici = setTimeout(ara, 150);
  });
  girdi.addEventListener('keydown', function(olay){
    if (olay.key === 'Escape') { girdi.value = ''; ara(); }
    // Telefonda "Ara"ya basınca klavye kapansın, sonuçlar görünsün.
    if (olay.key === 'Enter') { clearTimeout(zamanlayici); ara(); girdi.blur(); }
  });
  temizle.addEventListener('click', function(){
    girdi.value = '';
    ara();
    girdi.focus();
  });

  // Arama sürerken kategori, görünüm ya da kaynak düğmesine basılırsa
  // arama bırakılır; filtre.js kendi işini sonra (aynı tıklamada) yapar.
  document.addEventListener('click', function(olay){
    if (!aktif) return;
    if (olay.target.closest('.kategori-buton, .gorunum-buton')) {
      girdi.value = '';
      temizle.hidden = true;
      kapat();
    }
  }, true);
})();
