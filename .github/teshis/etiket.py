"""GEÇİCİ teşhis: TechCrunch ve The Verge etiket envanteri.
1) TechCrunch beslemesinin 1-10. sayfaları (başlık + <category>).
2) Arşivdeki (son 7 gün) TechCrunch ve The Verge yazılarının sayfa etiketleri
   (trafilatura metadata: tags, categories).
3) The Verge beslemesi (başlık + <category>) — sayfa etiketiyle karşılaştırma için."""
import json
import sys
import time

import feedparser
import trafilatura

sys.path.insert(0, "scripts")

for sayfa in range(1, 11):
    f = feedparser.parse(f"https://techcrunch.com/feed/?paged={sayfa}", agent="Mozilla/5.0")
    for e in f.entries:
        et = "|".join(t.get("term", "") for t in e.get("tags", []))
        print(f"[TESHIS] TCBESLEME\t{e.get('published','')[:16]}\t{e.get('title','')}\t{et}")
    time.sleep(1)

f = feedparser.parse("https://www.theverge.com/rss/index.xml", agent="Mozilla/5.0")
for e in f.entries:
    et = "|".join(t.get("term", "") for t in e.get("tags", []))
    print(f"[TESHIS] VBESLEME\t{e.get('link','')}\t{e.get('title','')}\t{et}")

arsiv = json.load(open("dist/arsiv.json"))
for k in arsiv:
    if k["kaynak"] not in ("techcrunch.com", "theverge.com"):
        continue
    try:
        html = trafilatura.fetch_url(k["url"])
        b = trafilatura.bare_extraction(html, url=k["url"], with_metadata=True).as_dict() if html else {}
    except Exception as hata:  # noqa: BLE001
        b = {"tags": f"HATA {hata!r}"}
    print(f"[TESHIS] SAYFA\t{k['kaynak']}\t{k['url']}\t{k['baslik']}\t{b.get('tags')}\t{b.get('categories')}")
