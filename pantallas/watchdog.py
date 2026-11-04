"""Revierte un cambio no confirmado incluso si se cierra la aplicación."""
import json
from pathlib import Path
import sys
import time
from . import backend

def main():
    path = Path(sys.argv[1])
    if not path.exists(): return
    tx = json.loads(path.read_text())
    while path.exists() and time.time() < tx['deadline']:
        time.sleep(.25)
    if path.exists():
        try:
            if not backend.revert(path):
                backend.atomic(path.with_suffix('.recovery.json'), json.dumps(tx, indent=2))
        except Exception:
            pass

if __name__ == '__main__': main()
