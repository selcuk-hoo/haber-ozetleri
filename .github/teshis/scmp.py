"""GEÇİCİ: SCMP metninin ilk satırları (ikinci başlık + alt başlık) ([TESHIS] satırları)."""
import json, subprocess, sys
sys.path.insert(0, "scripts")
from besleme import makale_getir
subprocess.run(["git", "fetch", "-q", "origin", "gh-pages"], check=True)
arsiv = json.loads(subprocess.run(["git", "show", "origin/gh-pages:arsiv.json"], capture_output=True, text=True, check=True).stdout)
urller = [k["url"] for k in arsiv if k["kaynak"] == "scmp.com"][:12]
for u in urller:
    s = makale_getir(u)
    if not s:
        continue
    print(f"[TESHIS] {u}\n[TESHIS]  BASLIK: {s['baslik']!r}")
    for satir in s["govde"].split("\n")[:4]:
        print(f"[TESHIS]  | {satir[:220]!r}")
