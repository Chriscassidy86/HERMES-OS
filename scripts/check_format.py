"""Dependency-free whitespace/formatting gate for Python sources."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
errors=[]
paths=(ROOT/"core"/"settings.py",ROOT/"core"/"health.py",ROOT/"database"/"maintenance.py",ROOT/"scripts"/"healthcheck.py",ROOT/"scripts"/"paper_service.py",ROOT/"scripts"/"check_format.py")
for path in paths:
    text=path.read_text(encoding="utf-8")
    if "\t" in text: errors.append(f"{path}: tab indentation")
    if any(line.endswith((" ","\t")) for line in text.splitlines()): errors.append(f"{path}: trailing whitespace")
    if text and not text.endswith("\n"): errors.append(f"{path}: missing final newline")
if errors: raise SystemExit("\n".join(errors))
print("format-check: ok")
