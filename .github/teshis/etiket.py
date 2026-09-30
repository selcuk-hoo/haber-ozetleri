"""GEÇİCİ teşhis: TechCrunch ve The Verge beslemelerindeki kategori etiketleri."""
from collections import Counter

import feedparser

for adres in ["https://techcrunch.com/feed/", "https://www.theverge.com/rss/index.xml"]:
    f = feedparser.parse(adres, agent="Mozilla/5.0")
    say = Counter()
    for e in f.entries:
        etiketler = [t.get("term", "") for t in e.get("tags", [])]
        say.update(etiketler)
        print(f"[TESHIS] {adres[:30]} | {e.get('title','')[:80]} | {etiketler}")
    print(f"[TESHIS] {adres} etiket sayıları: {say.most_common(40)}")
