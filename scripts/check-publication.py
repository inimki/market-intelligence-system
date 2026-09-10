"""Fail if private state or generated dependencies enter Git's public manifest."""
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = subprocess.check_output(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
).decode("utf-8").split("\0")
blocked = {".git", ".openai", ".wrangler", "node_modules", ".next", ".vinext"}
violations = []
for name in filter(None, files):
    path = Path(name)
    if (blocked.intersection(path.parts)
        or (path.name.startswith(".env") and path.name != ".env.example")
        or path.suffix.lower() in {".key", ".pem", ".pfx", ".p12", ".db", ".dump", ".bak"}
        or name.startswith(("data/raw/", "data/logs/", "learning-site/out/"))
        or (name.startswith("data/reports/") and path.name != ".gitkeep")):
        violations.append(name)
if violations:
    raise SystemExit("Private/generated paths in publication manifest: " + ", ".join(violations))
for name in ("package.json", "package-lock.json", "Dockerfile.nginx", "scripts/build-static.mjs"):
    if not (root / "learning-site" / name).is_file():
        raise SystemExit("Bundled learning source missing: " + name)
print("PASS: publication manifest excludes private state; bundled source is complete.")
