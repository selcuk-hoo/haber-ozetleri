"""Claude ile çeviri (yemek yazıları gibi deyim ve mutfak terimi dolu metinler).

Google kelimesi kelimesine çeviriyor: "garlic presses became a no-no" →
"hayır-hayır oldu", "mop the plate" → "tabağı paspaslamak", "jacket
potatoes" → "ceketli patates". Claude anlamı çeviriyor.

GitHub Actions'ta Claude Code CLI (`claude -p`) kullanıcının Claude
aboneliğiyle çalışır: CLAUDE_CODE_OAUTH_TOKEN gizli değişkeni (`claude
setup-token` ile üretilir). Anahtar yoksa, CLI yoksa ya da çağrı başarısız
olursa hiçbir şey çevrilmez ve metinler her zamanki gibi Google'a gider.

Bir çalıştırmadaki metinler PARCA_BOYU'luk parçalar halinde, her parça tek
bir çağrıyla (JSON girdi → JSON çıktı) çevrilir; araçlar kapalıdır.
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

SISTEM = """Sen İngilizce yemek ve mutfak yazılarını Türkçeye çeviren deneyimli bir editörsün.
Çevirilerin bir Türk haber sitesinde, Türk okur için yayımlanıyor.

Kurallar:
- Anlamı çevir, kelimeleri değil. Deyimleri ve esprileri Türkçede aynı etkiyi
  veren ifadelerle karşıla ("a no-no" → "yasak", "let's crack on" → "hadi
  başlayalım", "mop up the plate" → "tabağı sıyırmak").
- Mutfak terimlerinin Türkçede yerleşik karşılığını kullan ("jacket potatoes"
  → "fırında kabuklu patates", "apple butter" → "elma ezmesi", "baked beans"
  → "konserve kuru fasulye" ya da bağlama göre "fırın fasulye"). Türkçede
  karşılığı olmayan yemek adlarını (risotto, masala, chili, gaw mein) özgün
  adıyla bırak.
- Kişi, restoran, şirket, kitap ve program adlarını çevirme.
- Ölçü ve sıcaklık birimlerini değiştirme.
- Hiçbir şey ekleme, çıkarma ya da özetleme; cümle cümle, eksiksiz çevir.
- Başlıkları doğal bir Türkçe haber başlığı gibi yaz.
- Doğal, akıcı, yazım kurallarına uygun Türkçe kullan.

Girdi bir JSON nesnesidir: {"kimlik": "İngilizce metin", ...}.
Yalnızca aynı kimliklerle bir JSON nesnesi döndür: {"kimlik": "Türkçe çeviri", ...}.
Açıklama, kod bloğu işareti ya da başka metin yazma."""


def kullanilabilir_mi() -> bool:
    return bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")) and shutil.which("claude") is not None


def _cagir(girdi: dict[str, str]) -> dict[str, str]:
    komut = [
        "claude", "-p", "Aşağıdaki JSON nesnesindeki metinleri kurallara göre Türkçeye çevir.",
        "--output-format", "json",
        "--tools", "",
        "--max-turns", "1",
        "--no-session-persistence",
        "--system-prompt", SISTEM,
    ]
    model = os.environ.get("CLAUDE_CEVIRI_MODELI")
    if model:
        komut += ["--model", model]
    sonuc = subprocess.run(
        komut, input=json.dumps(girdi, ensure_ascii=False), capture_output=True, text=True, timeout=ZAMAN_ASIMI,
        cwd=os.environ.get("RUNNER_TEMP") or None,
    )
    if sonuc.returncode != 0:
        raise RuntimeError(f"claude çıkış kodu {sonuc.returncode}: {sonuc.stderr[-300:] or sonuc.stdout[-300:]}")
    zarf = json.loads(sonuc.stdout)
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


def toplu_cevir(metinler: dict[str, str], cagir=_cagir) -> dict[str, str]:
    """{kimlik: İngilizce} → {kimlik: Türkçe}. Başarısız parçalar ve
    cevapta olmayan kimlikler sonuçta yer almaz (Google'a kalır)."""
    sonuc: dict[str, str] = {}
    kimlikler = list(metinler)[:CALISTIRMA_BASINA_METIN]
    for i in range(0, len(kimlikler), PARCA_BOYU):
        parca = {k: metinler[k] for k in kimlikler[i:i + PARCA_BOYU]}
        try:
            cevap = cagir(parca)
        except Exception as hata:  # noqa: BLE001 - Claude olmazsa Google var
            print(f"Claude çevirisi alınamadı ({hata!r}); kalanlar Google'a kalıyor", file=sys.stderr)
            break
        sonuc.update({k: v for k, v in cevap.items() if k in parca})
    return sonuc
