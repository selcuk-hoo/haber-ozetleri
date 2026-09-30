"""GEÇİCİ teşhis: aynı yemek metinlerini farklı Claude modelleriyle çevirir."""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "scripts")
import claude_ceviri  # noqa: E402

metinler = json.loads((Path(__file__).parent / "model_metinler.json").read_text(encoding="utf-8"))
girdi = {f"m{i}": m for i, m in enumerate(metinler)}

for model in ("default", "sonnet", "haiku", "opus"):
    komut = [
        "claude", "-p", "Aşağıdaki JSON nesnesindeki metinleri kurallara göre Türkçeye çevir.",
        "--output-format", "json", "--tools", "", "--max-turns", "1",
        "--no-session-persistence", "--system-prompt", claude_ceviri.SISTEM,
    ]
    if model != "default":
        komut += ["--model", model]
    bas = time.time()
    try:
        s = subprocess.run(komut, input=json.dumps(girdi, ensure_ascii=False), capture_output=True,
                           text=True, timeout=300)
        zarf = json.loads(s.stdout)
        kullanilan = ",".join(zarf.get("modelUsage", {}).keys())
        print(f"[TESHIS] MODEL {model} -> {kullanilan} ({time.time() - bas:.0f} sn, hata={zarf.get('is_error')})")
        cevap = claude_ceviri.cevabi_ayikla(zarf.get("result") or "")
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] MODEL {model} HATA {hata!r} {getattr(s, 'stderr', '')[-300:]}")
        continue
    for k, v in cevap.items():
        print(f"[TESHIS] {model} {k}: {v}")
