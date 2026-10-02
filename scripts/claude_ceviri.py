"""Claude ile çeviri (yemek yazıları gibi deyim ve mutfak terimi dolu metinler).

Google kelimesi kelimesine çeviriyor: "garlic presses became a no-no" →
"hayır-hayır oldu", "mop the plate" → "tabağı paspaslamak", "jacket
potatoes" → "ceketli patates". Claude anlamı çeviriyor.

GitHub Actions'ta Claude Code CLI (`claude -p`) kullanıcının Claude
aboneliğiyle çalışır: CLAUDE_CODE_OAUTH_TOKEN gizli değişkeni (`claude
setup-token` ile üretilir). Anahtar yoksa, CLI yoksa ya da çağrı başarısız
olursa hiçbir şey çevrilmez ve metinler her zamanki gibi Google'a gider.

Bir çalıştırmadaki metinler PARCA_BOYU'luk parçalar halinde, her parça tek
bir çağrıyla (JSON girdi → JSON çıktı) çevrilir; araçlar kapalıdır. Cevap
bozuk JSON'sa parça ikiye bölünüp yeniden denenir.

Model: Sonnet. Sonnet, Haiku ve Opus 8 gerçek yemek metninde denendi
(Eylül 2026): Opus en iyisi ama farkı küçük, abonelik limitini çok daha hızlı
tüketir; Haiku Google'dan pek iyi değil (dil bilgisi hataları). Başka model
için CLAUDE_CEVIRI_MODELI.
"""

import json
import os
import re
import shutil
import subprocess
import sys

PARCA_BOYU = 12  # bir çağrıdaki metin sayısı
ZAMAN_ASIMI = 240  # sn, bir çağrı için
# Bir çalıştırmada en fazla bu kadar metin (abonelik kullanım limitini
# korumak için; kalanlar sonraki çalıştırmada).
CALISTIRMA_BASINA_METIN = 72
MODEL = "sonnet"

# Bu çalıştırmadaki Claude kullanımı (claude CLI'nin JSON cevabındaki
# "usage" ve "total_cost_usd"; aboneliğin kullanım limitini izlemek için
# loga yazılır). Maliyet API fiyatıyla karşılığıdır, abonelikte ödenmez.
kullanim = {"cagri": 0, "girdi": 0, "onbellek": 0, "cikti": 0, "maliyet": 0.0}
# Sağlık takibi için (bkz. saglik.py): bu çalıştırmada Claude'a gidildi mi,
# hata alındı mı.
durum: dict = {"denendi": False, "hata": None}


def kullanimi_ekle(zarf: dict) -> None:
    u = zarf.get("usage") or {}
    kullanim["cagri"] += 1
    kullanim["girdi"] += int(u.get("input_tokens") or 0) + int(u.get("cache_creation_input_tokens") or 0)
    kullanim["onbellek"] += int(u.get("cache_read_input_tokens") or 0)
    kullanim["cikti"] += int(u.get("output_tokens") or 0)
    kullanim["maliyet"] += float(zarf.get("total_cost_usd") or 0)


def kullanim_ozeti() -> str:
    k = kullanim
    return (f"{k['cagri']} çağrı, {k['girdi']} girdi + {k['onbellek']} önbellekten okunan + {k['cikti']} çıktı token"
            f" (API karşılığı ~${k['maliyet']:.3f})")

