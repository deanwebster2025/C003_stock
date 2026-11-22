"""Publish only public website assets; never ship workflows or source caches."""
from pathlib import Path
import shutil
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist"

def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for name in ("index.html", "styles.css", "app.js", "core.js", "bonds.js"):
        shutil.copy2(ROOT / name, OUT / name)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / "data").mkdir()
    payload = json.loads((ROOT / "data/events.json").read_text())
    (OUT / "data/events.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (OUT / ".nojekyll").touch()
    print(f"Built {OUT}")

if __name__ == "__main__":
    build()
