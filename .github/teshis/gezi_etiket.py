"""GEÇİCİ teşhis: Gezi kaynaklarının (CN Traveler, Lonely Planet) sayfa etiketleri."""
import json
import sys

import trafilatura

sys.path.insert(0, "scripts")
from besleme import sayfa_etiketleri  # noqa: E402

arsiv = json.load(open("dist/arsiv.json"))
for k in arsiv:
    if k["kategori"] != "Gezi" or k["kaynak"] not in ("cntraveler.com", "lonelyplanet.com"):
        continue
    try:
        html = trafilatura.fetch_url(k["url"])
        veri = trafilatura.bare_extraction(html, url=k["url"], with_metadata=True).as_dict() if html else {}
        et = sayfa_etiketleri(veri)
    except Exception as hata:  # noqa: BLE001
        et = [f"HATA {hata!r}"]
    print(f"[TESHIS] {k['kaynak']}\t{k['baslik'][:90]}\t{'|'.join(et)}")