# Kategoriye göre çevirmenin rolü ve alana özgü kurallar.
ALANLAR: dict[str, tuple[str, str]] = {
    "Yemek": ("yemek ve mutfak yazılarını", """- Mutfak terimlerinin Türkçede yerleşik karşılığını kullan ("jacket potatoes"
  → "fırında kabuklu patates", "apple butter" → "elma ezmesi", "baked beans"
  → "konserve kuru fasulye" ya da bağlama göre "fırın fasulye"). Türkçede
  karşılığı olmayan yemek adlarını (risotto, masala, chili, gaw mein) özgün
  adıyla bırak.
- Kişi, restoran, şirket, kitap ve program adlarını çevirme.
- Ölçü ve sıcaklık birimlerini değiştirme."""),
    "Gezi": ("gezi ve seyahat yazılarını", """- Yer adlarının Türkçede yerleşik biçimini kullan (Venice → Venedik, Florence
  → Floransa, Munich → Münih, the Alps → Alpler); yerleşik Türkçe biçimi
  olmayanları özgün yazılışıyla bırak.
- Otel, restoran, havayolu, şirket, marka, kişi ve etkinlik adlarını çevirme.
- Seyahat terimlerini Türkçede kullanıldığı gibi yaz ("layover" → "aktarma",
  "carry-on" → "kabin bagajı", "boutique hotel" → "butik otel").
- Para, mesafe ve sıcaklık birimlerini değiştirme."""),
    # Gündem, Teknoloji ve Bilim Gemini'yle çevriliyor (bkz. gemini_ceviri.py);
    # aynı talimat Google durunca Claude yedeğinde de kullanılır.
    "Gündem": ("dünya gündemi haberlerini", """- Kişi, şirket, parti ve yayın adlarını çevirme. Ülke, şehir ve kurum
  adlarının Türkçede yerleşik biçimini kullan (the Kremlin → Kremlin, the
  State Department → ABD Dışişleri Bakanlığı, Kyiv → Kiev).
- Unvanları Türk basınındaki gibi yaz (US President → ABD Başkanı, Prime
  Minister → Başbakan, Secretary of State → Dışişleri Bakanı).
- Haberin kesinlik derecesini koru: "reportedly", "allegedly", "according
  to", "said" gibi kayıtları atma ("7 Reported Killed" → "7 kişinin öldüğü
  bildirildi", "öldü" değil; "Apple's reportedly developing" → "Apple'ın
  … geliştirdiği bildiriliyor").
- "arrest" ile "detain" farkını gözet (gözaltı / tutuklama).
- Haber dilini koru: tarafsız, açık cümleler."""),
    "Teknoloji": ("teknoloji haberlerini", """- Şirket, ürün, uygulama, özellik ve marka adlarını çevirme ("Guided Vision",
  "Fire TV Stick"); kişi ve yayın adlarını da.
- Teknik terimlerin Türkçede yerleşik karşılığını kullan (EV → elektrikli
  araç, chip → çip); yerleşik karşılığı olmayanları özgün haliyle bırak.
- Haberin kesinlik derecesini koru: "reportedly", "allegedly", "according
  to" gibi kayıtları atma ("Apple's reportedly developing" → "Apple'ın …
  geliştirdiği bildiriliyor").
- Haber dilini koru: tarafsız, açık cümleler."""),
    "Bilim": ("bilim haberlerini ve yazılarını", """- Bilimsel terimlerin, canlı ve hastalık adlarının Türkçede yerleşik
  karşılığını kullan (stick insect → çubuk böceği, thunderstorm → gök
  gürültülü fırtına); Latince tür adlarını değiştirme.
- Kişi, üniversite, dergi ve kurum adlarını çevirme; üniversite adını Türkçe
  kalıpla yazabilirsin (University of Sydney → Sidney Üniversitesi).
- "scientists" → "bilim insanları".
- Bulguların kesinlik derecesini koru ("could help" → "yardımcı olabilir",
  "suggests" → "işaret ediyor").
- Açıklayıcı yazılarda yazarın üslubunu koru; deyimleri anlamıyla çevir
  ("how on earth" → "nasıl olur da")."""),
    "Sanat & Kültür": ("sanat, edebiyat ve kültür yazılarını (eleştiriler, denemeler, sergi ve kitap haberleri)",
                       """- Kitap, film, oyun, sergi ve eser adlarının Türkçede yerleşik adı varsa onu kullan
  ("Crime and Punishment" → "Suç ve Ceza", "The Iliad" → "İlyada"); yoksa
  özgün adıyla bırak.
- Kişi, müze, galeri, yayınevi, orkestra ve kurum adlarını çevirme.
- Sanat ve edebiyat terimlerinin Türkçedeki karşılığını kullan ("installation"
  → "yerleştirme", "retrospective" → "retrospektif", "memoir" → "anı").
- Denemelerde ve eleştirilerde yazarın üslubunu ve tonunu koru; alıntıları
  anlamıyla çevir."""),
}

SISTEM_KALIBI = """Sen İngilizce {rol} Türkçeye çeviren deneyimli bir editörsün.
Çevirilerin bir Türk haber sitesinde, Türk okur için yayımlanıyor.

Kurallar:
- Anlamı çevir, kelimeleri değil. Deyimleri ve esprileri Türkçede aynı etkiyi
  veren ifadelerle karşıla ("a no-no" → "yasak", "let's crack on" → "hadi
  başlayalım", "mop up the plate" → "tabağı sıyırmak").
{alan}
- Hiçbir şey ekleme, çıkarma ya da özetleme; cümle cümle, eksiksiz çevir.
  Açıklama, not ya da parantez içinde İngilizce karşılık ekleme.
- Başlıkları doğal bir Türkçe haber başlığı gibi yaz; başlığa bilgi ekleme
  ("3 Days in Budapest" → "Budapeşte'de 3 Gün", "Macaristan'ın başkenti" değil).
- Özel ad olmayan İngilizce ifadeleri İngilizce bırakma ("country-chic" →
  "kırsal şıklıkta").
- Doğal, akıcı, yazım kurallarına uygun Türkçe kullan.

Girdi bir JSON nesnesidir: {{"kimlik": "İngilizce metin", ...}}.
Yalnızca aynı kimliklerle bir JSON nesnesi döndür: {{"kimlik": "Türkçe çeviri", ...}}.
Çeviride tırnak işareti gerekirse “ ” ya da ‘ ’ kullan (JSON bozulmasın).
Açıklama, kod bloğu işareti ya da başka metin yazma."""


