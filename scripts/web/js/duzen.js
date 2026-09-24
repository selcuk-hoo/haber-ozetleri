// Döşeme/liste düzeni düğmesi: haberleri yan yana kutucuklar (döşeme)
// yerine tek sütun akış olarak göstermeye zorlar. Tercih hatırlanır.
(function(){
  var dugme = document.getElementById('duzen-buton');
  if (!dugme) return;

  function etiketGuncelle(listeMi) {
    dugme.setAttribute('data-etiket', listeMi ? '\u25A6 Kutu görünümü' : '\u2630 Liste görünümü');
  }

  var kayitli = null;
  try { kayitli = localStorage.getItem('duzen'); } catch (e) {}
  if (kayitli === 'liste') {
    document.documentElement.setAttribute('data-duzen', 'liste');
  }
  etiketGuncelle(kayitli === 'liste');

  dugme.addEventListener('click', function(){
    var suankiListe = document.documentElement.getAttribute('data-duzen') === 'liste';
    var yeni = suankiListe ? 'dosme' : 'liste';
    if (yeni === 'liste') {
      document.documentElement.setAttribute('data-duzen', 'liste');
    } else {
      document.documentElement.removeAttribute('data-duzen');
    }
    etiketGuncelle(yeni === 'liste');
    try { localStorage.setItem('duzen', yeni); } catch (e) {}
  });
})();
