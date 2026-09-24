// Karanlık tema düğmesi: sistem tercihinden bağımsız manuel geçiş,
// tercih tarayıcıda (localStorage) hatırlanır.
(function(){
  var dugme = document.getElementById('tema-buton');
  if (!dugme) return;

  function etiketGuncelle(koyuMu) {
    dugme.setAttribute('data-etiket', koyuMu ? '\u2600\uFE0F Açık tema' : '\uD83C\uDF19 Koyu tema');
  }

  var kayitli = null;
  try { kayitli = localStorage.getItem('tema'); } catch (e) {}
  if (kayitli === 'dark' || kayitli === 'light') {
    document.documentElement.setAttribute('data-theme', kayitli);
  }

  var sistemKoyu = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  etiketGuncelle(kayitli ? kayitli === 'dark' : sistemKoyu);

  dugme.addEventListener('click', function(){
    var mevcut = document.documentElement.getAttribute('data-theme');
    var suankiKoyu = mevcut ? mevcut === 'dark' : sistemKoyu;
    var yeni = suankiKoyu ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', yeni);
    etiketGuncelle(yeni === 'dark');
    try { localStorage.setItem('tema', yeni); } catch (e) {}
  });
})();