def sistem(kategori: str) -> str:
    rol, alan = ALANLAR.get(kategori, ("haber yazılarını", "- Kişi, kurum, şirket ve marka adlarını çevirme."))
    return SISTEM_KALIBI.format(rol=rol, alan=alan)


def kullanilabilir_mi() -> bool:
    return bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")) and shutil.which("claude") is not None


def _cagir(girdi: dict[str, str], sistem_metni: str) -> dict[str, str]:
    komut = [
        "claude", "-p", "Aşağıdaki JSON nesnesindeki metinleri kurallara göre Türkçeye çevir.",
        "--output-format", "json",
        "--tools", "",
        "--max-turns", "1",
        "--no-session-persistence",
        "--system-prompt", sistem_metni,
    ]
    komut += ["--model", os.environ.get("CLAUDE_CEVIRI_MODELI") or MODEL]
    sonuc = subprocess.run(
        komut, input=json.dumps(girdi, ensure_ascii=False), capture_output=True, text=True, timeout=ZAMAN_ASIMI,
        cwd=os.environ.get("RUNNER_TEMP") or None,
    )
    if sonuc.returncode != 0:
        raise RuntimeError(f"claude çıkış kodu {sonuc.returncode}: {sonuc.stderr[-300:] or sonuc.stdout[-300:]}")
    zarf = json.loads(sonuc.stdout)
    kullanimi_ekle(zarf)
    if zarf.get("is_error"):
        raise RuntimeError(f"claude hata: {str(zarf.get('result'))[:300]}")
    return cevabi_ayikla(zarf.get("result") or "")


def cevabi_ayikla(metin: str) -> dict[str, str]:
    """Modelin cevabındaki JSON nesnesini alır (kod bloğu işareti ya da
    öncesinde/sonrasında metin varsa atlanır)."""
    eslesme = re.search(r"\{.*\}", metin, re.S)
    if not eslesme:
        raise ValueError(f"cevapta JSON yok: {metin[:200]}")
    veri = json.loads(eslesme.group(0))
    if not isinstance(veri, dict):
        raise ValueError("cevap bir JSON nesnesi değil")
    return {str(k): str(v) for k, v in veri.items() if isinstance(v, str) and v.strip()}


def toplu_cevir(metinler: dict[str, str], cagir=None, kategori: str = "") -> dict[str, str]:
    """{kimlik: İngilizce} → {kimlik: Türkçe}. Başarısız parçalar ve
    cevapta olmayan kimlikler sonuçta yer almaz (Google'a kalır)."""
    if cagir is None:
        sistem_metni = sistem(kategori)
        cagir = lambda parca: _cagir(parca, sistem_metni)  # noqa: E731
    sonuc: dict[str, str] = {}
    kimlikler = list(metinler)[:CALISTIRMA_BASINA_METIN]
    for i in range(0, len(kimlikler), PARCA_BOYU):
        parca = {k: metinler[k] for k in kimlikler[i:i + PARCA_BOYU]}
        durum["denendi"] = True
        try:
            sonuc.update(_parcayi_cevir(parca, cagir))
        except Exception as hata:  # noqa: BLE001 - Claude olmazsa Google var
            print(f"Claude çevirisi alınamadı ({hata!r}); kalanlar Google'a kalıyor", file=sys.stderr)
            durum["hata"] = repr(hata)[:300]
            break
    return sonuc


def _parcayi_cevir(parca: dict[str, str], cagir, ad: str = "Claude") -> dict[str, str]:
    """Cevap bozuksa (ValueError: JSON yok ya da tırnak kaçmamış) parça
    ikiye bölünüp yeniden denenir; tek metinde de bozuksa o metin Google'a
    kalır. Öteki hatalar (limit, zaman aşımı) çalıştırmayı durdurur.
    Gemini de aynısını kullanır (bkz. gemini_ceviri.py)."""
    try:
        cevap = cagir(parca)
    except ValueError as hata:
        if len(parca) == 1:
            print(f"{ad} cevabı okunamadı ({hata!r}); metin Google'a kalıyor", file=sys.stderr)
            return {}
        kimlikler = list(parca)
        yari = len(kimlikler) // 2
        sonuc = _parcayi_cevir({k: parca[k] for k in kimlikler[:yari]}, cagir, ad)
        sonuc.update(_parcayi_cevir({k: parca[k] for k in kimlikler[yari:]}, cagir, ad))
        return sonuc
    return {k: v for k, v in cevap.items() if k in parca}
