"""GEÇİCİ: Türkiye havuzunun haberlerini loga yaz (gruplamayı yerelde ayarlamak için)."""
import json, sys
from datetime import datetime, timezone
sys.path.insert(0, "scripts")
import turkiye
for h in turkiye.haberleri_topla([], datetime.now(timezone.utc)):
    print("[TRVERI] " + json.dumps(h, ensure_ascii=False))
