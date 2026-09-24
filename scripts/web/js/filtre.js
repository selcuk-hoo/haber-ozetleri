// Kategori + kaynak filtresi: üstteki kategori sekmesi hangi konunun
// kartları görünsün onu belirler; altındaki tek "Kaynak" açılır menüsü
// her kategori değişiminde bu kategorinin kaynaklarına göre JS
// tarafından yeniden kurulur (sunucu tarafında bir buton yığını basmak
// yerine — çok sayıda kaynağı olan kategorilerde bu, N ayrı düğme yerine
// tek bir seçiciye sığar). "All Sources" o kategorinin tüm haberlerini
// zamana göre karışık gösterir, bir kaynak seçmek sayfa yeniden
// yüklenmeden sadece onu gösterir.
//
// Bilerek gerçek bir <select> DEĞİL: Google Çeviri (translate.goog)
// sayfadaki <select>/<form> elemanlarını "form" sayıp bir uyarıyla
// engelliyor. Onun yerine düz bir buton + gizli/görünür <ul> listesiyle
// kendi açılır menümüz kuruluyor.
var KATEGORI_VERISI = __KATEGORI_VERISI__;
(function(){
  var izgara = document.getElementById('izgara');
  var seciciButon = document.getElementById('kaynak-secici-buton');
  var seciciListe = document.getElementById('kaynak-secici-liste');
  var topButonu = document.getElementById('top-buton');
  var kategoriButonlari = document.querySelectorAll('.kategori-buton');
  if (!izgara || !seciciButon || !seciciListe || !kategoriButonlari.length) return;

  var aktifKategori = kategoriButonlari[0].dataset.kategori;
  var aktifKaynak = 'all';

  if (topButonu) {
    topButonu.addEventListener('click', function(){
      window.scrollTo({top: 0, behavior: 'smooth'});
    });
  }

  function uygula() {
    izgara.querySelectorAll('article[data-kategori]').forEach(function(el){
      var kategoriUyum = el.dataset.kategori === aktifKategori;
      var kaynakUyum = aktifKaynak === 'all' || el.dataset.kaynak === aktifKaynak;
      // '' değil 'block': boş string satır içi stili kaldırır, o zaman
      // sayfanın başındaki "sadece ilk kategori görünsün" CSS kuralı
      // (ekstra_stil) tekrar devreye girip kartı gizler. Satır içi stil
      // her zaman sayfa CSS'inden önceliklidir, bu yüzden açıkça 'block'
      // yazmak gerekiyor.
      el.style.display = (kategoriUyum && kaynakUyum) ? 'block' : 'none';
    });
    document.querySelectorAll('.bos[data-kategori]').forEach(function(el){
      var kategoriUyum = el.dataset.kategori === aktifKategori;
      el.hidden = !(kategoriUyum && aktifKaynak !== 'all' && el.dataset.kaynak === aktifKaynak);
    });
  }

  function listeyiKapat() {
    seciciListe.hidden = true;
    seciciButon.setAttribute('aria-expanded', 'false');
  }

  // Butonun etiketini SADECE textContent ile değiştirmek yerine, o
  // etiketi taşıyan span'ı yepyeni bir span ile değiştiriyoruz. Google
  // Çeviri (translate.goog) sayfayı ilk yüklerken DOM'daki mevcut
  // öğeleri çevirir, sonradan eklenen düğümleri de bir gözlemciyle
  // yakalayıp çevirir — ama var olan bir düğümün textContent'i
  // değiştirildiğinde bunu fark etmez (yalnızca ekleme/çıkarma
  // izliyor). innerHTML ile kurulan <li> seçenekleri tam olarak bu
  // yüzden çevriliyordu; buton etiketi ise düz metin ataması olduğu
  // için çevrilmeden İngilizce kalıyordu. Etiketi bağımsız bir span
  // yapıp her güncellemede yepyeni bir span ile değiştirmek, <li>'lerle
  // aynı "yeni düğüm" davranışını taklit ediyor.
  function etiketiGuncelle(metin) {
    var eskiEtiket = seciciButon.querySelector('.kaynak-secici-etiket');
    var yeniEtiket = document.createElement('span');
    yeniEtiket.className = 'kaynak-secici-etiket';
    yeniEtiket.textContent = metin;
    eskiEtiket.replaceWith(yeniEtiket);
  }

  function kaynakSeciciKur(butonuSifirla) {
    var kaynaklar = KATEGORI_VERISI[aktifKategori] || [];
    var kategoriToplami = kaynaklar.reduce(function(acc, k){ return acc + k[1]; }, 0);
    var html = '<li role="option" aria-selected="true" data-filtre="all">All Sources (' + kategoriToplami + ')</li>';
    kaynaklar.forEach(function(k){
      html += '<li role="option" aria-selected="false" data-filtre="' + k[0] + '">' + k[0] + ' (' + k[1] + ')</li>';
    });
    seciciListe.innerHTML = html;
    // İlk yüklemede butonun etiketine hiç DOKUNMA: sunucudan gelen
    // "All Sources" span'ı sayfanın ilk taramasında zaten Google
    // tarafından çevrilmiş olur. Kategori değişince filtre gerçekten
    // "all"a sıfırlandığı için orada etiketiGuncelle ile güncellemek
    // gerekiyor (yeni bir span olduğundan Google bunu da yakalar).
    if (butonuSifirla) {
      etiketiGuncelle('All Sources');
    }
    listeyiKapat();
  }

  seciciButon.addEventListener('click', function(olay){
    olay.stopPropagation();
    var acikMi = !seciciListe.hidden;
    if (acikMi) {
      listeyiKapat();
    } else {
      seciciListe.hidden = false;
      seciciButon.setAttribute('aria-expanded', 'true');
    }
  });

  seciciListe.addEventListener('click', function(olay){
    var secenek = olay.target.closest('[data-filtre]');
    if (!secenek) return;
    aktifKaynak = secenek.dataset.filtre;
    etiketiGuncelle(secenek.textContent);
    seciciListe.querySelectorAll('[data-filtre]').forEach(function(li){
      li.setAttribute('aria-selected', li === secenek ? 'true' : 'false');
    });
    listeyiKapat();
    uygula();
  });

  document.addEventListener('click', function(olay){
    if (!seciciListe.hidden && !seciciListe.contains(olay.target) && olay.target !== seciciButon) {
      listeyiKapat();
    }
  });

  kategoriButonlari.forEach(function(buton){
    buton.addEventListener('click', function(){
      aktifKategori = buton.dataset.kategori;
      aktifKaynak = 'all';
      kategoriButonlari.forEach(function(b){ b.classList.toggle('aktif', b === buton); });
      kaynakSeciciKur(true);
      uygula();
    });
  });

  kaynakSeciciKur();
  uygula();
})();
